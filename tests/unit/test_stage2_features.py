"""Tests for src.analysis.stage2_features -- Stage 2 Feature Extraction.

All tests use mock models to avoid downloading ~1.6 GB of NLP models in CI.
The mocks replicate the exact interface contracts of SentenceTransformer,
KeyBERT, transformers NER pipeline, and spaCy NER.

Test categories:
    - Schema validation: Parquet output matches PRD section 7.1
    - Text helpers: language detection, entity normalization, deduplication
    - Component unit tests: SBERT, TF-IDF, NER, KeyBERT (mocked)
    - Integration: full Stage2FeatureExtractor.run() with synthetic articles
    - Edge cases: empty corpus, missing columns, paywall-only articles
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.stage2_features import (
    Stage2Config,
    Stage2Metrics,
    Stage2FeatureExtractor,
    SBERTEncoder,
    TFIDFExtractor,
    NERExtractor,
    KeyBERTExtractor,
    _detect_language,
    _normalize_entity_name,
    _deduplicate_entities,
    _embeddings_schema,
    _tfidf_schema,
    _ner_schema,
    run_stage2,
    get_sbert_model,
    unload_sbert_model,
    _get_memory_gb,
)
from src.utils.error_handler import PipelineStageError, ModelLoadError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    """Return a default Stage2Config."""
    return Stage2Config()


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create and return a temporary output directory."""
    out = tmp_path / "features"
    out.mkdir()
    return out


@pytest.fixture
def sample_articles_parquet(tmp_path):
    """Create a sample articles.parquet with 5 articles (3 EN, 2 KO).

    Returns:
        Path to the created Parquet file.
    """
    schema = pa.schema([
        pa.field("article_id", pa.utf8()),
        pa.field("url", pa.utf8()),
        pa.field("title", pa.utf8()),
        pa.field("body", pa.utf8()),
        pa.field("source", pa.utf8()),
        pa.field("category", pa.utf8()),
        pa.field("language", pa.utf8()),
        pa.field("published_at", pa.utf8()),
        pa.field("crawled_at", pa.utf8()),
        pa.field("author", pa.utf8()),
        pa.field("word_count", pa.int32()),
        pa.field("content_hash", pa.utf8()),
    ])

    data = {
        "article_id": ["art-001", "art-002", "art-003", "art-004", "art-005"],
        "url": [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
            "https://example.kr/4",
            "https://example.kr/5",
        ],
        "title": [
            "US Federal Reserve raises interest rates amid inflation concerns",
            "Samsung Electronics posts record quarterly profits",
            "Climate change summit opens in Paris with 195 nations",
            "삼성전자, 분기 실적 사상 최대 기록",
            "한국은행 기준금리 인상 결정",
        ],
        "body": [
            "The Federal Reserve announced a 25 basis point increase in interest rates on Wednesday. "
            "Chair Jerome Powell stated that further increases may be necessary to combat persistent inflation. "
            "Wall Street reacted positively to the measured approach.",
            "Samsung Electronics reported revenues of $63 billion for Q3, exceeding analyst expectations. "
            "The semiconductor division led growth with strong demand for memory chips. "
            "CEO Jong-Hee Han credited the company's investment in AI chip technology.",
            "Leaders from 195 countries gathered in Paris for the annual climate summit. "
            "UN Secretary-General Antonio Guterres urged immediate action on carbon emissions. "
            "The European Union proposed a new carbon tax framework.",
            "삼성전자가 3분기 매출 63조원을 기록하며 사상 최대 실적을 달성했다. "
            "반도체 부문이 메모리 칩 수요 증가에 힘입어 성장을 견인했다. "
            "한종희 대표이사는 AI 칩 기술 투자의 성과라고 밝혔다.",
            "한국은행이 기준금리를 0.25%포인트 인상했다. "
            "이창용 총재는 물가 안정을 위해 추가 인상 가능성을 시사했다. "
            "금융시장은 예상된 결정이라며 안정적 반응을 보였다.",
        ],
        "source": ["reuters", "bloomberg", "bbc", "chosun", "yna"],
        "category": ["economy", "tech", "environment", "economy", "economy"],
        "language": ["en", "en", "en", "ko", "ko"],
        "published_at": [
            "2025-01-15T10:00:00Z",
            "2025-01-15T11:00:00Z",
            "2025-01-15T12:00:00Z",
            "2025-01-15T13:00:00Z",
            "2025-01-15T14:00:00Z",
        ],
        "crawled_at": ["2025-01-15T15:00:00Z"] * 5,
        "author": ["John Smith", "Jane Doe", "Alice Brown", "", ""],
        "word_count": [48, 45, 42, 50, 38],
        "content_hash": ["hash1", "hash2", "hash3", "hash4", "hash5"],
    }

    table = pa.table(data, schema=schema)
    parquet_path = tmp_path / "articles.parquet"
    pq.write_table(table, str(parquet_path))
    return parquet_path


@pytest.fixture
def minimal_articles_parquet(tmp_path):
    """Articles Parquet with only required columns (article_id, title)."""
    schema = pa.schema([
        pa.field("article_id", pa.utf8()),
        pa.field("title", pa.utf8()),
    ])
    data = {
        "article_id": ["min-001", "min-002"],
        "title": ["Test article one", "Test article two"],
    }
    table = pa.table(data, schema=schema)
    path = tmp_path / "minimal_articles.parquet"
    pq.write_table(table, str(path))
    return path


@pytest.fixture
def paywall_articles_parquet(tmp_path):
    """Articles with empty bodies (paywall simulation)."""
    schema = pa.schema([
        pa.field("article_id", pa.utf8()),
        pa.field("title", pa.utf8()),
        pa.field("body", pa.utf8()),
        pa.field("language", pa.utf8()),
    ])
    data = {
        "article_id": ["pw-001", "pw-002"],
        "title": ["Paywall article title one", "Paywall article title two"],
        "body": ["", ""],
        "language": ["en", "en"],
    }
    table = pa.table(data, schema=schema)
    path = tmp_path / "paywall_articles.parquet"
    pq.write_table(table, str(path))
    return path


def _mock_sbert_model(embedding_dim=384):
    """Create a mock SentenceTransformer that returns random embeddings."""
    model = MagicMock()
    model.get_sentence_embedding_dimension.return_value = embedding_dim

    def mock_encode(texts, batch_size=64, show_progress_bar=True,
                    normalize_embeddings=True, convert_to_numpy=True):
        n = len(texts)
        rng = np.random.default_rng(42)
        embs = rng.standard_normal((n, embedding_dim)).astype(np.float32)
        # L2 normalize
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embs = embs / norms
        return embs

    model.encode = mock_encode
    return model


def _mock_ner_pipeline():
    """Create a mock transformers NER pipeline."""
    def pipeline_fn(text):
        # Return a fixed set of entities for testing
        entities = []
        if "Samsung" in text or "삼성" in text:
            entities.append({
                "entity_group": "ORG",
                "word": "Samsung Electronics",
                "score": 0.98,
                "start": 0,
                "end": 20,
            })
        if "Federal Reserve" in text:
            entities.append({
                "entity_group": "ORG",
                "word": "Federal Reserve",
                "score": 0.97,
                "start": 0,
                "end": 15,
            })
        if "Jerome Powell" in text:
            entities.append({
                "entity_group": "PER",
                "word": "Jerome Powell",
                "score": 0.96,
                "start": 0,
                "end": 13,
            })
        if "Paris" in text:
            entities.append({
                "entity_group": "LOC",
                "word": "Paris",
                "score": 0.95,
                "start": 0,
                "end": 5,
            })
        if "Antonio Guterres" in text:
            entities.append({
                "entity_group": "PER",
                "word": "Antonio Guterres",
                "score": 0.94,
                "start": 0,
                "end": 16,
            })
        if "European Union" in text:
            entities.append({
                "entity_group": "ORG",
                "word": "European Union",
                "score": 0.93,
                "start": 0,
                "end": 14,
            })
        return entities

    return pipeline_fn


def _mock_keybert():
    """Create a mock KeyBERT instance."""
    kw_model = MagicMock()

    def mock_extract(text, keyphrase_ngram_range=(1, 2), top_n=10,
                     use_mmr=True, diversity=0.5):
        # Return simple keywords based on text content
        words = text.lower().split()[:top_n]
        return [(w, 0.5 + i * 0.01) for i, w in enumerate(words) if len(w) > 3]

    kw_model.extract_keywords = mock_extract
    return kw_model


# ===========================================================================
# Text Helper Tests
# ===========================================================================

class TestLanguageDetection:
    """Test the heuristic language detector."""

    def test_english_text(self):
        assert _detect_language("The quick brown fox jumps over the lazy dog") == "en"

    def test_korean_text(self):
        assert _detect_language("한국은행이 기준금리를 인상했다") == "ko"

    def test_mixed_mostly_korean(self):
        # 70% Korean characters
        text = "삼성전자가 AI chip 기술에 투자했다"
        assert _detect_language(text) == "ko"

    def test_empty_text(self):
        assert _detect_language("") == "en"

    def test_whitespace_only(self):
        assert _detect_language("   ") == "en"

    def test_numbers_only(self):
        assert _detect_language("12345 67890") == "en"


class TestEntityNormalization:
    """Test entity name normalization."""

    def test_strip_whitespace(self):
        assert _normalize_entity_name("  Samsung  ") == "Samsung"

    def test_remove_mr_prefix(self):
        assert _normalize_entity_name("Mr. John Smith") == "John Smith"

    def test_remove_dr_prefix(self):
        assert _normalize_entity_name("Dr. Jane Doe") == "Jane Doe"

    def test_remove_ms_prefix(self):
        assert _normalize_entity_name("Ms. Alice") == "Alice"

    def test_collapse_whitespace(self):
        assert _normalize_entity_name("Samsung   Electronics") == "Samsung Electronics"

    def test_no_change_needed(self):
        assert _normalize_entity_name("Google") == "Google"

    def test_empty_string(self):
        assert _normalize_entity_name("") == ""


class TestEntityDeduplication:
    """Test entity deduplication with substring merging."""

    def test_exact_duplicates(self):
        result = _deduplicate_entities(["Samsung", "Samsung"])
        assert result == ["Samsung"]

    def test_case_insensitive(self):
        result = _deduplicate_entities(["samsung", "Samsung"])
        # Keeps the longer form (same length -> first occurrence)
        assert len(result) == 1

    def test_substring_merge_keeps_longer(self):
        result = _deduplicate_entities(["Samsung", "Samsung Electronics"])
        assert "Samsung Electronics" in result
        assert len(result) == 1

    def test_no_duplicates(self):
        result = _deduplicate_entities(["Apple", "Google", "Samsung"])
        assert len(result) == 3

    def test_empty_list(self):
        assert _deduplicate_entities([]) == []

    def test_filters_empty_strings(self):
        result = _deduplicate_entities(["Apple", "", "  "])
        assert result == ["Apple"]


# ===========================================================================
# Schema Tests
# ===========================================================================

class TestParquetSchemas:
    """Verify Parquet schemas match PRD section 7.1 specification."""

    def test_embeddings_schema_columns(self):
        schema = _embeddings_schema()
        names = schema.names
        assert names == ["article_id", "embedding", "title_embedding", "keywords"]

    def test_embeddings_schema_types(self):
        schema = _embeddings_schema()
        assert schema.field("article_id").type == pa.utf8()
        assert schema.field("embedding").type == pa.list_(pa.float32())
        assert schema.field("title_embedding").type == pa.list_(pa.float32())
        assert schema.field("keywords").type == pa.list_(pa.utf8())

    def test_embeddings_schema_not_nullable(self):
        schema = _embeddings_schema()
        for field in schema:
            assert not field.nullable, f"{field.name} should not be nullable"

    def test_tfidf_schema_columns(self):
        schema = _tfidf_schema()
        assert schema.names == ["article_id", "tfidf_top_terms", "tfidf_scores"]

    def test_tfidf_schema_types(self):
        schema = _tfidf_schema()
        assert schema.field("tfidf_top_terms").type == pa.list_(pa.utf8())
        assert schema.field("tfidf_scores").type == pa.list_(pa.float32())

    def test_ner_schema_columns(self):
        schema = _ner_schema()
        assert schema.names == [
            "article_id", "entities_person", "entities_org", "entities_location",
        ]

    def test_ner_schema_types(self):
        schema = _ner_schema()
        assert schema.field("entities_person").type == pa.list_(pa.utf8())
        assert schema.field("entities_org").type == pa.list_(pa.utf8())
        assert schema.field("entities_location").type == pa.list_(pa.utf8())


# ===========================================================================
# SBERT Component Tests
# ===========================================================================

class TestSBERTEncoder:
    """Test SBERT embedding generation with mock model."""

    def test_encode_batch_produces_correct_shape(self, config):
        encoder = SBERTEncoder(config)
        encoder._model = _mock_sbert_model(384)
        texts = ["Hello world", "Test sentence", "Another one"]
        result = encoder.encode_batch(texts, show_progress=False)
        assert result.shape == (3, 384)
        assert result.dtype == np.float32

    def test_encode_batch_handles_empty_text(self, config):
        encoder = SBERTEncoder(config)
        encoder._model = _mock_sbert_model(384)
        texts = ["Valid text", "", "  ", "Also valid"]
        result = encoder.encode_batch(texts, show_progress=False)
        assert result.shape == (4, 384)
        # Empty texts get zero vectors
        assert np.all(result[1] == 0)
        assert np.all(result[2] == 0)
        # Non-empty texts get non-zero vectors
        assert np.any(result[0] != 0)
        assert np.any(result[3] != 0)

    def test_compute_article_embeddings_body_priority(self, config):
        encoder = SBERTEncoder(config)
        encoder._model = _mock_sbert_model(384)

        ids = ["a1", "a2"]
        titles = ["Title one", "Title two"]
        bodies = ["Body content here", ""]

        results = encoder.compute_article_embeddings(ids, titles, bodies)
        assert "a1" in results
        assert "a2" in results
        # a1 has body -> embedding should be body embedding
        # a2 has no body -> embedding should be title embedding
        assert "embedding" in results["a1"]
        assert "title_embedding" in results["a1"]

    def test_encode_without_load_raises(self, config):
        encoder = SBERTEncoder(config)
        # Model not loaded
        with pytest.raises(PipelineStageError):
            encoder.encode_batch(["test"])

    def test_embeddings_are_normalized(self, config):
        encoder = SBERTEncoder(config)
        encoder._model = _mock_sbert_model(384)
        texts = ["A sentence for encoding"]
        result = encoder.encode_batch(texts, show_progress=False)
        norm = np.linalg.norm(result[0])
        assert abs(norm - 1.0) < 0.01, f"Expected unit norm, got {norm}"

    def test_all_empty_texts(self, config):
        encoder = SBERTEncoder(config)
        encoder._model = _mock_sbert_model(384)
        texts = ["", "", ""]
        result = encoder.encode_batch(texts, show_progress=False)
        assert result.shape == (3, 384)
        assert np.all(result == 0)


# ===========================================================================
# TF-IDF Component Tests
# ===========================================================================

class TestTFIDFExtractor:
    """Test TF-IDF feature extraction."""

    def test_basic_extraction(self, config):
        extractor = TFIDFExtractor(config)
        ids = ["a1", "a2", "a3"]
        texts = [
            "The stock market rose today on strong earnings reports",
            "Interest rates were raised by the central bank committee",
            "Technology stocks declined amid regulatory concerns today",
        ]
        languages = ["en", "en", "en"]

        results = extractor.fit_transform(ids, texts, languages)
        assert len(results) == 3
        for aid in ids:
            assert "terms" in results[aid]
            assert "scores" in results[aid]
            assert len(results[aid]["terms"]) <= config.tfidf_top_terms

    def test_bilingual_separation(self):
        # Use min_df=1 for small test corpus to avoid "no terms remain" error
        cfg = Stage2Config(tfidf_min_df=1)
        extractor = TFIDFExtractor(cfg)
        ids = ["en1", "en2", "ko1", "ko2"]
        texts = [
            "Federal Reserve raises interest rates in the United States",
            "Wall Street reacts to new economic data from Treasury",
            "한국은행이 기준금리를 인상하며 통화정책을 긴축 전환했다",
            "삼성전자 반도체 부문 실적이 시장 기대치를 상회했다",
        ]
        languages = ["en", "en", "ko", "ko"]

        results = extractor.fit_transform(ids, texts, languages)
        assert len(results) == 4
        assert extractor.vocab_size_en > 0
        assert extractor.vocab_size_ko > 0

    def test_empty_corpus(self, config):
        extractor = TFIDFExtractor(config)
        results = extractor.fit_transform([], [], [])
        assert results == {}

    def test_single_document_returns_empty(self, config):
        """TF-IDF needs >=2 documents; single doc should gracefully degrade."""
        extractor = TFIDFExtractor(config)
        results = extractor.fit_transform(
            ["only-one"],
            ["Single document text here"],
            ["en"],
        )
        assert "only-one" in results
        # With only 1 doc, TF-IDF can't compute meaningful scores
        assert results["only-one"]["terms"] == []

    def test_scores_are_descending(self):
        # Use min_df=1 for small test corpus
        cfg = Stage2Config(tfidf_min_df=1)
        extractor = TFIDFExtractor(cfg)
        ids = [f"a{i}" for i in range(10)]
        texts = [
            f"Document number {i} about topic {i % 3} with unique word-{i} and extra content"
            for i in range(10)
        ]
        languages = ["en"] * 10

        results = extractor.fit_transform(ids, texts, languages)
        for aid in ids:
            scores = results[aid]["scores"]
            if len(scores) > 1:
                # Scores should be in descending order
                for j in range(len(scores) - 1):
                    assert scores[j] >= scores[j + 1], (
                        f"Scores not descending for {aid}: {scores}"
                    )


# ===========================================================================
# NER Component Tests
# ===========================================================================

class TestNERExtractor:
    """Test NER extraction with mock pipeline."""

    def test_transformers_backend(self, config):
        extractor = NERExtractor(config)
        extractor._pipeline = _mock_ner_pipeline()
        extractor._backend = "transformers"

        results = extractor.extract_batch(
            ["a1"],
            ["The Federal Reserve led by Jerome Powell meets in Paris"],
        )
        assert "a1" in results
        assert "Jerome Powell" in results["a1"]["person"]
        assert "Federal Reserve" in results["a1"]["org"]
        assert "Paris" in results["a1"]["location"]

    def test_empty_text_returns_empty_entities(self, config):
        extractor = NERExtractor(config)
        extractor._pipeline = _mock_ner_pipeline()
        extractor._backend = "transformers"

        results = extractor.extract_batch(["a1"], [""])
        assert results["a1"] == {"person": [], "org": [], "location": []}

    def test_disabled_backend_returns_empty(self, config):
        extractor = NERExtractor(config)
        extractor._backend = "none"

        results = extractor.extract_batch(
            ["a1", "a2"],
            ["Some text", "More text"],
        )
        for aid in ["a1", "a2"]:
            assert results[aid] == {"person": [], "org": [], "location": []}

    def test_entity_deduplication_in_ner(self, config):
        """NER should deduplicate entities within each type."""
        extractor = NERExtractor(config)

        # Custom mock that returns duplicates
        def dup_pipeline(text):
            return [
                {"entity_group": "ORG", "word": "Samsung", "score": 0.9, "start": 0, "end": 7},
                {"entity_group": "ORG", "word": "Samsung Electronics", "score": 0.95, "start": 0, "end": 20},
            ]

        extractor._pipeline = dup_pipeline
        extractor._backend = "transformers"

        results = extractor.extract_batch(["a1"], ["Samsung Electronics reported..."])
        # Should merge "Samsung" into "Samsung Electronics"
        assert len(results["a1"]["org"]) == 1
        assert "Samsung Electronics" in results["a1"]["org"]

    def test_batch_processing(self, config):
        extractor = NERExtractor(config)
        extractor._pipeline = _mock_ner_pipeline()
        extractor._backend = "transformers"

        ids = [f"a{i}" for i in range(50)]
        texts = ["Samsung Electronics reported profits in Paris"] * 50

        results = extractor.extract_batch(ids, texts)
        assert len(results) == 50

    def test_unload(self, config):
        extractor = NERExtractor(config)
        extractor._pipeline = _mock_ner_pipeline()
        extractor._backend = "transformers"

        extractor.unload()
        assert extractor._pipeline is None
        assert extractor._backend == "none"


# ===========================================================================
# KeyBERT Component Tests
# ===========================================================================

class TestKeyBERTExtractor:
    """Test KeyBERT keyword extraction with mock model."""

    def test_basic_extraction(self, config):
        extractor = KeyBERTExtractor(config)
        extractor._kw_model = _mock_keybert()

        results = extractor.extract_keywords(
            ["a1"],
            ["The Federal Reserve raises interest rates for economic stability"],
        )
        assert "a1" in results
        assert len(results["a1"]) > 0

    def test_empty_text_uses_fallback(self, config):
        extractor = KeyBERTExtractor(config)
        extractor._kw_model = _mock_keybert()

        fallback = {"a1": {"terms": ["fallback_term_1", "fallback_term_2"], "scores": [0.5, 0.3]}}
        results = extractor.extract_keywords(["a1"], [""], tfidf_fallback=fallback)
        assert results["a1"] == ["fallback_term_1", "fallback_term_2"]

    def test_fallback_on_error(self, config):
        extractor = KeyBERTExtractor(config)

        # Mock that raises an exception
        mock_kw = MagicMock()
        mock_kw.extract_keywords.side_effect = RuntimeError("KeyBERT failed")
        extractor._kw_model = mock_kw

        fallback = {"a1": {"terms": ["backup_keyword"], "scores": [0.5]}}
        results = extractor.extract_keywords(
            ["a1"],
            ["Some text that will fail"],
            tfidf_fallback=fallback,
        )
        assert results["a1"] == ["backup_keyword"]

    def test_no_model_uses_fallback(self, config):
        extractor = KeyBERTExtractor(config)
        extractor._kw_model = None  # Not loaded

        results = extractor.extract_keywords(
            ["a1"],
            ["Test text"],
            tfidf_fallback=None,
        )
        assert results["a1"] == []

    def test_unload(self, config):
        extractor = KeyBERTExtractor(config)
        extractor._kw_model = _mock_keybert()
        extractor.unload()
        assert extractor._kw_model is None


# ===========================================================================
# Stage2Config Tests
# ===========================================================================

class TestStage2Config:
    """Test configuration dataclass defaults."""

    def test_default_values(self):
        config = Stage2Config()
        assert config.sbert_model_name == "paraphrase-multilingual-MiniLM-L12-v2"
        assert config.sbert_batch_size == 64
        assert config.sbert_embedding_dim == 384
        assert config.tfidf_max_features == 10000
        assert config.tfidf_ngram_range == (1, 2)
        assert config.keybert_top_n == 10
        assert config.ner_batch_size == 32

    def test_override_values(self):
        config = Stage2Config(sbert_batch_size=32, keybert_top_n=5)
        assert config.sbert_batch_size == 32
        assert config.keybert_top_n == 5
        # Other values unchanged
        assert config.sbert_embedding_dim == 384


# ===========================================================================
# Integration Tests: Full Stage 2 Pipeline (with mocks)
# ===========================================================================

class TestStage2Integration:
    """Integration test: full pipeline run with mocked models."""

    def _run_with_mocks(self, articles_path, output_dir, config=None):
        """Helper to run Stage 2 with all models mocked."""
        cfg = config or Stage2Config()
        extractor = Stage2FeatureExtractor(config=cfg)

        # Replace component internals with mocks
        mock_sbert = _mock_sbert_model(cfg.sbert_embedding_dim)
        extractor._sbert._model = mock_sbert

        extractor._ner._pipeline = _mock_ner_pipeline()
        extractor._ner._backend = "transformers"

        extractor._keybert._kw_model = _mock_keybert()

        # Patch load methods to avoid real model downloads
        extractor._sbert.load = lambda: None
        extractor._ner.load = lambda: None
        extractor._keybert.load = lambda sbert_model: None

        # Patch the model property for keybert sharing
        type(extractor._sbert).model = PropertyMock(return_value=mock_sbert)

        return extractor.run(articles_path=articles_path, output_dir=output_dir)

    def test_full_pipeline_produces_three_files(
        self, sample_articles_parquet, tmp_output_dir,
    ):
        """Stage 2 should produce embeddings.parquet, tfidf.parquet, ner.parquet."""
        metrics = self._run_with_mocks(sample_articles_parquet, tmp_output_dir)

        assert (tmp_output_dir / "embeddings.parquet").exists()
        assert (tmp_output_dir / "tfidf.parquet").exists()
        assert (tmp_output_dir / "ner.parquet").exists()

    def test_article_id_coverage(
        self, sample_articles_parquet, tmp_output_dir,
    ):
        """All article_ids from input must appear in every output file."""
        self._run_with_mocks(sample_articles_parquet, tmp_output_dir)

        # Read input IDs
        input_table = pq.read_table(str(sample_articles_parquet))
        input_ids = set(input_table.column("article_id").to_pylist())

        # Check each output
        for fname in ["embeddings.parquet", "tfidf.parquet", "ner.parquet"]:
            out_table = pq.read_table(str(tmp_output_dir / fname))
            out_ids = set(out_table.column("article_id").to_pylist())
            assert out_ids == input_ids, f"ID mismatch in {fname}"

    def test_embeddings_dimensions_consistent(
        self, sample_articles_parquet, tmp_output_dir,
    ):
        """All embeddings must have exactly 384 dimensions."""
        self._run_with_mocks(sample_articles_parquet, tmp_output_dir)

        table = pq.read_table(str(tmp_output_dir / "embeddings.parquet"))
        for i in range(table.num_rows):
            emb = table.column("embedding")[i].as_py()
            title_emb = table.column("title_embedding")[i].as_py()
            assert len(emb) == 384, f"Row {i}: embedding has {len(emb)} dims"
            assert len(title_emb) == 384, f"Row {i}: title_embedding has {len(title_emb)} dims"

    def test_keywords_are_lists_of_strings(
        self, sample_articles_parquet, tmp_output_dir,
    ):
        """Keywords column should contain lists of strings."""
        self._run_with_mocks(sample_articles_parquet, tmp_output_dir)

        table = pq.read_table(str(tmp_output_dir / "embeddings.parquet"))
        for i in range(table.num_rows):
            kws = table.column("keywords")[i].as_py()
            assert isinstance(kws, list)
            for kw in kws:
                assert isinstance(kw, str)

    def test_tfidf_terms_and_scores_aligned(
        self, sample_articles_parquet, tmp_output_dir,
    ):
        """TF-IDF terms and scores lists must have equal length per row."""
        self._run_with_mocks(sample_articles_parquet, tmp_output_dir)

        table = pq.read_table(str(tmp_output_dir / "tfidf.parquet"))
        for i in range(table.num_rows):
            terms = table.column("tfidf_top_terms")[i].as_py()
            scores = table.column("tfidf_scores")[i].as_py()
            assert len(terms) == len(scores), (
                f"Row {i}: terms ({len(terms)}) != scores ({len(scores)})"
            )

    def test_ner_entity_types(
        self, sample_articles_parquet, tmp_output_dir,
    ):
        """NER output should have all three entity type columns."""
        self._run_with_mocks(sample_articles_parquet, tmp_output_dir)

        table = pq.read_table(str(tmp_output_dir / "ner.parquet"))
        assert "entities_person" in table.schema.names
        assert "entities_org" in table.schema.names
        assert "entities_location" in table.schema.names

    def test_metrics_populated(
        self, sample_articles_parquet, tmp_output_dir,
    ):
        """Metrics should reflect processing statistics."""
        metrics = self._run_with_mocks(sample_articles_parquet, tmp_output_dir)

        assert metrics.total_articles == 5
        assert metrics.embedding_time_s >= 0
        assert metrics.tfidf_time_s >= 0
        assert metrics.ner_time_s >= 0
        assert metrics.keybert_time_s >= 0
        assert metrics.total_time_s > 0

    def test_output_schema_compliance(
        self, sample_articles_parquet, tmp_output_dir,
    ):
        """Output Parquet files must exactly match defined schemas."""
        self._run_with_mocks(sample_articles_parquet, tmp_output_dir)

        # Embeddings schema
        emb_table = pq.read_table(str(tmp_output_dir / "embeddings.parquet"))
        expected_emb = _embeddings_schema()
        assert emb_table.schema.equals(expected_emb), (
            f"Embeddings schema mismatch:\n"
            f"  Expected: {expected_emb}\n"
            f"  Got: {emb_table.schema}"
        )

        # TF-IDF schema
        tfidf_table = pq.read_table(str(tmp_output_dir / "tfidf.parquet"))
        expected_tfidf = _tfidf_schema()
        assert tfidf_table.schema.equals(expected_tfidf), (
            f"TF-IDF schema mismatch:\n"
            f"  Expected: {expected_tfidf}\n"
            f"  Got: {tfidf_table.schema}"
        )

        # NER schema
        ner_table = pq.read_table(str(tmp_output_dir / "ner.parquet"))
        expected_ner = _ner_schema()
        assert ner_table.schema.equals(expected_ner), (
            f"NER schema mismatch:\n"
            f"  Expected: {expected_ner}\n"
            f"  Got: {ner_table.schema}"
        )


# ===========================================================================
# Edge Case Tests
# ===========================================================================

class TestEdgeCases:
    """Test boundary conditions and error handling."""

    def test_missing_parquet_raises_file_not_found(self, tmp_path, tmp_output_dir):
        """Non-existent input should raise FileNotFoundError."""
        fake_path = tmp_path / "nonexistent.parquet"
        extractor = Stage2FeatureExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.run(articles_path=fake_path, output_dir=tmp_output_dir)

    def test_missing_required_columns_raises(self, tmp_path, tmp_output_dir):
        """Parquet without article_id should raise PipelineStageError."""
        schema = pa.schema([pa.field("wrong_column", pa.utf8())])
        table = pa.table({"wrong_column": ["val"]}, schema=schema)
        path = tmp_path / "bad_articles.parquet"
        pq.write_table(table, str(path))

        extractor = Stage2FeatureExtractor()
        with pytest.raises(PipelineStageError):
            extractor.run(articles_path=path, output_dir=tmp_output_dir)

    def test_empty_parquet_writes_empty_outputs(self, tmp_path, tmp_output_dir):
        """Zero-row input should produce zero-row valid Parquet outputs."""
        schema = pa.schema([
            pa.field("article_id", pa.utf8()),
            pa.field("title", pa.utf8()),
            pa.field("body", pa.utf8()),
            pa.field("language", pa.utf8()),
        ])
        table = pa.table(
            {f.name: pa.array([], type=f.type) for f in schema},
            schema=schema,
        )
        path = tmp_path / "empty_articles.parquet"
        pq.write_table(table, str(path))

        extractor = Stage2FeatureExtractor()
        metrics = extractor.run(articles_path=path, output_dir=tmp_output_dir)

        assert metrics.total_articles == 0
        for fname in ["embeddings.parquet", "tfidf.parquet", "ner.parquet"]:
            out = pq.read_table(str(tmp_output_dir / fname))
            assert out.num_rows == 0

    def test_paywall_articles_use_title_embedding(
        self, paywall_articles_parquet, tmp_output_dir,
    ):
        """Articles with empty body should use title embedding as combined."""
        cfg = Stage2Config()
        extractor = Stage2FeatureExtractor(config=cfg)

        mock_sbert = _mock_sbert_model(384)
        extractor._sbert._model = mock_sbert
        extractor._sbert.load = lambda: None
        extractor._ner._backend = "none"
        extractor._keybert._kw_model = None
        extractor._ner.load = lambda: None
        extractor._keybert.load = lambda m: None
        type(extractor._sbert).model = PropertyMock(return_value=mock_sbert)

        metrics = extractor.run(
            articles_path=paywall_articles_parquet,
            output_dir=tmp_output_dir,
        )

        table = pq.read_table(str(tmp_output_dir / "embeddings.parquet"))
        for i in range(table.num_rows):
            emb = np.array(table.column("embedding")[i].as_py())
            title_emb = np.array(table.column("title_embedding")[i].as_py())
            # For paywall articles, combined embedding equals title embedding
            np.testing.assert_array_equal(emb, title_emb)

    def test_minimal_schema_auto_detects_language(
        self, minimal_articles_parquet, tmp_output_dir,
    ):
        """Without language column, should auto-detect from content."""
        cfg = Stage2Config()
        extractor = Stage2FeatureExtractor(config=cfg)

        mock_sbert = _mock_sbert_model(384)
        extractor._sbert._model = mock_sbert
        extractor._sbert.load = lambda: None
        extractor._ner._backend = "none"
        extractor._keybert._kw_model = None
        extractor._ner.load = lambda: None
        extractor._keybert.load = lambda m: None
        type(extractor._sbert).model = PropertyMock(return_value=mock_sbert)

        metrics = extractor.run(
            articles_path=minimal_articles_parquet,
            output_dir=tmp_output_dir,
        )

        assert metrics.total_articles == 2
        assert (tmp_output_dir / "embeddings.parquet").exists()


# ===========================================================================
# SBERT Singleton Tests
# ===========================================================================

class TestSBERTSingleton:
    """Test the module-level SBERT singleton management."""

    def test_unload_clears_singleton(self):
        """unload_sbert_model should clear the global singleton."""
        import src.analysis.stage2_features as mod
        # Set fake singleton
        mod._sbert_instance = "fake_model"
        mod._sbert_model_name = "fake"

        unload_sbert_model()

        assert mod._sbert_instance is None
        assert mod._sbert_model_name is None


# ===========================================================================
# Convenience Function Test
# ===========================================================================

class TestConvenienceFunction:
    """Test the run_stage2() module-level function."""

    def test_run_stage2_delegates_to_extractor(self, tmp_path):
        """run_stage2 should create an extractor and call run()."""
        # Create minimal input
        schema = pa.schema([
            pa.field("article_id", pa.utf8()),
            pa.field("title", pa.utf8()),
        ])
        table = pa.table(
            {"article_id": pa.array([], type=pa.utf8()),
             "title": pa.array([], type=pa.utf8())},
            schema=schema,
        )
        path = tmp_path / "articles.parquet"
        pq.write_table(table, str(path))

        out = tmp_path / "features"
        out.mkdir()

        metrics = run_stage2(articles_path=path, output_dir=out)
        assert isinstance(metrics, Stage2Metrics)
        assert metrics.total_articles == 0
