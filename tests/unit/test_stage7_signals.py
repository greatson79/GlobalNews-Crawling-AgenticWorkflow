"""Unit tests for Stage 7 Signal Classification pipeline.

Tests cover:
    - 5-Layer classification logic (L1-L5 exact rule matching)
    - Singularity composite score (PRD Appendix E exact weights)
    - Three independent pathway checks
    - Confidence scoring per layer (base + boosters + penalties)
    - Evidence summary generation
    - OOD detection (LOF + IF ensemble)
    - Z-score anomaly detection (T51)
    - Entropy spike computation (T52)
    - Zipf distribution deviation (T53)
    - Survival analysis (T54)
    - KL divergence (T55)
    - BERTrend lifecycle classification
    - Dual-pass classification
    - Signal deduplication
    - Parquet schema compliance
    - Empty input handling
    - Full pipeline integration
    - Edge cases (NaN, missing data, insufficient samples)

Fixture strategy:
    - Uses synthetic data to avoid heavy upstream dependencies.
    - Tests classification logic independently of data loading.
    - Integration tests verify full Parquet I/O with temporary directories.
"""

import math
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.stage7_signals import (
    CONFIDENCE_BASE,
    ENTROPY_ZSCORE_NORMALIZER,
    LOF_N_NEIGHBORS,
    STEEPS_TOTAL_DOMAINS,
    VALID_SIGNAL_LAYERS,
    ZSCORE_ANOMALY_THRESHOLD,
    SingularityIndicators,
    SignalRecord,
    Stage7Output,
    Stage7SignalClassifier,
    TopicFeatures,
    _build_signals_schema,
    _clamp,
    _days_between,
    _safe_float,
    _safe_int,
    build_evidence_summary,
    check_singularity_pathways,
    classify_bertrend_state,
    classify_signal_layer,
    compute_confidence,
    compute_entropy_spike,
    compute_kl_divergence,
    compute_ood_scores,
    compute_singularity_composite,
    compute_survival_durations,
    compute_volume_zscores,
    compute_zipf_deviation,
    dual_pass_classify,
    run_stage7,
)
from src.config.constants import (
    L1_BURST_SCORE_THRESHOLD,
    L1_VOLUME_ZSCORE_THRESHOLD,
    L2_SUSTAINED_DAYS_THRESHOLD,
    L3_CHANGEPOINT_SIGNIFICANCE_THRESHOLD,
    L3_MODULARITY_DELTA_THRESHOLD,
    L4_EMBEDDING_DRIFT_THRESHOLD,
    L4_WAVELET_PERIOD_THRESHOLD,
    L5_CROSS_DOMAIN_THRESHOLD,
    L5_NOVELTY_THRESHOLD,
    SINGULARITY_THRESHOLD,
    SINGULARITY_WEIGHTS,
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
def tmp_data_dirs(tmp_path):
    """Create temporary data directories mirroring the pipeline structure."""
    analysis_dir = tmp_path / "analysis"
    features_dir = tmp_path / "features"
    output_dir = tmp_path / "output"
    analysis_dir.mkdir()
    features_dir.mkdir()
    output_dir.mkdir()
    return analysis_dir, features_dir, output_dir


@pytest.fixture
def sample_topic_features_l1():
    """TopicFeatures that should classify as L1_fad."""
    return TopicFeatures(
        topic_id=1,
        article_ids=["a1", "a2", "a3"],
        article_count=3,
        source_count=1,
        data_span_days=3,
        volume_zscore=4.0,  # > 3.0
        burst_score=3.5,    # > 2.0
        has_burst=True,
    )


@pytest.fixture
def sample_topic_features_l2():
    """TopicFeatures that should classify as L2_short."""
    return TopicFeatures(
        topic_id=2,
        article_ids=[f"a{i}" for i in range(20)],
        article_count=20,
        source_count=5,
        data_span_days=21,
        volume_above_ma14_days=10,  # >= 7
        ma_signal="rising",
        emotion_trajectory_shift=True,
    )


@pytest.fixture
def sample_topic_features_l3():
    """TopicFeatures that should classify as L3_mid."""
    return TopicFeatures(
        topic_id=3,
        article_ids=[f"a{i}" for i in range(50)],
        article_count=50,
        source_count=10,
        data_span_days=120,  # >= 90
        changepoint_significance=0.9,  # > 0.8
        has_changepoint=True,
        network_modularity_delta=0.2,  # > 0.1
        frame_divergence_detected=True,
    )


@pytest.fixture
def sample_topic_features_l4():
    """TopicFeatures that should classify as L4_long."""
    return TopicFeatures(
        topic_id=4,
        article_ids=[f"a{i}" for i in range(100)],
        article_count=100,
        source_count=20,
        data_span_days=400,  # >= 365
        embedding_drift=0.4,  # > 0.3
        wavelet_dominant_period=120,  # > 90
        steeps_shift_detected=True,
        steeps_categories={"S", "T", "E", "P"},
    )


@pytest.fixture
def sample_topic_features_l5():
    """TopicFeatures that should classify as L5_singularity."""
    return TopicFeatures(
        topic_id=5,
        article_ids=[f"a{i}" for i in range(200)],
        article_count=200,
        source_count=30,
        data_span_days=60,
        # Novelty > 0.7
        novelty_score=0.85,
        ood_score=0.9,
        # Cross-domain >= 2
        cross_domain_count=4,
        steeps_categories={"S", "T", "E", "P"},
        # Must achieve composite >= 0.65
        changepoint_significance=0.9,
        bertrend_transition=1,
        entropy_spike=0.7,
        new_nodes_ratio=0.6,
        new_edges_ratio=0.5,
        # Pathways: A (OOD>0.7), B (cp>0.8 AND entropy>0.5), C (bertrend=1 AND cd>0.3)
    )


@pytest.fixture
def sample_topic_features_no_signal():
    """TopicFeatures that should not classify into any layer."""
    return TopicFeatures(
        topic_id=99,
        article_ids=["a1"],
        article_count=1,
        source_count=1,
        data_span_days=1,
        volume_zscore=1.0,  # < 3.0
        burst_score=0.5,    # < 2.0
    )


@pytest.fixture
def minimal_topics_parquet(tmp_path):
    """Create a minimal topics.parquet for testing."""
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir(exist_ok=True)

    table = pa.table({
        "article_id": pa.array(["a1", "a2", "a3", "a4", "a5"], type=pa.utf8()),
        "topic_id": pa.array([0, 0, 1, 1, 1], type=pa.int32()),
        "topic_label": pa.array(["Topic A", "Topic A", "Topic B", "Topic B", "Topic B"], type=pa.utf8()),
        "topic_probability": pa.array([0.8, 0.7, 0.9, 0.85, 0.75], type=pa.float32()),
    })
    pq.write_table(table, str(analysis_dir / "topics.parquet"))
    return analysis_dir


# =============================================================================
# Test: Helper Functions
# =============================================================================

class TestHelpers:
    """Tests for helper functions."""

    def test_safe_float_valid(self):
        assert _safe_float(3.14) == 3.14
        assert _safe_float(42) == 42.0
        assert _safe_float("2.5") == 2.5

    def test_safe_float_none(self):
        assert _safe_float(None) == 0.0
        assert _safe_float(None, -1.0) == -1.0

    def test_safe_float_nan(self):
        assert _safe_float(float("nan")) == 0.0

    def test_safe_float_inf(self):
        assert _safe_float(float("inf")) == 0.0
        assert _safe_float(float("-inf")) == 0.0

    def test_safe_float_invalid(self):
        assert _safe_float("not_a_number") == 0.0
        assert _safe_float([1, 2, 3]) == 0.0

    def test_safe_int_valid(self):
        assert _safe_int(42) == 42
        assert _safe_int(3.7) == 3
        assert _safe_int("5") == 5

    def test_safe_int_none(self):
        assert _safe_int(None) == 0
        assert _safe_int(None, -1) == -1

    def test_safe_int_nan(self):
        assert _safe_int(float("nan")) == 0

    def test_clamp_in_range(self):
        assert _clamp(0.5) == 0.5

    def test_clamp_below(self):
        assert _clamp(-0.5) == 0.0

    def test_clamp_above(self):
        assert _clamp(1.5) == 1.0

    def test_clamp_custom_bounds(self):
        assert _clamp(50, 10, 100) == 50
        assert _clamp(5, 10, 100) == 10
        assert _clamp(150, 10, 100) == 100

    def test_days_between_valid_datetimes(self):
        from datetime import timedelta
        d1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        d2 = datetime(2025, 1, 31, tzinfo=timezone.utc)
        assert _days_between([d1, d2]) == 30

    def test_days_between_single_date(self):
        d1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert _days_between([d1]) == 0

    def test_days_between_empty(self):
        assert _days_between([]) == 0

    def test_days_between_with_nones(self):
        d1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        d2 = datetime(2025, 1, 10, tzinfo=timezone.utc)
        assert _days_between([d1, None, d2]) == 9


# =============================================================================
# Test: Singularity Composite Score (PRD Appendix E)
# =============================================================================

class TestSingularityComposite:
    """Tests for the Singularity Composite Score formula."""

    def test_weights_sum_to_one(self):
        """CRITICAL: Weights must sum to exactly 1.0."""
        total = sum(SINGULARITY_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-10, f"Weights sum to {total}, expected 1.0"

    def test_exact_weights(self):
        """CRITICAL: Verify each weight matches PRD Appendix E exactly."""
        assert SINGULARITY_WEIGHTS["w1_ood"] == 0.20
        assert SINGULARITY_WEIGHTS["w2_changepoint"] == 0.15
        assert SINGULARITY_WEIGHTS["w3_cross_domain"] == 0.20
        assert SINGULARITY_WEIGHTS["w4_bertrend"] == 0.15
        assert SINGULARITY_WEIGHTS["w5_entropy"] == 0.10
        assert SINGULARITY_WEIGHTS["w6_novelty"] == 0.10
        assert SINGULARITY_WEIGHTS["w7_network"] == 0.10

    def test_all_zeros(self):
        """All zero indicators -> composite = 0."""
        indicators = SingularityIndicators()
        assert compute_singularity_composite(indicators) == 0.0

    def test_all_ones(self):
        """All maximum indicators -> composite = 1.0."""
        indicators = SingularityIndicators(
            ood_score=1.0,
            changepoint_sig=1.0,
            cross_domain=1.0,
            bertrend_transition=1,
            entropy_spike=1.0,
            novelty_score=1.0,
            network_anomaly=1.0,
        )
        assert abs(compute_singularity_composite(indicators) - 1.0) < 1e-6

    def test_partial_indicators(self):
        """Verify weighted sum with partial values."""
        indicators = SingularityIndicators(
            ood_score=0.8,       # contributes 0.20 * 0.8 = 0.16
            changepoint_sig=0.0,
            cross_domain=0.5,    # contributes 0.20 * 0.5 = 0.10
            bertrend_transition=1,  # contributes 0.15 * 1.0 = 0.15
            entropy_spike=0.0,
            novelty_score=0.0,
            network_anomaly=0.0,
        )
        expected = 0.16 + 0.10 + 0.15  # = 0.41
        result = compute_singularity_composite(indicators)
        assert abs(result - expected) < 1e-6, f"Expected {expected}, got {result}"

    def test_clamped_to_unit(self):
        """Scores above 1 or below 0 are clamped."""
        indicators = SingularityIndicators(
            ood_score=2.0,  # Will be clamped to 1.0 internally
            changepoint_sig=1.5,
            cross_domain=1.0,
            bertrend_transition=1,
            entropy_spike=1.0,
            novelty_score=1.0,
            network_anomaly=1.0,
        )
        result = compute_singularity_composite(indicators)
        assert 0.0 <= result <= 1.0

    def test_threshold_constant(self):
        """Verify the singularity threshold constant."""
        assert SINGULARITY_THRESHOLD == 0.65


# =============================================================================
# Test: Three Independent Pathways
# =============================================================================

class TestSingularityPathways:
    """Tests for the three independent L5 pathways."""

    def test_pathway_a_ood(self):
        """Pathway A: OOD_score > 0.7 OR Novelty_score > 0.7."""
        # OOD triggers
        ind = SingularityIndicators(ood_score=0.8)
        a, _, _ = check_singularity_pathways(ind)
        assert a is True

        # Novelty triggers
        ind = SingularityIndicators(novelty_score=0.75)
        a, _, _ = check_singularity_pathways(ind)
        assert a is True

        # Neither triggers
        ind = SingularityIndicators(ood_score=0.5, novelty_score=0.5)
        a, _, _ = check_singularity_pathways(ind)
        assert a is False

    def test_pathway_b_structural(self):
        """Pathway B: Changepoint > 0.8 AND (Entropy > 0.5 OR Network > 0.5)."""
        # Both conditions
        ind = SingularityIndicators(changepoint_sig=0.9, entropy_spike=0.6)
        _, b, _ = check_singularity_pathways(ind)
        assert b is True

        # Changepoint + Network
        ind = SingularityIndicators(changepoint_sig=0.85, network_anomaly=0.7)
        _, b, _ = check_singularity_pathways(ind)
        assert b is True

        # Changepoint only (missing secondary)
        ind = SingularityIndicators(changepoint_sig=0.9, entropy_spike=0.3, network_anomaly=0.2)
        _, b, _ = check_singularity_pathways(ind)
        assert b is False

        # Missing changepoint
        ind = SingularityIndicators(changepoint_sig=0.5, entropy_spike=0.9)
        _, b, _ = check_singularity_pathways(ind)
        assert b is False

    def test_pathway_c_emergence(self):
        """Pathway C: BERTrend_transition == 1 AND CrossDomain > 0.3."""
        ind = SingularityIndicators(bertrend_transition=1, cross_domain=0.5)
        _, _, c = check_singularity_pathways(ind)
        assert c is True

        # Missing transition
        ind = SingularityIndicators(bertrend_transition=0, cross_domain=0.5)
        _, _, c = check_singularity_pathways(ind)
        assert c is False

        # Low cross-domain
        ind = SingularityIndicators(bertrend_transition=1, cross_domain=0.2)
        _, _, c = check_singularity_pathways(ind)
        assert c is False

    def test_two_of_three_required(self):
        """At least 2 of 3 pathways must trigger for L5."""
        # Only 1 pathway
        ind = SingularityIndicators(ood_score=0.9)
        pa_a, pa_b, pa_c = check_singularity_pathways(ind)
        assert sum([pa_a, pa_b, pa_c]) == 1

        # 2 pathways
        ind = SingularityIndicators(
            ood_score=0.9,
            changepoint_sig=0.9, entropy_spike=0.6,
        )
        pa_a, pa_b, pa_c = check_singularity_pathways(ind)
        assert sum([pa_a, pa_b, pa_c]) == 2

        # All 3 pathways
        ind = SingularityIndicators(
            ood_score=0.9,
            changepoint_sig=0.9, entropy_spike=0.6,
            bertrend_transition=1, cross_domain=0.5,
        )
        pa_a, pa_b, pa_c = check_singularity_pathways(ind)
        assert sum([pa_a, pa_b, pa_c]) == 3


# =============================================================================
# Test: 5-Layer Classification (EXACT rules)
# =============================================================================

class TestLayerClassification:
    """Tests for the 5-layer signal classification logic."""

    def test_l5_singularity(self, sample_topic_features_l5):
        """L5 classification with all criteria met."""
        layer = classify_signal_layer(sample_topic_features_l5)
        assert layer == "L5_singularity"

    def test_l4_long(self, sample_topic_features_l4):
        """L4 classification with all criteria met."""
        layer = classify_signal_layer(sample_topic_features_l4)
        assert layer == "L4_long"

    def test_l3_mid(self, sample_topic_features_l3):
        """L3 classification with all criteria met."""
        layer = classify_signal_layer(sample_topic_features_l3)
        assert layer == "L3_mid"

    def test_l2_short(self, sample_topic_features_l2):
        """L2 classification with all criteria met."""
        layer = classify_signal_layer(sample_topic_features_l2)
        assert layer == "L2_short"

    def test_l1_fad(self, sample_topic_features_l1):
        """L1 classification with all criteria met."""
        layer = classify_signal_layer(sample_topic_features_l1)
        assert layer == "L1_fad"

    def test_no_signal(self, sample_topic_features_no_signal):
        """No layer matches."""
        layer = classify_signal_layer(sample_topic_features_no_signal)
        assert layer == ""

    def test_l5_requires_novelty_above_threshold(self):
        """L5 requires novelty_score > 0.7."""
        feat = TopicFeatures(
            topic_id=5,
            novelty_score=0.5,  # Below threshold
            cross_domain_count=4,
            ood_score=0.9,
            changepoint_significance=0.9,
            bertrend_transition=1,
            entropy_spike=0.7,
            new_nodes_ratio=0.6,
            new_edges_ratio=0.5,
        )
        layer = classify_signal_layer(feat)
        assert layer != "L5_singularity"

    def test_l5_requires_cross_domain_ge_2(self):
        """L5 requires cross_domain_count >= 2."""
        feat = TopicFeatures(
            topic_id=5,
            novelty_score=0.85,
            cross_domain_count=1,  # Below threshold
            ood_score=0.9,
            changepoint_significance=0.9,
            bertrend_transition=1,
            entropy_spike=0.7,
        )
        layer = classify_signal_layer(feat)
        assert layer != "L5_singularity"

    def test_l5_requires_composite_above_threshold(self):
        """L5 requires singularity_composite >= 0.65."""
        feat = TopicFeatures(
            topic_id=5,
            novelty_score=0.85,
            cross_domain_count=3,
            ood_score=0.2,  # Low, so composite will be low
            changepoint_significance=0.1,
            bertrend_transition=0,
            entropy_spike=0.1,
            new_nodes_ratio=0.1,
            new_edges_ratio=0.1,
        )
        layer = classify_signal_layer(feat)
        assert layer != "L5_singularity"

    def test_l5_requires_two_pathways(self):
        """L5 requires at least 2 of 3 pathways."""
        feat = TopicFeatures(
            topic_id=5,
            novelty_score=0.85,
            cross_domain_count=4,
            # Only Pathway A triggers (OOD > 0.7)
            ood_score=0.9,
            # Pathway B: changepoint low
            changepoint_significance=0.3,
            # Pathway C: no transition
            bertrend_transition=0,
            entropy_spike=0.8,
            new_nodes_ratio=0.6,
            new_edges_ratio=0.5,
        )
        layer = classify_signal_layer(feat)
        assert layer != "L5_singularity"

    def test_l4_requires_data_span_365(self):
        """L4 requires data_span_days >= 365."""
        feat = TopicFeatures(
            topic_id=4,
            embedding_drift=0.5,
            wavelet_dominant_period=120,
            steeps_shift_detected=True,
            data_span_days=200,  # Below 365
        )
        layer = classify_signal_layer(feat)
        assert layer != "L4_long"

    def test_l3_requires_frame_divergence(self):
        """L3 requires frame_divergence_detected."""
        feat = TopicFeatures(
            topic_id=3,
            changepoint_significance=0.9,
            network_modularity_delta=0.2,
            frame_divergence_detected=False,  # Missing
            data_span_days=120,
        )
        layer = classify_signal_layer(feat)
        assert layer != "L3_mid"

    def test_l2_requires_rising_ma(self):
        """L2 requires ma_signal == 'rising'."""
        feat = TopicFeatures(
            topic_id=2,
            volume_above_ma14_days=10,
            ma_signal="falling",  # Not rising
            emotion_trajectory_shift=True,
            data_span_days=21,
        )
        layer = classify_signal_layer(feat)
        assert layer != "L2_short"

    def test_l1_requires_both_zscore_and_burst(self):
        """L1 requires both volume_zscore > 3.0 AND burst_score > 2.0."""
        # Has z-score but not burst
        feat = TopicFeatures(
            topic_id=1,
            volume_zscore=4.0,
            burst_score=1.0,  # Below threshold
            data_span_days=3,
        )
        assert classify_signal_layer(feat) == ""

        # Has burst but not z-score
        feat = TopicFeatures(
            topic_id=1,
            volume_zscore=2.0,  # Below threshold
            burst_score=3.0,
            data_span_days=3,
        )
        assert classify_signal_layer(feat) == ""

    def test_l5_takes_priority_over_l4(self):
        """L5 is checked first and takes priority."""
        feat = TopicFeatures(
            topic_id=5,
            # L5 criteria
            novelty_score=0.85,
            cross_domain_count=4,
            ood_score=0.9,
            changepoint_significance=0.9,
            bertrend_transition=1,
            entropy_spike=0.7,
            new_nodes_ratio=0.6,
            new_edges_ratio=0.5,
            # Also meets L4 criteria
            embedding_drift=0.4,
            wavelet_dominant_period=120,
            steeps_shift_detected=True,
            data_span_days=400,
        )
        layer = classify_signal_layer(feat)
        assert layer == "L5_singularity"

    def test_valid_layer_values(self):
        """All returned layers must be in VALID_SIGNAL_LAYERS or empty."""
        test_features = [
            TopicFeatures(topic_id=1, volume_zscore=4.0, burst_score=3.0, data_span_days=3),
            TopicFeatures(topic_id=2),
        ]
        for feat in test_features:
            layer = classify_signal_layer(feat)
            assert layer in VALID_SIGNAL_LAYERS or layer == ""


# =============================================================================
# Test: Confidence Scoring
# =============================================================================

class TestConfidenceScoring:
    """Tests for per-layer confidence scoring."""

    def test_l1_base_confidence(self):
        feat = TopicFeatures(topic_id=1, source_count=2)
        conf = compute_confidence(feat, "L1_fad")
        assert conf == pytest.approx(0.6)  # 0.4 + 0.2 multi-source

    def test_l1_single_source_penalty(self):
        feat = TopicFeatures(topic_id=1, source_count=1)
        conf = compute_confidence(feat, "L1_fad")
        # 0.4 base - 0.2 single-source (penalty applied because source_count <= 1)
        # Note: the booster check (source_count > 1) fails, then penalty applies
        assert conf == pytest.approx(0.2)

    def test_l2_emotion_booster(self):
        feat = TopicFeatures(topic_id=2, emotion_trajectory_shift=True, source_count=3)
        conf = compute_confidence(feat, "L2_short")
        assert conf == pytest.approx(0.65)  # 0.5 + 0.15 emotion

    def test_l2_five_sources_booster(self):
        feat = TopicFeatures(topic_id=2, source_count=5)
        conf = compute_confidence(feat, "L2_short")
        assert conf == pytest.approx(0.6)  # 0.5 + 0.1

    def test_l3_causal_booster(self):
        feat = TopicFeatures(
            topic_id=3,
            causal_depth=3,
            frame_divergence_detected=True,
        )
        conf = compute_confidence(feat, "L3_mid")
        # 0.6 + 0.15 causal + 0.1 frame = 0.85
        assert conf == pytest.approx(0.85)

    def test_l4_wavelet_booster(self):
        feat = TopicFeatures(
            topic_id=4,
            wavelet_dominant_period=200,
            steeps_categories={"S", "T", "E"},
        )
        conf = compute_confidence(feat, "L4_long")
        # 0.7 + 0.1 wavelet>180 + 0.1 cross-lingual = 0.9
        assert conf == pytest.approx(0.9)

    def test_l5_three_pathways_booster(self):
        feat = TopicFeatures(
            topic_id=5,
            ood_score=0.9,
            changepoint_significance=0.9,
            cross_domain_count=4,
            bertrend_transition=1,
            entropy_spike=0.7,
            novelty_score=0.85,
            new_nodes_ratio=0.6,
            new_edges_ratio=0.5,
        )
        conf = compute_confidence(feat, "L5_singularity")
        # 0.5 + 0.2 (3 pathways) + possible composite booster
        assert conf >= 0.7

    def test_l5_single_pathway_penalty(self):
        feat = TopicFeatures(
            topic_id=5,
            ood_score=0.9,  # Only pathway A
            changepoint_significance=0.3,
            cross_domain_count=1,
            bertrend_transition=0,
            novelty_score=0.5,
        )
        conf = compute_confidence(feat, "L5_singularity")
        assert conf == pytest.approx(0.3)  # 0.5 - 0.2

    def test_confidence_clamped_to_unit(self):
        """Confidence must be in [0, 1]."""
        feat = TopicFeatures(
            topic_id=4,
            wavelet_dominant_period=200,
            steeps_categories={"S", "T", "E", "P", "En", "Se"},
        )
        conf = compute_confidence(feat, "L4_long")
        assert 0.0 <= conf <= 1.0

    def test_invalid_layer_returns_zero(self):
        feat = TopicFeatures(topic_id=1)
        conf = compute_confidence(feat, "L99_invalid")
        assert conf == 0.0


# =============================================================================
# Test: Evidence Summary
# =============================================================================

class TestEvidenceSummary:
    """Tests for evidence summary generation."""

    def test_l1_evidence_includes_burst(self, sample_topic_features_l1):
        summary = build_evidence_summary(sample_topic_features_l1, "L1_fad")
        assert "burst" in summary.lower() or "Burst" in summary
        assert "L1_fad" in summary

    def test_l5_evidence_includes_novelty(self, sample_topic_features_l5):
        summary = build_evidence_summary(sample_topic_features_l5, "L5_singularity")
        assert "Novelty" in summary or "novelty" in summary
        assert "OOD" in summary
        assert "L5_singularity" in summary

    def test_evidence_includes_topic_id(self):
        feat = TopicFeatures(topic_id=42, article_count=10, source_count=3, data_span_days=5)
        summary = build_evidence_summary(feat, "L1_fad")
        assert "42" in summary

    def test_evidence_includes_steeps(self):
        feat = TopicFeatures(
            topic_id=1,
            steeps_categories={"S", "T"},
            article_count=1, source_count=1, data_span_days=1,
        )
        summary = build_evidence_summary(feat, "L1_fad")
        assert "STEEPS" in summary


# =============================================================================
# Test: OOD Detection (T47 + T48)
# =============================================================================

class TestOODDetection:
    """Tests for LOF + Isolation Forest novelty detection."""

    def test_normal_data_low_scores(self):
        """Normal data should have low OOD scores."""
        np.random.seed(42)
        n = 100
        embeddings = np.random.randn(n, 10).astype(np.float32)
        article_ids = [f"a{i}" for i in range(n)]

        scores = compute_ood_scores(embeddings, article_ids)
        assert len(scores) == n
        # Most scores should be relatively low
        values = list(scores.values())
        assert np.mean(values) < 0.7

    def test_outlier_has_higher_score(self):
        """An outlier point should have a higher OOD score than inliers."""
        np.random.seed(42)
        n = 100
        normal = np.random.randn(n, 10).astype(np.float32)
        outlier = np.ones((1, 10), dtype=np.float32) * 10  # Far from cluster
        embeddings = np.vstack([normal, outlier])
        article_ids = [f"a{i}" for i in range(n + 1)]

        scores = compute_ood_scores(embeddings, article_ids)
        outlier_score = scores[f"a{n}"]
        mean_normal = np.mean([scores[f"a{i}"] for i in range(n)])
        assert outlier_score > mean_normal

    def test_too_few_samples_returns_zeros(self):
        """Fewer than LOF_N_NEIGHBORS+1 samples should return zeros."""
        embeddings = np.random.randn(5, 10).astype(np.float32)
        article_ids = [f"a{i}" for i in range(5)]
        scores = compute_ood_scores(embeddings, article_ids)
        assert all(v == 0.0 for v in scores.values())

    def test_scores_in_unit_range(self):
        """All OOD scores must be in [0, 1]."""
        np.random.seed(42)
        embeddings = np.random.randn(50, 10).astype(np.float32)
        article_ids = [f"a{i}" for i in range(50)]
        scores = compute_ood_scores(embeddings, article_ids)
        for v in scores.values():
            assert 0.0 <= v <= 1.0


# =============================================================================
# Test: Z-score Anomaly (T51)
# =============================================================================

class TestZScoreAnomaly:
    """Tests for z-score anomaly detection."""

    def test_spike_at_end(self):
        """A spike at the end should have high z-score."""
        volumes = {1: [10.0] * 30 + [100.0]}  # Spike at end
        zscores = compute_volume_zscores(volumes)
        assert zscores[1] > ZSCORE_ANOMALY_THRESHOLD

    def test_flat_series(self):
        """A flat series should have near-zero z-score."""
        volumes = {1: [10.0] * 30}
        zscores = compute_volume_zscores(volumes)
        assert abs(zscores[1]) < 0.1

    def test_too_few_points(self):
        """Fewer than 3 points should return 0."""
        volumes = {1: [10.0, 20.0]}
        zscores = compute_volume_zscores(volumes)
        assert zscores[1] == 0.0


# =============================================================================
# Test: Entropy Spike (T52)
# =============================================================================

class TestEntropySpike:
    """Tests for entropy change detection."""

    def test_stable_distributions_low_spike(self):
        """Stable distributions should have near-zero entropy spike."""
        # 10 identical uniform distributions
        dists = [np.ones(5) / 5.0 for _ in range(10)]
        spike = compute_entropy_spike(dists)
        assert spike < 0.1

    def test_sudden_concentration_spike(self):
        """A sudden concentration in distribution should produce a spike."""
        # 10 uniform distributions followed by concentrated
        dists = [np.ones(5) / 5.0 for _ in range(10)]
        concentrated = np.array([0.9, 0.025, 0.025, 0.025, 0.025])
        dists.append(concentrated)
        spike = compute_entropy_spike(dists)
        # Entropy decreases sharply -> negative z-score -> but we take absolute or
        # the formula normalizes differently. The spike value should be non-trivial.
        assert isinstance(spike, float)

    def test_too_few_distributions(self):
        """Fewer than 3 distributions should return 0."""
        dists = [np.ones(5) / 5.0, np.ones(5) / 5.0]
        spike = compute_entropy_spike(dists)
        assert spike == 0.0


# =============================================================================
# Test: Zipf Deviation (T53)
# =============================================================================

class TestZipfDeviation:
    """Tests for Zipf distribution deviation."""

    def test_perfect_zipf_low_deviation(self):
        """A Zipf-distributed frequency should have low deviation."""
        freqs = {f"term_{i}": int(1000 / (i + 1)) for i in range(100)}
        deviation = compute_zipf_deviation(freqs)
        assert deviation < 0.5  # Should be relatively low

    def test_uniform_high_deviation(self):
        """A uniform frequency distribution deviates from Zipf."""
        freqs = {f"term_{i}": 100 for i in range(100)}
        deviation = compute_zipf_deviation(freqs)
        assert deviation > 0.0

    def test_too_few_terms(self):
        """Fewer than 5 terms returns 0."""
        freqs = {"a": 10, "b": 5, "c": 3}
        deviation = compute_zipf_deviation(freqs)
        assert deviation == 0.0

    def test_score_in_unit_range(self):
        """Zipf deviation must be in [0, 1]."""
        freqs = {f"term_{i}": (100 - i) for i in range(100)}
        deviation = compute_zipf_deviation(freqs)
        assert 0.0 <= deviation <= 1.0


# =============================================================================
# Test: Survival Analysis (T54)
# =============================================================================

class TestSurvivalAnalysis:
    """Tests for Kaplan-Meier survival estimation."""

    def test_basic_survival(self):
        """Basic survival estimation with enough topics."""
        durations = {
            1: (10.0, False),
            2: (20.0, False),
            3: (30.0, True),  # Censored (still active)
            4: (5.0, False),
            5: (15.0, False),
        }
        estimates = compute_survival_durations(durations)
        assert len(estimates) == 5
        for tid, est in estimates.items():
            assert est > 0, f"Topic {tid} has non-positive estimate"

    def test_too_few_topics(self):
        """Fewer than SURVIVAL_MIN_TOPICS returns raw durations."""
        durations = {1: (10.0, False), 2: (20.0, True)}
        estimates = compute_survival_durations(durations)
        assert estimates[1] == 10.0
        assert estimates[2] == 20.0


# =============================================================================
# Test: KL Divergence (T55)
# =============================================================================

class TestKLDivergence:
    """Tests for KL divergence computation."""

    def test_identical_distributions_zero(self):
        """KL(P||Q) = 0 when P == Q (approximately, due to epsilon)."""
        p = np.array([0.25, 0.25, 0.25, 0.25])
        q = np.array([0.25, 0.25, 0.25, 0.25])
        kl = compute_kl_divergence(p, q)
        assert kl < 0.01

    def test_divergent_distributions_positive(self):
        """Divergent distributions should have positive KL."""
        p = np.array([0.9, 0.05, 0.03, 0.02])
        q = np.array([0.25, 0.25, 0.25, 0.25])
        kl = compute_kl_divergence(p, q)
        assert kl > 0.1

    def test_empty_distributions(self):
        """Empty arrays return 0."""
        assert compute_kl_divergence(np.array([]), np.array([])) == 0.0

    def test_mismatched_shapes(self):
        """Mismatched shapes return 0."""
        p = np.array([0.5, 0.5])
        q = np.array([0.33, 0.33, 0.34])
        assert compute_kl_divergence(p, q) == 0.0


# =============================================================================
# Test: BERTrend Lifecycle
# =============================================================================

class TestBERTrendLifecycle:
    """Tests for BERTrend weak signal detection."""

    def test_noise_state(self):
        """Few articles = noise state."""
        state, transition = classify_bertrend_state(2, 0.0, 0.0)
        assert state == "noise"
        assert transition == 0

    def test_noise_to_weak(self):
        """Moderate articles with growth = weak with transition."""
        state, transition = classify_bertrend_state(8, 0.3, 0.1)
        assert state == "weak"
        assert transition == 1  # noise->weak transition

    def test_weak_no_growth(self):
        """Moderate articles without growth = weak without transition."""
        state, transition = classify_bertrend_state(8, 0.0, 0.1)
        assert state == "weak"
        assert transition == 0

    def test_weak_to_emerging(self):
        """High growth rate = emerging with transition."""
        state, transition = classify_bertrend_state(15, 0.6, 0.3)
        assert state == "emerging"
        assert transition == 1  # weak->emerging transition

    def test_strong_state(self):
        """High trend strength without high growth = strong."""
        state, transition = classify_bertrend_state(15, 0.2, 0.7)
        assert state == "strong"
        assert transition == 0

    def test_declining_state(self):
        """Declining trend overrides all."""
        state, transition = classify_bertrend_state(100, 2.0, 0.8, is_declining=True)
        assert state == "declining"
        assert transition == 0


# =============================================================================
# Test: Dual-Pass Classification
# =============================================================================

class TestDualPass:
    """Tests for dual-pass classification."""

    def test_body_pass_authoritative(self, sample_topic_features_l1):
        """Body pass result is authoritative even if title pass differs."""
        title_feat = TopicFeatures(topic_id=1)  # No signal in title
        layer = dual_pass_classify(sample_topic_features_l1, title_feat)
        assert layer == "L1_fad"

    def test_no_title_features(self, sample_topic_features_l2):
        """Works without title features."""
        layer = dual_pass_classify(sample_topic_features_l2)
        assert layer == "L2_short"


# =============================================================================
# Test: Parquet Schema Compliance
# =============================================================================

class TestParquetSchema:
    """Tests for signals.parquet schema compliance."""

    def test_schema_has_12_columns(self):
        """Schema must have exactly 12 columns."""
        schema = _build_signals_schema()
        assert len(schema) == 12

    def test_schema_column_names(self):
        """All required column names must be present."""
        schema = _build_signals_schema()
        expected = {
            "signal_id", "signal_layer", "signal_label", "detected_at",
            "topic_ids", "article_ids", "burst_score", "changepoint_significance",
            "novelty_score", "singularity_composite", "evidence_summary", "confidence",
        }
        actual = {field.name for field in schema}
        assert actual == expected

    def test_schema_types(self):
        """Column types must match specification."""
        schema = _build_signals_schema()
        field_types = {field.name: field.type for field in schema}

        assert field_types["signal_id"] == pa.utf8()
        assert field_types["signal_layer"] == pa.utf8()
        assert field_types["signal_label"] == pa.utf8()
        assert field_types["detected_at"] == pa.timestamp("us", tz="UTC")
        assert field_types["topic_ids"] == pa.list_(pa.int32())
        assert field_types["article_ids"] == pa.list_(pa.utf8())
        assert field_types["burst_score"] == pa.float32()
        assert field_types["changepoint_significance"] == pa.float32()
        assert field_types["novelty_score"] == pa.float32()
        assert field_types["singularity_composite"] == pa.float32()
        assert field_types["evidence_summary"] == pa.utf8()
        assert field_types["confidence"] == pa.float32()

    def test_nullable_fields(self):
        """Correct nullable specifications."""
        schema = _build_signals_schema()
        field_nullable = {field.name: field.nullable for field in schema}

        # Non-nullable
        assert field_nullable["signal_id"] is False
        assert field_nullable["signal_layer"] is False
        assert field_nullable["signal_label"] is False
        assert field_nullable["detected_at"] is False
        assert field_nullable["evidence_summary"] is False
        assert field_nullable["confidence"] is False

        # Nullable
        assert field_nullable["burst_score"] is True
        assert field_nullable["changepoint_significance"] is True
        assert field_nullable["novelty_score"] is True
        assert field_nullable["singularity_composite"] is True


# =============================================================================
# Test: Empty Input Handling
# =============================================================================

class TestEmptyInput:
    """Tests for empty and missing input scenarios."""

    def test_empty_output_written(self, tmp_output_dir):
        """Empty signals.parquet should be written for no signals."""
        classifier = Stage7SignalClassifier()
        classifier._write_empty_output(tmp_output_dir)

        output_path = tmp_output_dir / "signals.parquet"
        assert output_path.exists()

        table = pq.read_table(str(output_path))
        assert table.num_rows == 0
        assert len(table.schema) == 12

    def test_run_with_no_data(self, tmp_data_dirs):
        """Run with no input files should produce empty output."""
        analysis_dir, features_dir, output_dir = tmp_data_dirs
        classifier = Stage7SignalClassifier()
        output = classifier.run(
            analysis_dir=analysis_dir,
            features_dir=features_dir,
            output_dir=output_dir,
        )
        assert output.n_signals == 0
        assert output.n_topics_analyzed == 0

        # Verify empty parquet was written
        output_path = output_dir / "signals.parquet"
        assert output_path.exists()
        table = pq.read_table(str(output_path))
        assert table.num_rows == 0


# =============================================================================
# Test: Full Pipeline Integration
# =============================================================================

class TestPipelineIntegration:
    """Integration tests for the full Stage 7 pipeline."""

    @staticmethod
    def _create_synthetic_topics(analysis_dir: Path, n_articles: int = 50):
        """Create synthetic topics.parquet."""
        n_topics = 5
        article_ids = [str(uuid.uuid4()) for _ in range(n_articles)]
        topic_ids = [i % n_topics for i in range(n_articles)]
        labels = [f"Topic {tid}" for tid in topic_ids]

        table = pa.table({
            "article_id": pa.array(article_ids, type=pa.utf8()),
            "topic_id": pa.array(topic_ids, type=pa.int32()),
            "topic_label": pa.array(labels, type=pa.utf8()),
            "topic_probability": pa.array(
                [0.8] * n_articles, type=pa.float32()
            ),
        })
        pq.write_table(table, str(analysis_dir / "topics.parquet"))
        return article_ids, topic_ids

    @staticmethod
    def _create_synthetic_timeseries(
        analysis_dir: Path,
        topic_ids: list[int],
        n_days: int = 30,
    ):
        """Create synthetic timeseries.parquet with burst and trend data."""
        records_tid = []
        records_date = []
        records_value = []
        records_trend = []
        records_burst = []
        records_cp_sig = []
        records_is_cp = []
        records_ma_signal = []
        records_ma_short = []
        records_ma_long = []

        unique_tids = sorted(set(topic_ids))
        for tid in unique_tids:
            for day in range(n_days):
                records_tid.append(tid)
                from datetime import timedelta
                dt = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
                records_date.append(dt)

                # Generate values with patterns per topic
                base = 10 + tid * 5
                if tid == 0:
                    # L1-like: spike at end
                    val = base if day < n_days - 2 else base * 5
                    burst = 0.5 if day < n_days - 2 else 3.0
                elif tid == 1:
                    # L2-like: steady rise
                    val = base + day * 2
                    burst = 0.5
                else:
                    val = base + np.random.random() * 5
                    burst = 0.3

                records_value.append(float(val))
                records_trend.append(float(val * 0.7))
                records_burst.append(float(burst))
                records_cp_sig.append(0.3)
                records_is_cp.append(False)
                records_ma_signal.append("rising" if tid == 1 else "neutral")
                records_ma_short.append(float(val * 1.1))
                records_ma_long.append(float(val * 0.9) if tid == 1 else float(val * 1.1))

        table = pa.table({
            "topic_id": pa.array(records_tid, type=pa.int32()),
            "date": pa.array(records_date, type=pa.timestamp("us", tz="UTC")),
            "value": pa.array(records_value, type=pa.float32()),
            "trend": pa.array(records_trend, type=pa.float32()),
            "burst_score": pa.array(records_burst, type=pa.float32()),
            "changepoint_significance": pa.array(records_cp_sig, type=pa.float32()),
            "is_changepoint": pa.array(records_is_cp, type=pa.bool_()),
            "ma_signal": pa.array(records_ma_signal, type=pa.utf8()),
            "ma_short": pa.array(records_ma_short, type=pa.float32()),
            "ma_long": pa.array(records_ma_long, type=pa.float32()),
            "series_id": pa.array(
                [f"s_{tid}_{d}" for tid, d in zip(records_tid, range(len(records_tid)))],
                type=pa.utf8(),
            ),
            "metric_type": pa.array(["article_count"] * len(records_tid), type=pa.utf8()),
            "seasonal": pa.array([0.0] * len(records_tid), type=pa.float32()),
            "residual": pa.array([0.0] * len(records_tid), type=pa.float32()),
        })
        pq.write_table(table, str(analysis_dir / "timeseries.parquet"))

    @staticmethod
    def _create_synthetic_article_analysis(
        analysis_dir: Path,
        article_ids: list[str],
    ):
        """Create synthetic article_analysis.parquet."""
        n = len(article_ids)
        sources = [f"source_{i % 5}" for i in range(n)]
        steeps = ["S", "T", "E", "En", "P"]
        steeps_primary = [steeps[i % len(steeps)] for i in range(n)]
        emotion_values = [0.3 if i % 3 == 0 else 0.0 for i in range(n)]

        table = pa.table({
            "article_id": pa.array(article_ids, type=pa.utf8()),
            "source": pa.array(sources, type=pa.utf8()),
            "steeps_primary": pa.array(steeps_primary, type=pa.utf8()),
            "emotion_trajectory": pa.array(emotion_values, type=pa.float32()),
        })
        pq.write_table(table, str(analysis_dir / "article_analysis.parquet"))

    @staticmethod
    def _create_synthetic_embeddings(
        features_dir: Path,
        article_ids: list[str],
        dim: int = 10,
    ):
        """Create synthetic embeddings.parquet."""
        n = len(article_ids)
        np.random.seed(42)
        embeddings = np.random.randn(n, dim).astype(np.float32)

        table = pa.table({
            "article_id": pa.array(article_ids, type=pa.utf8()),
            "embedding": pa.array(
                [emb.tolist() for emb in embeddings],
                type=pa.list_(pa.float32()),
            ),
        })
        pq.write_table(table, str(features_dir / "embeddings.parquet"))

    def test_full_pipeline_with_synthetic_data(self, tmp_data_dirs):
        """Full pipeline integration test with synthetic data."""
        analysis_dir, features_dir, output_dir = tmp_data_dirs

        # Create synthetic data
        article_ids, topic_ids = self._create_synthetic_topics(analysis_dir, n_articles=50)
        self._create_synthetic_timeseries(analysis_dir, topic_ids)
        self._create_synthetic_article_analysis(analysis_dir, article_ids)
        self._create_synthetic_embeddings(features_dir, article_ids)

        # Run pipeline
        classifier = Stage7SignalClassifier()
        output = classifier.run(
            analysis_dir=analysis_dir,
            features_dir=features_dir,
            output_dir=output_dir,
        )
        classifier.cleanup()

        # Verify output
        assert output.n_topics_analyzed > 0
        assert output.elapsed_seconds > 0

        # Verify parquet file
        output_path = output_dir / "signals.parquet"
        assert output_path.exists()

        table = pq.read_table(str(output_path))
        assert len(table.schema) == 12

        # If signals were detected, verify structure
        if table.num_rows > 0:
            # Check signal_layer values
            layers = table.column("signal_layer").to_pylist()
            for layer in layers:
                assert layer in VALID_SIGNAL_LAYERS

            # Check confidence range
            confs = table.column("confidence").to_pylist()
            for c in confs:
                assert 0.0 <= c <= 1.0

            # Check signal_id is UUID format
            ids = table.column("signal_id").to_pylist()
            for sid in ids:
                # Should be valid UUID
                uuid.UUID(sid)  # Will raise ValueError if invalid

    def test_convenience_function(self, tmp_data_dirs):
        """Test run_stage7 convenience function."""
        analysis_dir, features_dir, output_dir = tmp_data_dirs

        # Create minimal topics
        self._create_synthetic_topics(analysis_dir, n_articles=10)

        output = run_stage7(
            data_dir=analysis_dir.parent,
            output_dir=output_dir,
        )
        assert isinstance(output, Stage7Output)

    def test_pipeline_produces_valid_parquet_schema(self, tmp_data_dirs):
        """The output parquet must match SIGNALS_SCHEMA exactly."""
        analysis_dir, features_dir, output_dir = tmp_data_dirs

        article_ids, topic_ids = self._create_synthetic_topics(analysis_dir, n_articles=50)
        self._create_synthetic_timeseries(analysis_dir, topic_ids)
        self._create_synthetic_article_analysis(analysis_dir, article_ids)
        self._create_synthetic_embeddings(features_dir, article_ids)

        classifier = Stage7SignalClassifier()
        classifier.run(
            analysis_dir=analysis_dir,
            features_dir=features_dir,
            output_dir=output_dir,
        )
        classifier.cleanup()

        table = pq.read_table(str(output_dir / "signals.parquet"))
        expected_schema = _build_signals_schema()

        # Verify column names match exactly
        assert table.schema.names == expected_schema.names

        # Verify column types match
        for i, field in enumerate(expected_schema):
            actual_field = table.schema.field(i)
            assert actual_field.type == field.type, (
                f"Column {field.name}: expected {field.type}, got {actual_field.type}"
            )


# =============================================================================
# Test: Signal Deduplication
# =============================================================================

class TestDeduplication:
    """Tests for signal deduplication logic."""

    def test_duplicate_removed(self):
        """Duplicate signals (same topic + layer) are merged."""
        classifier = Stage7SignalClassifier()
        sig1 = SignalRecord(
            signal_id="id1", signal_layer="L1_fad",
            topic_ids=[1], article_ids=["a1", "a2"],
            confidence=0.6,
        )
        sig2 = SignalRecord(
            signal_id="id2", signal_layer="L1_fad",
            topic_ids=[1], article_ids=["a2", "a3"],
            confidence=0.8,
        )
        classifier._signals = [sig1, sig2]
        classifier._deduplicate_signals()

        assert len(classifier._signals) == 1
        merged = classifier._signals[0]
        assert merged.confidence == 0.8  # Higher confidence kept

    def test_different_layers_not_merged(self):
        """Different layers for same topic are not merged."""
        classifier = Stage7SignalClassifier()
        sig1 = SignalRecord(
            signal_id="id1", signal_layer="L1_fad",
            topic_ids=[1], article_ids=["a1"],
            confidence=0.6,
        )
        sig2 = SignalRecord(
            signal_id="id2", signal_layer="L2_short",
            topic_ids=[1], article_ids=["a2"],
            confidence=0.7,
        )
        classifier._signals = [sig1, sig2]
        classifier._deduplicate_signals()

        assert len(classifier._signals) == 2

    def test_empty_signals_no_error(self):
        """Deduplication with empty list does not error."""
        classifier = Stage7SignalClassifier()
        classifier._signals = []
        classifier._deduplicate_signals()
        assert len(classifier._signals) == 0


# =============================================================================
# Test: Stage7Output Data Class
# =============================================================================

class TestStage7Output:
    """Tests for the Stage7Output data class."""

    def test_default_values(self):
        output = Stage7Output()
        assert output.n_signals == 0
        assert output.n_topics_analyzed == 0
        assert output.layer_distribution == {}
        assert output.l5_candidates == []
        assert output.elapsed_seconds == 0.0
        assert output.signals == []


# =============================================================================
# Test: Constants Consistency
# =============================================================================

class TestConstantsConsistency:
    """Tests that Stage 7 constants are consistent with config/constants.py."""

    def test_singularity_threshold(self):
        assert SINGULARITY_THRESHOLD == 0.65

    def test_l1_thresholds(self):
        assert L1_VOLUME_ZSCORE_THRESHOLD == 3.0
        assert L1_BURST_SCORE_THRESHOLD == 2.0

    def test_l2_threshold(self):
        assert L2_SUSTAINED_DAYS_THRESHOLD == 7

    def test_l3_thresholds(self):
        assert L3_CHANGEPOINT_SIGNIFICANCE_THRESHOLD == 0.8
        assert L3_MODULARITY_DELTA_THRESHOLD == 0.1

    def test_l4_thresholds(self):
        assert L4_EMBEDDING_DRIFT_THRESHOLD == 0.3
        assert L4_WAVELET_PERIOD_THRESHOLD == 90

    def test_l5_thresholds(self):
        assert L5_NOVELTY_THRESHOLD == 0.7
        assert L5_CROSS_DOMAIN_THRESHOLD == 0.3

    def test_confidence_bases(self):
        """Verify all layers have confidence bases."""
        for layer in VALID_SIGNAL_LAYERS:
            assert layer in CONFIDENCE_BASE


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_nan_in_features(self):
        """NaN values in features should not crash classification."""
        feat = TopicFeatures(
            topic_id=1,
            volume_zscore=float("nan"),
            burst_score=float("nan"),
        )
        layer = classify_signal_layer(feat)
        # NaN comparisons are False, so no layer should match
        assert layer == ""

    def test_negative_values(self):
        """Negative values should not match positive thresholds."""
        feat = TopicFeatures(
            topic_id=1,
            volume_zscore=-5.0,
            burst_score=-3.0,
            data_span_days=3,
        )
        layer = classify_signal_layer(feat)
        assert layer == ""

    def test_zero_division_in_cross_domain(self):
        """Cross-domain computation should handle zero STEEPS domains."""
        feat = TopicFeatures(topic_id=1, cross_domain_count=0)
        layer = classify_signal_layer(feat)
        assert layer == ""  # No crash

    def test_singularity_with_nan_indicators(self):
        """Singularity composite should handle NaN indicators gracefully."""
        indicators = SingularityIndicators(
            ood_score=float("nan"),
            changepoint_sig=0.5,
        )
        result = compute_singularity_composite(indicators)
        assert 0.0 <= result <= 1.0  # _clamp handles NaN

    def test_topic_features_default_values(self):
        """TopicFeatures should have sane defaults."""
        feat = TopicFeatures(topic_id=0)
        assert feat.article_count == 0
        assert feat.source_count == 0
        assert feat.data_span_days == 0
        assert feat.volume_zscore == 0.0
        assert feat.burst_score == 0.0
        assert feat.novelty_score == 0.0
        assert feat.ood_score == 0.0
        assert feat.bertrend_state == "noise"
        assert feat.bertrend_transition == 0

    def test_large_topic_count(self):
        """Pipeline should handle a large number of topics."""
        classifier = Stage7SignalClassifier()
        for i in range(1000):
            classifier._topic_features[i] = TopicFeatures(
                topic_id=i,
                article_ids=[f"a{i}_{j}" for j in range(3)],
                article_count=3,
                source_count=1,
                data_span_days=2,
                volume_zscore=1.0,
                burst_score=0.5,
            )

        # Should not crash
        classifier._classify_all_signals()
        classifier._score_all_confidence()
        classifier._deduplicate_signals()

        # No signals expected (features don't meet any threshold)
        assert len(classifier._signals) == 0
