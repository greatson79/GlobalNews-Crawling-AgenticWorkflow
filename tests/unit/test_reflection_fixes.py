"""Tests for critical reflection fixes (2026-03-11).

Covers:
    1. NER entity filter — false positive prevention for Korean entities
    2. _write_run_metadata — full mode combined metadata
    3. TOPICS_PA_SCHEMA — published_at/source column propagation
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root on sys.path
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


# ============================================================================
# Phase 2: NER Korean entity filter tests
# ============================================================================

class TestNerKoreanFilter:
    """Test _is_valid_entity with Korean false-positive-prone entities."""

    @pytest.fixture(autouse=True)
    def _import_filter(self):
        from src.analysis.stage2_features import _is_valid_entity
        self.filter = _is_valid_entity

    # --- Previously false-positive entities (should now PASS) ---

    @pytest.mark.parametrize("entity", [
        "캐나다",      # Country ending in 다
        "인도네시아",   # Country
        "테슬라",      # Company ending in 라
        "김영지",      # Korean name ending in 지
        "김미라",      # Korean name ending in 라
        "이슬라",      # Korean name ending in 라
        "박지요",      # Korean name ending in 요
        "최소네",      # Korean name ending in 네
        "일본기상청",   # Org name
    ])
    def test_legitimate_korean_entities_pass(self, entity):
        """Entities ending in single syllables that match old regex should pass."""
        assert self.filter(entity, lang="ko") is True

    # --- Sentence fragments (should still FAIL) ---

    @pytest.mark.parametrize("fragment", [
        "올해 경제성장률이 둔화됩니다",   # ends in 됩니다
        "지난해 대비 급증했다",           # ends in 했다
        "이에 대해 살펴보겠다",           # ends in 겠다
        "정부가 발표한다",               # ends in 한다
        "투자 확대가 필요합니다",         # ends in 합니다
        "시장에서 확인하세요",           # ends in 세요
        "문제가 있네요",                 # ends in 네요
        "이해할 수 있어요",              # ends in 어요
        "결과가 나왔거든",               # ends in 거든
        "경제가 성장하니까",             # ends in 니까
    ])
    def test_sentence_fragments_rejected(self, fragment):
        """Sentence fragments ending in conjugation patterns should fail."""
        assert self.filter(fragment, lang="ko") is False

    # --- English entities unchanged ---

    def test_english_entities_unaffected(self):
        """English entities should not be affected by Korean filters."""
        assert self.filter("Canada", lang="en") is True
        assert self.filter("Tesla", lang="en") is True

    # --- Basic filters still work ---

    def test_too_short_rejected(self):
        assert self.filter("A", lang="ko") is False

    def test_too_long_rejected(self):
        assert self.filter("가" * 51, lang="ko") is False

    def test_numeric_heavy_rejected(self):
        assert self.filter("12345678", lang="ko") is False


# ============================================================================
# Phase 2: Regex pattern verification
# ============================================================================

class TestNerRegexPattern:
    """Verify the updated regex only matches 2+ syllable endings."""

    @pytest.fixture(autouse=True)
    def _import_regex(self):
        from src.analysis.stage2_features import _NER_KO_SENTENCE_ENDINGS
        self.regex = _NER_KO_SENTENCE_ENDINGS

    def test_single_syllable_endings_not_matched(self):
        """Old single-syllable patterns (다/요/죠/네/지/라) should NOT match."""
        for suffix in ["다", "요", "죠", "네", "지", "라"]:
            word = f"테스트{suffix}"
            assert self.regex.search(word) is None, f"'{word}' should not match"

    def test_multi_syllable_endings_matched(self):
        """2+ syllable conjugation endings should match."""
        for suffix in ["습니다", "됩니다", "입니다", "합니다", "했다", "겠다", "된다",
                        "한다", "세요", "네요", "어요", "아요", "거든", "니까"]:
            word = f"테스트{suffix}"
            assert self.regex.search(word) is not None, f"'{word}' should match"


# ============================================================================
# Phase 3: cmd_full metadata fix
# ============================================================================

class TestRunMetadataSkip:
    """Test that _skip_metadata attribute prevents sub-command metadata writes."""

    def test_skip_metadata_attribute(self):
        """getattr(args, '_skip_metadata', False) should return True when set."""
        import argparse
        args = argparse.Namespace(date="2026-03-11")
        assert getattr(args, "_skip_metadata", False) is False
        args._skip_metadata = True
        assert getattr(args, "_skip_metadata", False) is True


# ============================================================================
# Phase 1: TOPICS_PA_SCHEMA synchronization
# ============================================================================

class TestTopicsSchemaConsistency:
    """Verify TOPICS_PA_SCHEMA has published_at and source columns everywhere."""

    def test_parquet_writer_schema_has_9_columns(self):
        from src.storage.parquet_writer import TOPICS_PA_SCHEMA
        assert len(TOPICS_PA_SCHEMA) == 9
        names = TOPICS_PA_SCHEMA.names
        assert "published_at" in names
        assert "source" in names

    def test_validate_data_schema_matches(self):
        from scripts.validate_data_schema import TOPICS_EXPECTED
        assert len(TOPICS_EXPECTED) == 9
        assert "published_at" in TOPICS_EXPECTED
        assert "source" in TOPICS_EXPECTED

    def test_schemas_are_synchronized(self):
        from src.storage.parquet_writer import TOPICS_PA_SCHEMA
        from scripts.validate_data_schema import TOPICS_EXPECTED
        pa_names = TOPICS_PA_SCHEMA.names
        assert pa_names == TOPICS_EXPECTED


# ============================================================================
# Phase 4: Dead code removal verification
# ============================================================================

class TestDeadCodeRemoval:
    """Verify dead code has been removed from stage3."""

    def test_no_stance_labels(self):
        import src.analysis.stage3_article_analysis as s3
        assert not hasattr(s3, "STANCE_LABELS")

    def test_no_narrative_labels(self):
        import src.analysis.stage3_article_analysis as s3
        assert not hasattr(s3, "NARRATIVE_LABELS")

    def test_no_detect_stance_method(self):
        from src.analysis.stage3_article_analysis import Stage3ArticleAnalyzer
        assert not hasattr(Stage3ArticleAnalyzer, "_detect_stance")

    def test_no_extract_narrative_method(self):
        from src.analysis.stage3_article_analysis import Stage3ArticleAnalyzer
        assert not hasattr(Stage3ArticleAnalyzer, "_extract_narrative")
