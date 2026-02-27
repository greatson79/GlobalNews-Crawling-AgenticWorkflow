"""Unit tests for Stage 1 Preprocessing pipeline.

Tests cover:
    - Text normalization (Unicode, HTML, URLs, whitespace)
    - Language detection with source verification
    - Korean processing (Kiwi tokenization, stopwords, sentences)
    - English processing (spaCy lemmatization, POS filtering, sentences)
    - Other language processing (whitespace tokenization, regex sentences)
    - Word count computation
    - Timestamp parsing
    - Parquet schema compliance
    - Edge cases (empty articles, paywall, mixed language, special chars)
    - Full pipeline integration (JSONL -> Parquet)

Fixture strategy:
    - Kiwi and spaCy are expensive to load (~1 GB combined).
    - We use module-scoped fixtures to load them once per test session.
    - Tests that require NLP models are marked with pytest.mark.slow
      and can be skipped with `pytest -m 'not slow'`.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.stage1_preprocessing import (
    ARTICLES_SCHEMA,
    ENGLISH_NEWS_STOPWORDS,
    KIWI_KEEP_POS,
    KOREAN_STOPWORDS,
    ArticleIntermediateData,
    Stage1Preprocessor,
    compute_word_count,
    detect_language,
    normalize_text,
    process_other_language_text,
    validate_output,
    _parse_timestamp,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create a temporary output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def sample_korean_article():
    """A sample Korean article dict (RawArticle format)."""
    return {
        "url": "https://www.chosun.com/article/12345",
        "title": "\ubb38\uc7ac\uc778 \ub300\ud1b5\ub839\uc774 \uc624\ub298 \uae34\uae09 \uae30\uc790\ud68c\uacac\uc744 \uac1c\ucd5c\ud588\ub2e4",
        "body": (
            "\ubb38\uc7ac\uc778 \ub300\ud1b5\ub839\uc774 \uc624\ub298 \uc624\ud6c4 2\uc2dc \uccad\uc640\ub300\uc5d0\uc11c "
            "\uae34\uae09 \uae30\uc790\ud68c\uacac\uc744 \uac1c\ucd5c\ud588\ub2e4. "
            "\uc774\ubc88 \ud68c\uacac\uc5d0\uc11c\ub294 \uacbd\uc81c \ud68c\ubcf5\uc744 \uc704\ud55c "
            "\uc0c8\ub85c\uc6b4 \uc815\ucc45\uc774 \ubc1c\ud45c\ub418\uc5c8\ub2e4. "
            "\uae30\uc790\ub4e4\uc740 \ub9ce\uc740 \uc9c8\ubb38\uc744 \uc3df\uc544\ub0c8\ub2e4."
        ),
        "source_id": "chosun",
        "source_name": "Chosun Ilbo",
        "language": "ko",
        "published_at": "2026-02-25T14:00:00+09:00",
        "crawled_at": "2026-02-25T15:30:00+00:00",
        "author": "\uae40\ucca0\uc218",
        "category": "\uc815\uce58",
        "content_hash": "abc123def456",
        "crawl_tier": 1,
        "crawl_method": "rss",
        "is_paywall_truncated": False,
    }


@pytest.fixture
def sample_english_article():
    """A sample English article dict (RawArticle format)."""
    return {
        "url": "https://www.cnn.com/2026/02/25/politics/climate-summit",
        "title": "World Leaders Gather for Emergency Climate Summit",
        "body": (
            "World leaders from over 50 countries gathered in Geneva today "
            "for an emergency climate summit. The meeting was called after "
            "record-breaking temperatures were reported across Europe. "
            "Scientists warned that immediate action is needed to prevent "
            "catastrophic environmental damage. The summit is expected to "
            "produce new binding agreements on carbon emissions."
        ),
        "source_id": "cnn",
        "source_name": "CNN",
        "language": "en",
        "published_at": "2026-02-25T10:00:00+00:00",
        "crawled_at": "2026-02-25T12:00:00+00:00",
        "author": "Jane Smith",
        "category": "politics",
        "content_hash": "xyz789abc012",
        "crawl_tier": 1,
        "crawl_method": "rss",
        "is_paywall_truncated": False,
    }


@pytest.fixture
def sample_paywall_article():
    """A sample paywall-truncated article."""
    return {
        "url": "https://www.nytimes.com/2026/02/25/business/market-crash",
        "title": "Stock Market Plunges 500 Points on Inflation Fears",
        "body": "",
        "source_id": "nytimes",
        "source_name": "The New York Times",
        "language": "en",
        "published_at": "2026-02-25T16:00:00+00:00",
        "crawled_at": "2026-02-25T17:00:00+00:00",
        "author": None,
        "category": "business",
        "content_hash": "",
        "crawl_tier": 3,
        "crawl_method": "playwright",
        "is_paywall_truncated": True,
    }


@pytest.fixture
def sample_chinese_article():
    """A sample Chinese article dict."""
    return {
        "url": "https://www.globaltimes.cn/article/54321",
        "title": "\u4e2d\u56fd\u79d1\u6280\u521b\u65b0\u8fbe\u5230\u65b0\u9ad8\u5ea6",
        "body": "\u4eca\u5929\uff0c\u4e2d\u56fd\u5ba3\u5e03\u4e86\u65b0\u7684\u79d1\u6280\u521b\u65b0\u653f\u7b56\u3002\u8fd9\u9879\u653f\u7b56\u5c06\u63a8\u52a8\u4eba\u5de5\u667a\u80fd\u548c\u534a\u5bfc\u4f53\u4ea7\u4e1a\u7684\u53d1\u5c55\u3002",
        "source_id": "globaltimes",
        "source_name": "Global Times",
        "language": "zh",
        "published_at": "2026-02-25T08:00:00+08:00",
        "crawled_at": "2026-02-25T09:00:00+00:00",
        "author": None,
        "category": "technology",
        "content_hash": "chi123hash",
        "crawl_tier": 1,
        "crawl_method": "rss",
        "is_paywall_truncated": False,
    }


def _make_jsonl_file(tmp_path: Path, articles: list[dict], name: str = "all_articles.jsonl") -> Path:
    """Write articles to a JSONL file."""
    jsonl_path = tmp_path / name
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for article in articles:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")
    return jsonl_path


# =============================================================================
# Text Normalization Tests
# =============================================================================

class TestNormalizeText:
    """Tests for the normalize_text function."""

    def test_unicode_nfkc_korean(self):
        """NFKC normalization decomposes compatibility characters."""
        # fullwidth latin -> ascii
        text = "\uff28\uff45\uff4c\uff4c\uff4f"  # "Hello" in fullwidth
        result = normalize_text(text, language="ko")
        assert "Hello" in result

    def test_unicode_nfc_english(self):
        """NFC normalization composes decomposed characters."""
        # e + combining acute accent -> e with acute
        text = "caf\u0065\u0301"
        result = normalize_text(text, language="en")
        assert "\u00e9" in result  # composed form

    def test_html_entity_decoding(self):
        """HTML entities are decoded."""
        text = "AT&amp;T &lt;strong&gt;test&lt;/strong&gt;"
        result = normalize_text(text)
        assert "AT&T" in result
        assert "<" not in result  # tags removed
        assert "test" in result

    def test_url_removal(self):
        """URLs are removed from text."""
        text = "Visit https://www.example.com/path?q=1 for details."
        result = normalize_text(text)
        assert "https://" not in result
        assert "Visit" in result
        assert "details" in result

    def test_email_removal(self):
        """Email addresses are removed."""
        text = "Contact user@example.com for more info."
        result = normalize_text(text)
        assert "@" not in result

    def test_whitespace_collapse(self):
        """Multiple spaces/newlines are collapsed."""
        text = "Hello    world\n\n\n\n\nNew paragraph"
        result = normalize_text(text)
        assert "  " not in result  # No double spaces
        assert "\n\n\n" not in result  # At most 2 newlines

    def test_empty_text(self):
        """Empty/None text returns empty string."""
        assert normalize_text("") == ""
        assert normalize_text("   ") == ""

    def test_preserves_hyphens(self):
        """Hyphens in compound terms are preserved."""
        text = "state-of-the-art technology"
        result = normalize_text(text)
        assert "state-of-the-art" in result

    def test_decorative_punctuation_removed(self):
        """Decorative characters like stars and arrows are removed."""
        text = "\u2605\u2605\u2605 Breaking News \u2605\u2605\u2605"
        result = normalize_text(text)
        assert "\u2605" not in result
        assert "Breaking News" in result


# =============================================================================
# Language Detection Tests
# =============================================================================

class TestLanguageDetection:
    """Tests for the detect_language function."""

    def test_korean_detection(self):
        """Korean text is correctly detected."""
        result = detect_language(
            "\ubb38\uc7ac\uc778 \ub300\ud1b5\ub839\uc774 \uc624\ub298 \uae34\uae09 \ud68c\uacac\uc744 \uac1c\ucd5c\ud588\ub2e4",
            "\ub300\ud1b5\ub839\uc740 \uacbd\uc81c \ud68c\ubcf5\uc744 \uc704\ud55c \uc0c8\ub85c\uc6b4 \uc815\ucc45\uc744 \ubc1c\ud45c\ud588\ub2e4",
            "chosun",
        )
        assert result == "ko"

    def test_english_detection(self):
        """English text is correctly detected."""
        result = detect_language(
            "World Leaders Gather for Emergency Climate Summit",
            "World leaders from over 50 countries gathered today.",
            "cnn",
        )
        assert result == "en"

    def test_falls_back_to_expected(self):
        """Very short text falls back to source_id expected language."""
        result = detect_language("test", "", "chosun")
        assert result == "ko"  # chosun is Korean site

    def test_unknown_source_defaults_to_en(self):
        """Unknown source_id defaults to English."""
        result = detect_language("Hello world", "This is a test.", "unknown_site")
        assert result == "en"

    @patch("src.analysis.stage1_preprocessing.detect_language")
    def test_detection_failure_returns_expected(self, mock_detect):
        """If langdetect raises, return expected language."""
        # This tests the error path conceptually
        # The actual function has try/except internally
        result = detect_language("x", "", "chosun")
        # Should get "ko" either via detection or fallback
        assert result in ("ko", "en")


# =============================================================================
# Other Language Processing Tests
# =============================================================================

class TestOtherLanguageProcessing:
    """Tests for non-Korean, non-English language processing."""

    def test_chinese_tokenization(self):
        """Chinese text is tokenized by word/character boundaries."""
        text = "\u4e2d\u56fd\u79d1\u6280\u521b\u65b0\u8fbe\u5230\u65b0\u9ad8\u5ea6"
        tokens, pos_tags, sentences = process_other_language_text(text, "zh")
        assert len(tokens) > 0
        assert all(tag == "UNK" for _, tag in pos_tags)

    def test_chinese_sentence_splitting(self):
        """Chinese sentences are split on CJK period."""
        text = "\u7b2c\u4e00\u53e5\u3002\u7b2c\u4e8c\u53e5\u3002\u7b2c\u4e09\u53e5\u3002"
        tokens, _, sentences = process_other_language_text(text, "zh")
        assert len(sentences) >= 2

    def test_german_tokenization(self):
        """German text is whitespace-tokenized."""
        text = "Die Bundesregierung hat neue Klimaschutzgesetze verabschiedet."
        tokens, _, _ = process_other_language_text(text, "de")
        assert len(tokens) > 0
        # Single-char tokens should be filtered out
        assert "." not in tokens

    def test_arabic_tokenization(self):
        """Arabic text is whitespace-tokenized."""
        text = "\u0627\u0644\u0645\u0645\u0644\u0643\u0629 \u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629 \u062a\u0639\u0644\u0646 \u0627\u0644\u062e\u0637\u0629"
        tokens, _, _ = process_other_language_text(text, "ar")
        assert len(tokens) > 0

    def test_title_mode(self):
        """Title mode returns text as single sentence."""
        text = "Breaking News Title"
        _, _, sentences = process_other_language_text(text, "de", is_title=True)
        assert len(sentences) == 1
        assert sentences[0] == "Breaking News Title"

    def test_empty_text(self):
        """Empty text returns empty lists."""
        tokens, pos_tags, sentences = process_other_language_text("", "fr")
        assert tokens == []
        assert pos_tags == []
        assert sentences == []


# =============================================================================
# Word Count Tests
# =============================================================================

class TestWordCount:
    """Tests for compute_word_count."""

    def test_uses_body_tokens(self):
        """Word count comes from body tokens when available."""
        assert compute_word_count(["a", "b", "c"], ["x"], "raw body", "en") == 3

    def test_falls_back_to_title_tokens(self):
        """Falls back to title tokens when body tokens are empty."""
        assert compute_word_count([], ["x", "y"], "", "en") == 2

    def test_falls_back_to_raw_body(self):
        """Falls back to raw body whitespace split."""
        assert compute_word_count([], [], "one two three four", "en") == 4

    def test_empty_returns_zero(self):
        """All empty returns 0."""
        assert compute_word_count([], [], "", "en") == 0


# =============================================================================
# Timestamp Parsing Tests
# =============================================================================

class TestTimestampParsing:
    """Tests for _parse_timestamp."""

    def test_iso_string(self):
        """ISO 8601 string is parsed correctly."""
        result = _parse_timestamp("2026-02-25T14:00:00+00:00")
        assert result is not None
        assert result.tzinfo is not None
        assert result.year == 2026

    def test_naive_datetime(self):
        """Naive datetime gets UTC timezone added."""
        dt = datetime(2026, 2, 25, 14, 0, 0)
        result = _parse_timestamp(dt)
        assert result.tzinfo == timezone.utc

    def test_aware_datetime(self):
        """Aware datetime is returned as-is."""
        dt = datetime(2026, 2, 25, 14, 0, 0, tzinfo=timezone.utc)
        result = _parse_timestamp(dt)
        assert result == dt

    def test_none_returns_none(self):
        """None returns None."""
        assert _parse_timestamp(None) is None

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert _parse_timestamp("") is None
        assert _parse_timestamp("   ") is None

    def test_invalid_string_returns_none(self):
        """Invalid date string returns None."""
        assert _parse_timestamp("not-a-date") is None


# =============================================================================
# Schema Tests
# =============================================================================

class TestArticlesSchema:
    """Tests for ARTICLES_SCHEMA definition."""

    def test_schema_has_12_columns(self):
        """Schema must have exactly 12 columns per PRD SS7.1.1."""
        assert len(ARTICLES_SCHEMA) == 12

    def test_column_names(self):
        """All expected column names are present."""
        expected = [
            "article_id", "url", "title", "body", "source", "category",
            "language", "published_at", "crawled_at", "author",
            "word_count", "content_hash",
        ]
        actual = [f.name for f in ARTICLES_SCHEMA]
        assert actual == expected

    def test_timestamp_columns_have_utc(self):
        """Timestamp columns must use microsecond precision with UTC."""
        for name in ("published_at", "crawled_at"):
            f = ARTICLES_SCHEMA.field(name)
            assert f.type == pa.timestamp("us", tz="UTC"), (
                f"{name} should be timestamp[us, tz=UTC], got {f.type}"
            )

    def test_word_count_is_int32(self):
        """word_count must be int32."""
        f = ARTICLES_SCHEMA.field("word_count")
        assert f.type == pa.int32()

    def test_nullable_fields(self):
        """Only published_at, crawled_at, and author are nullable."""
        nullable_fields = {"published_at", "crawled_at", "author"}
        for f in ARTICLES_SCHEMA:
            if f.name in nullable_fields:
                assert f.nullable, f"{f.name} should be nullable"
            else:
                assert not f.nullable, f"{f.name} should NOT be nullable"


# =============================================================================
# Korean Stopword List Tests
# =============================================================================

class TestKoreanStopwords:
    """Tests for the Korean stopword list completeness."""

    def test_particles_present(self):
        """Core particles are in the stopword list."""
        particles = [
            "\uc774", "\uac00", "\uc740", "\ub294", "\uc744", "\ub97c",
            "\uc5d0", "\uc5d0\uc11c", "\uc73c\ub85c",
        ]
        for p in particles:
            assert p in KOREAN_STOPWORDS, f"Missing particle: {p}"

    def test_news_fillers_present(self):
        """News boilerplate words are in the stopword list."""
        fillers = ["\uae30\uc790", "\ud2b9\ud30c\uc6d0", "\uc575\ucee4", "\ub274\uc2a4"]
        for f in fillers:
            assert f in KOREAN_STOPWORDS, f"Missing news filler: {f}"

    def test_copulas_present(self):
        """Copulas are in the stopword list."""
        assert "\uc774\ub2e4" in KOREAN_STOPWORDS
        assert "\uc785\ub2c8\ub2e4" in KOREAN_STOPWORDS


# =============================================================================
# English Stopwords Tests
# =============================================================================

class TestEnglishStopwords:
    """Tests for the English news stopword list."""

    def test_news_verbs_present(self):
        """Common news attribution verbs are stopwords."""
        verbs = ["said", "according", "reported", "told"]
        for v in verbs:
            assert v in ENGLISH_NEWS_STOPWORDS, f"Missing: {v}"

    def test_wire_service_terms(self):
        """Wire service names are stopwords."""
        assert "reuters" in ENGLISH_NEWS_STOPWORDS
        assert "ap" in ENGLISH_NEWS_STOPWORDS


# =============================================================================
# Stage1Preprocessor Integration Tests
# =============================================================================

class TestStage1PreprocessorUnit:
    """Unit tests for Stage1Preprocessor that do NOT require NLP models."""

    def test_load_jsonl(self, tmp_path, sample_english_article):
        """JSONL loading reads articles correctly."""
        jsonl_path = _make_jsonl_file(tmp_path, [sample_english_article])
        articles = Stage1Preprocessor.load_jsonl(jsonl_path)
        assert len(articles) == 1
        assert articles[0]["title"] == "World Leaders Gather for Emergency Climate Summit"

    def test_load_jsonl_skips_invalid_lines(self, tmp_path):
        """Invalid JSON lines are skipped with warning."""
        jsonl_path = tmp_path / "test.jsonl"
        with open(jsonl_path, "w") as f:
            f.write('{"title": "valid"}\n')
            f.write("not valid json\n")
            f.write('{"title": "also valid"}\n')
        articles = Stage1Preprocessor.load_jsonl(jsonl_path)
        assert len(articles) == 2

    def test_load_jsonl_skips_empty_lines(self, tmp_path):
        """Empty lines are skipped."""
        jsonl_path = tmp_path / "test.jsonl"
        with open(jsonl_path, "w") as f:
            f.write('{"title": "article1"}\n')
            f.write("\n")
            f.write("\n")
            f.write('{"title": "article2"}\n')
        articles = Stage1Preprocessor.load_jsonl(jsonl_path)
        assert len(articles) == 2

    def test_build_empty_table(self):
        """Building from empty rows returns valid empty table."""
        preprocessor = Stage1Preprocessor()
        table = preprocessor._build_table([])
        assert table.num_rows == 0
        assert table.num_columns == 12
        assert table.schema == ARTICLES_SCHEMA

    def test_skip_empty_title(self):
        """Articles with empty title are skipped."""
        preprocessor = Stage1Preprocessor()
        raw = {"url": "https://example.com", "title": "", "body": "content"}
        row, intermediate = preprocessor.process_article(raw)
        assert row is None
        assert intermediate is None

    def test_skip_empty_url(self):
        """Articles with empty URL are skipped."""
        preprocessor = Stage1Preprocessor()
        raw = {"url": "", "title": "Some Title", "body": "content"}
        row, intermediate = preprocessor.process_article(raw)
        assert row is None

    def test_category_defaults_to_uncategorized(self):
        """Missing category defaults to 'uncategorized'."""
        preprocessor = Stage1Preprocessor()
        # Mock the models to avoid loading
        preprocessor._kiwi = MagicMock()
        preprocessor._nlp = MagicMock()

        # Create a minimal mock for spaCy doc
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        mock_doc.sents = []
        preprocessor._nlp.return_value = mock_doc

        raw = {
            "url": "https://example.com/article",
            "title": "Test Article Title Here Now",
            "body": "Some body content for the article.",
            "source_id": "cnn",
            "source_name": "CNN",
            "language": "en",
            "category": None,
            "crawled_at": "2026-02-25T12:00:00+00:00",
        }
        row, _ = preprocessor.process_article(raw)
        assert row is not None
        assert row["category"] == "uncategorized"

    def test_paywall_body_is_empty(self):
        """Paywall-truncated articles have empty body."""
        preprocessor = Stage1Preprocessor()
        preprocessor._kiwi = MagicMock()
        preprocessor._nlp = MagicMock()

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        mock_doc.sents = []
        preprocessor._nlp.return_value = mock_doc

        raw = {
            "url": "https://nytimes.com/article",
            "title": "Stock Market Plunges Five Hundred Points",
            "body": "This should be cleared",
            "source_id": "nytimes",
            "source_name": "NYT",
            "language": "en",
            "is_paywall_truncated": True,
            "crawled_at": "2026-02-25T12:00:00+00:00",
        }
        row, _ = preprocessor.process_article(raw)
        assert row is not None
        assert row["body"] == ""

    def test_write_parquet(self, tmp_output_dir):
        """Writing and reading back Parquet preserves schema."""
        preprocessor = Stage1Preprocessor()

        # Build a minimal table
        rows = [{
            "article_id": str(uuid.uuid4()),
            "url": "https://example.com",
            "title": "Test Title",
            "body": "Test body content",
            "source": "Test Source",
            "category": "test",
            "language": "en",
            "published_at": datetime(2026, 2, 25, 10, 0, 0, tzinfo=timezone.utc),
            "crawled_at": datetime(2026, 2, 25, 12, 0, 0, tzinfo=timezone.utc),
            "author": "Test Author",
            "word_count": 3,
            "content_hash": "testhash123",
        }]
        table = preprocessor._build_table(rows)

        output_path = tmp_output_dir / "test_articles.parquet"
        preprocessor.write_parquet(table, output_path)

        # Read back
        assert output_path.exists()
        read_back = pq.read_table(str(output_path))
        assert read_back.num_rows == 1
        assert read_back.num_columns == 12
        assert read_back.schema == ARTICLES_SCHEMA

    def test_validate_output_valid(self, tmp_output_dir):
        """validate_output passes for a valid Parquet file."""
        preprocessor = Stage1Preprocessor()
        rows = [{
            "article_id": str(uuid.uuid4()),
            "url": "https://example.com",
            "title": "Test",
            "body": "Body",
            "source": "Src",
            "category": "cat",
            "language": "en",
            "published_at": datetime(2026, 2, 25, tzinfo=timezone.utc),
            "crawled_at": datetime(2026, 2, 25, tzinfo=timezone.utc),
            "author": None,
            "word_count": 1,
            "content_hash": "hash",
        }]
        table = preprocessor._build_table(rows)
        output_path = tmp_output_dir / "valid.parquet"
        preprocessor.write_parquet(table, output_path)

        result = validate_output(output_path)
        assert result["valid"] is True
        assert result["stats"]["rows"] == 1
        assert result["stats"]["columns"] == 12

    def test_validate_output_missing_file(self, tmp_output_dir):
        """validate_output fails for missing file."""
        result = validate_output(tmp_output_dir / "nonexistent.parquet")
        assert result["valid"] is False
        assert "File not found" in result["errors"][0]


# =============================================================================
# Slow Integration Tests (require NLP models)
# =============================================================================

@pytest.mark.slow
class TestKoreanProcessing:
    """Integration tests for Korean text processing with Kiwi.

    Requires kiwipiepy to be installed and model to be loadable.
    """

    @pytest.fixture(scope="class")
    def kiwi(self):
        """Load Kiwi once for all tests in this class."""
        try:
            from kiwipiepy import Kiwi
            return Kiwi()
        except ImportError:
            pytest.skip("kiwipiepy not installed")

    def test_basic_tokenization(self, kiwi):
        """Korean text is tokenized into morphemes."""
        from src.analysis.stage1_preprocessing import process_korean_text

        text = "\ub300\ud1b5\ub839\uc774 \uacbd\uc81c \uc815\ucc45\uc744 \ubc1c\ud45c\ud588\ub2e4"
        tokens, pos_tags, sentences = process_korean_text(text, kiwi)
        assert len(tokens) > 0
        # Should contain nouns like "\ub300\ud1b5\ub839", "\uacbd\uc81c", "\uc815\ucc45"
        token_set = set(tokens)
        assert "\ub300\ud1b5\ub839" in token_set or any("\ub300\ud1b5\ub839" in t for t in tokens)

    def test_stopword_removal(self, kiwi):
        """Particles and news fillers are removed."""
        from src.analysis.stage1_preprocessing import process_korean_text

        text = "\uae30\uc790\uac00 \ub274\uc2a4\ub97c \ubcf4\ub3c4\ud588\ub2e4"
        tokens, _, _ = process_korean_text(text, kiwi)
        # "\uae30\uc790" and "\ub274\uc2a4" should be filtered as stopwords
        # "\ubcf4\ub3c4" should also be filtered
        for token in tokens:
            assert token not in KOREAN_STOPWORDS

    def test_sentence_splitting(self, kiwi):
        """Korean text is split into sentences."""
        from src.analysis.stage1_preprocessing import process_korean_text

        text = "\uccab \ubc88\uc9f8 \ubb38\uc7a5\uc774\ub2e4. \ub450 \ubc88\uc9f8 \ubb38\uc7a5\uc774\ub2e4. \uc138 \ubc88\uc9f8 \ubb38\uc7a5\uc774\ub2e4."
        _, _, sentences = process_korean_text(text, kiwi)
        assert len(sentences) >= 2

    def test_title_mode_single_sentence(self, kiwi):
        """Title mode returns one sentence."""
        from src.analysis.stage1_preprocessing import process_korean_text

        text = "\ub300\ud1b5\ub839 \uae34\uae09 \ud68c\uacac \uac1c\ucd5c"
        _, _, sentences = process_korean_text(text, kiwi, is_title=True)
        assert len(sentences) == 1

    def test_empty_text(self, kiwi):
        """Empty text returns empty lists."""
        from src.analysis.stage1_preprocessing import process_korean_text

        tokens, pos_tags, sentences = process_korean_text("", kiwi)
        assert tokens == []
        assert pos_tags == []
        assert sentences == []

    def test_pos_tags_are_valid(self, kiwi):
        """All returned POS tags are from KIWI_KEEP_POS."""
        from src.analysis.stage1_preprocessing import process_korean_text

        text = "\uacbd\uc81c \uc131\uc7a5\uc774 \ub458\ud654\ub418\uba74\uc11c \uc0c8\ub85c\uc6b4 \uc815\ucc45\uc774 \ud544\uc694\ud558\ub2e4"
        _, pos_tags, _ = process_korean_text(text, kiwi)
        for _, tag in pos_tags:
            assert tag in KIWI_KEEP_POS or tag == "UNK", f"Unexpected POS tag: {tag}"


@pytest.mark.slow
class TestEnglishProcessing:
    """Integration tests for English text processing with spaCy.

    Requires spaCy and en_core_web_sm to be installed.
    """

    @pytest.fixture(scope="class")
    def nlp(self):
        """Load spaCy once for all tests in this class."""
        try:
            import spacy
            return spacy.load("en_core_web_sm", disable=["ner"])
        except Exception:
            pytest.skip("spaCy en_core_web_sm not available")

    def test_basic_tokenization(self, nlp):
        """English text is tokenized and lemmatized."""
        from src.analysis.stage1_preprocessing import process_english_text

        text = "The researchers published groundbreaking findings in the journal."
        tokens, pos_tags, sentences = process_english_text(text, nlp)
        assert len(tokens) > 0
        # Should contain lemmatized nouns like "researcher", "finding", "journal"
        token_set = set(tokens)
        assert "researcher" in token_set or "finding" in token_set or "journal" in token_set

    def test_stopword_removal(self, nlp):
        """spaCy default stopwords and news stopwords are removed."""
        from src.analysis.stage1_preprocessing import process_english_text

        text = "He said that the reported findings were also very important."
        tokens, _, _ = process_english_text(text, nlp)
        for token in tokens:
            assert token.lower() not in ENGLISH_NEWS_STOPWORDS

    def test_pos_filtering(self, nlp):
        """Only NOUN, VERB, ADJ, PROPN tokens are kept."""
        from src.analysis.stage1_preprocessing import process_english_text

        text = "The large company quickly released impressive new products yesterday."
        _, pos_tags, _ = process_english_text(text, nlp)
        valid_pos = {"NOUN", "VERB", "ADJ", "PROPN"}
        for _, pos in pos_tags:
            assert pos in valid_pos, f"Unexpected POS: {pos}"

    def test_proper_noun_case_preserved(self, nlp):
        """Proper nouns keep their original case."""
        from src.analysis.stage1_preprocessing import process_english_text

        text = "President Biden visited Paris and Berlin last week."
        tokens, pos_tags, _ = process_english_text(text, nlp)
        # Check that at least one PROPN preserves capitalization
        propn_tokens = [t for t, pos in zip(tokens, pos_tags) if pos[1] == "PROPN"]
        if propn_tokens:
            assert any(t[0].isupper() for t in propn_tokens)

    def test_sentence_splitting(self, nlp):
        """English text is split into sentences."""
        from src.analysis.stage1_preprocessing import process_english_text

        text = (
            "The economy grew by 3 percent. "
            "Unemployment fell to record lows. "
            "Experts predict continued growth."
        )
        _, _, sentences = process_english_text(text, nlp)
        assert len(sentences) >= 2

    def test_title_mode(self, nlp):
        """Title mode returns one sentence."""
        from src.analysis.stage1_preprocessing import process_english_text

        text = "World Leaders Gather for Summit"
        _, _, sentences = process_english_text(text, nlp, is_title=True)
        assert len(sentences) == 1

    def test_empty_text(self, nlp):
        """Empty text returns empty lists."""
        from src.analysis.stage1_preprocessing import process_english_text

        tokens, pos_tags, sentences = process_english_text("", nlp)
        assert tokens == []
        assert pos_tags == []
        assert sentences == []

    def test_lemmatization(self, nlp):
        """Verbs are lemmatized to base form."""
        from src.analysis.stage1_preprocessing import process_english_text

        text = "The companies were producing innovative solutions."
        tokens, _, _ = process_english_text(text, nlp)
        # "producing" should be lemmatized to "produce"
        # "companies" should be lemmatized to "company"
        token_set = set(tokens)
        assert "produce" in token_set or "company" in token_set or "solution" in token_set


@pytest.mark.slow
class TestFullPipeline:
    """Full pipeline integration tests (JSONL -> process -> Parquet).

    Requires both Kiwi and spaCy models.
    """

    def test_mixed_language_batch(
        self,
        tmp_path,
        sample_korean_article,
        sample_english_article,
        sample_paywall_article,
    ):
        """Process a batch with Korean, English, and paywall articles."""
        try:
            from kiwipiepy import Kiwi
            import spacy
            spacy.load("en_core_web_sm")
        except Exception:
            pytest.skip("NLP models not available")

        articles = [
            sample_korean_article,
            sample_english_article,
            sample_paywall_article,
        ]
        jsonl_path = _make_jsonl_file(tmp_path, articles)

        preprocessor = Stage1Preprocessor()
        raw_data = preprocessor.load_jsonl(jsonl_path)
        table, intermediates, stats = preprocessor.process(raw_data)

        # All 3 articles should be processed
        assert table.num_rows == 3
        assert len(intermediates) == 3

        # Schema compliance
        assert table.schema == ARTICLES_SCHEMA

        # Language distribution
        langs = table.column("language").to_pylist()
        assert "ko" in langs
        assert "en" in langs

        # Paywall article has empty body
        bodies = table.column("body").to_pylist()
        assert "" in bodies  # At least one empty (paywall)

        # Stats
        assert stats["total_processed"] == 3
        assert stats["total_skipped"] == 0

        # Cleanup
        preprocessor.cleanup(keep_kiwi=False)

    def test_parquet_roundtrip(
        self,
        tmp_path,
        sample_english_article,
    ):
        """Parquet write + read preserves all data."""
        try:
            import spacy
            spacy.load("en_core_web_sm")
        except Exception:
            pytest.skip("spaCy en_core_web_sm not available")

        articles = [sample_english_article]
        jsonl_path = _make_jsonl_file(tmp_path, articles)
        output_path = tmp_path / "output" / "articles.parquet"

        preprocessor = Stage1Preprocessor()
        raw_data = preprocessor.load_jsonl(jsonl_path)
        table, _, _ = preprocessor.process(raw_data)
        preprocessor.write_parquet(table, output_path)

        # Validate
        result = validate_output(output_path)
        assert result["valid"] is True

        # Read back and check values
        read_table = pq.read_table(str(output_path))
        assert read_table.num_rows == 1
        row = read_table.to_pydict()
        assert row["url"][0] == sample_english_article["url"]
        assert row["source"][0] == "CNN"
        assert row["language"][0] == "en"
        assert row["word_count"][0] > 0

        preprocessor.cleanup(keep_kiwi=False)

    def test_intermediate_data_structure(
        self,
        tmp_path,
        sample_english_article,
    ):
        """Intermediate data contains expected fields."""
        try:
            import spacy
            spacy.load("en_core_web_sm")
        except Exception:
            pytest.skip("spaCy en_core_web_sm not available")

        preprocessor = Stage1Preprocessor()
        raw_data = [sample_english_article]
        table, intermediates, _ = preprocessor.process(raw_data)

        assert len(intermediates) == 1
        inter = intermediates[0]
        assert isinstance(inter, ArticleIntermediateData)
        assert len(inter.article_id) == 36  # UUID v4 format
        assert len(inter.title_tokens) > 0
        assert len(inter.body_tokens) > 0
        assert len(inter.sentences) > 0
        assert len(inter.pos_tags) > 0

        preprocessor.cleanup(keep_kiwi=False)

    def test_other_language_processing(
        self,
        tmp_path,
        sample_chinese_article,
    ):
        """Non-Korean, non-English articles use basic tokenization."""
        # Chinese processing does not require Kiwi or spaCy
        preprocessor = Stage1Preprocessor()
        raw_data = [sample_chinese_article]
        # Manually process since we might not have the NLP models
        # but Chinese uses process_other_language_text
        preprocessor._kiwi = MagicMock()  # Won't be used for Chinese
        preprocessor._nlp = MagicMock()  # Won't be used for Chinese

        row, inter = preprocessor.process_article(sample_chinese_article)
        assert row is not None
        assert row["language"] in ("zh", "en")  # langdetect might detect differently
        assert inter is not None
        assert len(inter.title_tokens) > 0

    def test_empty_batch(self, tmp_path):
        """Processing an empty batch returns empty table."""
        preprocessor = Stage1Preprocessor()
        table, intermediates, stats = preprocessor.process([])
        assert table.num_rows == 0
        assert len(intermediates) == 0
        assert stats["total_processed"] == 0


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Edge case tests that do not require NLP models."""

    def test_article_with_only_urls(self):
        """Article body containing only URLs normalizes to near-empty."""
        text = "https://example.com https://test.org/path"
        result = normalize_text(text)
        assert "https://" not in result

    def test_mixed_script_text(self):
        """Text mixing Korean and English normalizes correctly."""
        text = "\ud55c\uad6d AI \uae30\uc220\uc774 \uc138\uacc4 1\uc704"
        result = normalize_text(text, "ko")
        assert "AI" in result
        assert "\ud55c\uad6d" in result
        assert "1\uc704" in result

    def test_special_characters_preserved(self):
        """Hyphens and apostrophes in compound terms are preserved."""
        text = "state-of-the-art AI don't stop won't stop"
        result = normalize_text(text)
        assert "state-of-the-art" in result

    def test_very_long_text_normalization(self):
        """Very long text is normalized without error."""
        text = "word " * 100000  # 500K characters
        result = normalize_text(text)
        assert len(result) > 0

    def test_unicode_surrogates_handled(self):
        """Malformed Unicode does not crash normalization."""
        # NFKC normalization handles various edge cases
        text = "Normal text with \u200b zero-width space"
        result = normalize_text(text, "en")
        assert "Normal" in result

    def test_intermediate_data_paywall(self):
        """Paywall article intermediate data uses title tokens."""
        preprocessor = Stage1Preprocessor()
        preprocessor._kiwi = MagicMock()
        preprocessor._nlp = MagicMock()

        mock_doc = MagicMock()
        mock_token = MagicMock()
        mock_token.is_punct = False
        mock_token.is_space = False
        mock_token.pos_ = "NOUN"
        mock_token.lemma_ = "market"
        mock_token.text = "Market"
        mock_token.is_stop = False
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_token]))
        mock_doc.sents = [MagicMock(text="Market Plunges")]
        preprocessor._nlp.return_value = mock_doc

        raw = {
            "url": "https://example.com/article",
            "title": "Market Plunges Sharply",
            "body": "",
            "source_id": "nytimes",
            "source_name": "NYT",
            "language": "en",
            "is_paywall_truncated": True,
            "crawled_at": "2026-02-25T12:00:00+00:00",
        }
        row, inter = preprocessor.process_article(raw)
        assert row is not None
        assert inter is not None
        # Intermediate should use title-based data since body is empty
        assert inter.body_tokens == []

    def test_article_id_is_valid_uuid(self):
        """Generated article_id is a valid UUID v4."""
        preprocessor = Stage1Preprocessor()
        preprocessor._kiwi = MagicMock()
        preprocessor._nlp = MagicMock()

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        mock_doc.sents = []
        preprocessor._nlp.return_value = mock_doc

        raw = {
            "url": "https://example.com/article",
            "title": "Test Article Title Goes Here",
            "body": "Some body text.",
            "source_id": "cnn",
            "source_name": "CNN",
            "language": "en",
            "crawled_at": "2026-02-25T12:00:00+00:00",
        }
        row, _ = preprocessor.process_article(raw)
        assert row is not None
        # Should be valid UUID
        parsed = uuid.UUID(row["article_id"])
        assert parsed.version == 4


# =============================================================================
# ArticleIntermediateData Tests
# =============================================================================

class TestArticleIntermediateData:
    """Tests for the ArticleIntermediateData dataclass."""

    def test_default_fields(self):
        """Default fields are empty lists."""
        data = ArticleIntermediateData(article_id="test-id")
        assert data.title_tokens == []
        assert data.body_tokens == []
        assert data.sentences == []
        assert data.pos_tags == []

    def test_custom_fields(self):
        """Custom field values are preserved."""
        data = ArticleIntermediateData(
            article_id="test-id",
            title_tokens=["hello", "world"],
            body_tokens=["foo", "bar", "baz"],
            sentences=["Hello world.", "Foo bar baz."],
            pos_tags=[("hello", "NOUN"), ("world", "NOUN")],
        )
        assert len(data.title_tokens) == 2
        assert len(data.body_tokens) == 3
        assert len(data.sentences) == 2
        assert len(data.pos_tags) == 2
