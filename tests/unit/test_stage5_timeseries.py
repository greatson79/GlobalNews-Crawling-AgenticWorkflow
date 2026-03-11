"""Unit tests for Stage 5 Time Series Analysis pipeline.

Tests cover:
    - STL Decomposition (T29): decomposition quality, anomaly detection, fallback
    - Kleinberg Burst Detection (T30): burst intervals, edge cases
    - PELT Changepoint Detection (T31): changepoint detection, empty results
    - Prophet Forecast (T32): forecast generation, insufficient data handling
    - Wavelet Analysis (T33): decomposition, short signal handling
    - ARIMA Modeling (T34): order selection, forecast generation
    - Moving Average Crossover (T35): crossover signals, edge cases
    - Seasonality Detection (T36): periodogram, significance testing
    - Time series construction: daily aggregation, zero-fill, NaN handling
    - Parquet schema compliance: TIMESERIES_SCHEMA (17 columns)
    - Full pipeline integration: run() with synthetic data
    - Edge cases: empty input, single day, no topics

Fixture strategy:
    - Heavy libraries (prophet, ruptures, pywt) are tested with mocks for
      fast execution. Slow tests with real libraries are marked pytest.mark.slow.
    - Synthetic data generators create realistic daily time series with known
      patterns (trend, seasonal, burst) for deterministic verification.
"""

import math
import sys
from datetime import datetime, timedelta, timezone
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

from src.analysis.stage5_timeseries import (
    EMOTION_COLUMNS,
    MA_LONG_WINDOW,
    MA_SHORT_WINDOW,
    PELT_MIN_SIZE,
    STL_MIN_OBSERVATIONS,
    STL_PERIOD,
    TIMESERIES_SCHEMA,
    ARIMAResult,
    BurstInterval,
    ChangepointResult,
    ProphetResult,
    STLResult,
    Stage5Config,
    Stage5Metrics,
    Stage5TimeseriesAnalyzer,
    TimeSeriesRecord,
    WaveletResult,
    _build_daily_series,
    _compute_ma_crossover,
    _detect_seasonality,
    _get_memory_gb,
    _parse_series_id,
    _run_kleinberg_burst,
    _run_pelt,
    _run_stl,
    _run_wavelet,
    _simple_linear_trend,
    run_stage5,
    validate_output,
)
from src.utils.error_handler import PipelineStageError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    """Return a default Stage5Config."""
    return Stage5Config()


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create and return a temporary output directory."""
    out = tmp_path / "analysis"
    out.mkdir()
    return out


@pytest.fixture
def base_date():
    """Return a base date for synthetic data generation."""
    return datetime(2025, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def synthetic_30day_series(base_date):
    """Generate a synthetic 30-day volume time series with weekly pattern.

    Pattern: baseline=10, weekly spike on day 0 (Mon), trend +0.5/day.
    """
    n = 30
    values = np.zeros(n, dtype=np.float32)
    for i in range(n):
        baseline = 10.0 + 0.5 * i  # Upward trend
        seasonal = 5.0 if i % 7 == 0 else 0.0  # Weekly spike
        noise = np.random.default_rng(42 + i).normal(0, 1)
        values[i] = max(0, baseline + seasonal + noise)
    dates = [base_date + timedelta(days=i) for i in range(n)]
    return dates, values


@pytest.fixture
def synthetic_burst_series():
    """Generate a series with a known burst at days 10-15."""
    n = 30
    counts = np.ones(n, dtype=np.float64) * 5  # Baseline of 5
    counts[10:16] = 50  # Burst: 10x baseline
    return counts


@pytest.fixture
def synthetic_changepoint_series():
    """Generate a series with a known mean shift at day 20."""
    rng = np.random.default_rng(42)
    n = 40
    values = np.empty(n, dtype=np.float64)
    values[:20] = rng.normal(10, 1, size=20)  # Mean = 10
    values[20:] = rng.normal(30, 1, size=20)  # Mean = 30
    return values


def _make_articles_parquet(tmp_path, n_articles=50, n_days=30, base_date=None):
    """Create a synthetic articles.parquet.

    Returns:
        Path to the created Parquet file.
    """
    if base_date is None:
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

    rng = np.random.default_rng(42)
    schema = pa.schema([
        pa.field("article_id", pa.utf8()),
        pa.field("url", pa.utf8()),
        pa.field("title", pa.utf8()),
        pa.field("body", pa.utf8()),
        pa.field("source", pa.utf8()),
        pa.field("category", pa.utf8()),
        pa.field("language", pa.utf8()),
        pa.field("published_at", pa.timestamp("us", tz="UTC")),
        pa.field("crawled_at", pa.timestamp("us", tz="UTC")),
        pa.field("author", pa.utf8()),
        pa.field("word_count", pa.int32()),
        pa.field("content_hash", pa.utf8()),
    ])

    article_ids = [f"art-{i:04d}" for i in range(n_articles)]
    dates = [
        base_date + timedelta(days=int(rng.integers(0, n_days)))
        for _ in range(n_articles)
    ]
    sources = [f"source-{rng.integers(0, 5)}" for _ in range(n_articles)]

    table = pa.table(
        {
            "article_id": article_ids,
            "url": [f"https://example.com/{i}" for i in range(n_articles)],
            "title": [f"Article {i}" for i in range(n_articles)],
            "body": [f"Body text for article {i}" for i in range(n_articles)],
            "source": sources,
            "category": ["politics"] * n_articles,
            "language": ["en"] * n_articles,
            "published_at": dates,
            "crawled_at": dates,
            "author": [None] * n_articles,
            "word_count": [100] * n_articles,
            "content_hash": [f"hash-{i}" for i in range(n_articles)],
        },
        schema=schema,
    )
    path = tmp_path / "processed" / "articles.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(path))
    return path, article_ids, dates


def _make_topics_parquet(tmp_path, article_ids, n_topics=5):
    """Create a synthetic topics.parquet.

    Assigns articles round-robin to topics.
    """
    rng = np.random.default_rng(42)
    schema = pa.schema([
        pa.field("article_id", pa.utf8()),
        pa.field("topic_id", pa.int32()),
        pa.field("topic_label", pa.utf8()),
        pa.field("topic_probability", pa.float32()),
        pa.field("hdbscan_cluster_id", pa.int32()),
        pa.field("nmf_topic_id", pa.int32()),
        pa.field("lda_topic_id", pa.int32()),
        pa.field("published_at", pa.timestamp("us", tz="UTC")),
        pa.field("source", pa.utf8()),
    ])

    topic_ids = [i % n_topics for i in range(len(article_ids))]
    n = len(article_ids)
    sources = ["chosun", "yna", "donga", "hani", "mk"]
    table = pa.table(
        {
            "article_id": article_ids,
            "topic_id": topic_ids,
            "topic_label": [f"Topic {t}" for t in topic_ids],
            "topic_probability": rng.random(n).astype(np.float32).tolist(),
            "hdbscan_cluster_id": topic_ids,
            "nmf_topic_id": topic_ids,
            "lda_topic_id": topic_ids,
            "published_at": pa.array([None] * n, type=pa.timestamp("us", tz="UTC")),
            "source": [sources[i % len(sources)] for i in range(n)],
        },
        schema=schema,
    )
    path = tmp_path / "analysis" / "topics.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(path))
    return path


def _make_analysis_parquet(tmp_path, article_ids):
    """Create a synthetic article_analysis.parquet."""
    rng = np.random.default_rng(42)
    n = len(article_ids)

    columns = {
        "article_id": article_ids,
        "sentiment_label": ["positive" if rng.random() > 0.5 else "negative" for _ in range(n)],
        "sentiment_score": rng.uniform(-1.0, 1.0, size=n).astype(np.float32).tolist(),
    }
    schema_fields = [
        pa.field("article_id", pa.utf8()),
        pa.field("sentiment_label", pa.utf8()),
        pa.field("sentiment_score", pa.float32()),
    ]

    for ecol in EMOTION_COLUMNS:
        columns[ecol] = rng.uniform(0, 1, size=n).astype(np.float32).tolist()
        schema_fields.append(pa.field(ecol, pa.float32()))

    # Add STEEPS and importance
    columns["steeps_category"] = ["S"] * n
    columns["importance_score"] = rng.uniform(0, 100, size=n).astype(np.float32).tolist()
    schema_fields.append(pa.field("steeps_category", pa.utf8()))
    schema_fields.append(pa.field("importance_score", pa.float32()))

    schema = pa.schema(schema_fields)
    table = pa.table(columns, schema=schema)
    path = tmp_path / "analysis" / "article_analysis.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(path))
    return path


# ---------------------------------------------------------------------------
# Test: Memory helper
# ---------------------------------------------------------------------------

class TestMemoryHelper:
    """Tests for _get_memory_gb()."""

    def test_returns_float(self):
        """Memory usage is returned as a float."""
        result = _get_memory_gb()
        assert isinstance(result, float)

    def test_non_negative(self):
        """Memory usage is non-negative."""
        assert _get_memory_gb() >= 0.0


# ---------------------------------------------------------------------------
# Test: T29 STL Decomposition
# ---------------------------------------------------------------------------

class TestSTLDecomposition:
    """Tests for STL decomposition (T29)."""

    def test_stl_with_sufficient_data(self, synthetic_30day_series):
        """STL produces trend, seasonal, residual for 30-day series."""
        dates, values = synthetic_30day_series
        result = _run_stl(values, period=7)

        assert result is not None
        assert len(result.trend) == len(values)
        assert len(result.seasonal) == len(values)
        assert len(result.residual) == len(values)
        assert len(result.anomaly_mask) == len(values)

    def test_stl_reconstruction(self, synthetic_30day_series):
        """Trend + seasonal + residual reconstructs original (within tolerance)."""
        dates, values = synthetic_30day_series
        result = _run_stl(values, period=7)

        assert result is not None
        reconstructed = result.trend + result.seasonal + result.residual
        np.testing.assert_allclose(
            reconstructed, values, atol=1e-3,
            err_msg="STL reconstruction does not match original series"
        )

    def test_stl_insufficient_data(self):
        """STL returns None when data is too short (< 2*period)."""
        short_values = np.array([1, 2, 3, 4, 5], dtype=np.float32)
        result = _run_stl(short_values, period=7)
        assert result is None

    def test_stl_exact_minimum_length(self):
        """STL works with exactly 2*period observations."""
        values = np.random.default_rng(42).normal(10, 2, size=14).astype(np.float32)
        result = _run_stl(values, period=7)
        assert result is not None
        assert len(result.trend) == 14

    def test_stl_anomaly_detection(self):
        """STL detects residual anomalies beyond threshold."""
        # Create series with a spike
        values = np.ones(28, dtype=np.float32) * 10
        values[14] = 100  # Extreme spike
        result = _run_stl(values, period=7, anomaly_threshold=2.0)

        if result is not None:
            # The spike should produce a large residual
            assert np.max(np.abs(result.residual)) > 10


class TestSimpleLinearTrend:
    """Tests for the linear trend fallback."""

    def test_upward_trend(self):
        """Detects upward linear trend."""
        values = np.arange(10, dtype=np.float32)
        trend = _simple_linear_trend(values)
        assert len(trend) == 10
        # Trend should be increasing
        assert trend[-1] > trend[0]

    def test_constant_series(self):
        """Constant series produces flat trend."""
        values = np.ones(10, dtype=np.float32) * 5
        trend = _simple_linear_trend(values)
        np.testing.assert_allclose(trend, 5.0, atol=1e-5)

    def test_single_value(self):
        """Single value returns that value."""
        values = np.array([7.0], dtype=np.float32)
        trend = _simple_linear_trend(values)
        assert len(trend) == 1
        assert abs(trend[0] - 7.0) < 1e-5

    def test_with_nans(self):
        """Handles NaN values gracefully."""
        values = np.array([1, 2, float("nan"), 4, 5], dtype=np.float32)
        trend = _simple_linear_trend(values)
        assert len(trend) == 5
        assert not np.any(np.isnan(trend))


# ---------------------------------------------------------------------------
# Test: T30 Kleinberg Burst Detection
# ---------------------------------------------------------------------------

class TestKleinbergBurst:
    """Tests for Kleinberg burst detection (T30)."""

    def test_detects_burst(self, synthetic_burst_series):
        """Detects burst in synthetic series with 10x spike."""
        bursts = _run_kleinberg_burst(synthetic_burst_series, s=2.0, gamma=1.0)

        assert len(bursts) > 0
        # At least one burst should overlap with the spike region [10, 15]
        has_overlap = any(
            b.start_idx <= 15 and b.end_idx >= 10 for b in bursts
        )
        assert has_overlap, f"No burst overlaps with spike region. Bursts: {bursts}"

    def test_burst_score_positive(self, synthetic_burst_series):
        """All burst scores are positive."""
        bursts = _run_kleinberg_burst(synthetic_burst_series)
        for b in bursts:
            assert b.burst_score > 0

    def test_no_burst_in_flat_series(self):
        """No bursts detected in constant series."""
        flat = np.ones(30, dtype=np.float64) * 5
        bursts = _run_kleinberg_burst(flat)
        # Flat series should not produce bursts
        assert len(bursts) == 0

    def test_empty_series(self):
        """Empty series returns no bursts."""
        bursts = _run_kleinberg_burst(np.array([]))
        assert len(bursts) == 0

    def test_zero_series(self):
        """All-zero series returns no bursts."""
        bursts = _run_kleinberg_burst(np.zeros(30))
        assert len(bursts) == 0

    def test_short_series(self):
        """Very short series (< 3) returns no bursts."""
        bursts = _run_kleinberg_burst(np.array([1, 2]))
        assert len(bursts) == 0

    def test_burst_interval_fields(self, synthetic_burst_series):
        """BurstInterval has valid field values."""
        bursts = _run_kleinberg_burst(synthetic_burst_series)
        for b in bursts:
            assert b.start_idx >= 0
            assert b.end_idx >= b.start_idx
            assert b.burst_level >= 1
            assert b.burst_score >= 0


# ---------------------------------------------------------------------------
# Test: T31 PELT Changepoint Detection
# ---------------------------------------------------------------------------

class TestPELTChangepoint:
    """Tests for PELT changepoint detection (T31)."""

    def test_detects_mean_shift(self, synthetic_changepoint_series):
        """Detects changepoint near the known mean shift at index 20."""
        try:
            import ruptures  # noqa: F401
        except ImportError:
            pytest.skip("ruptures not installed")

        result = _run_pelt(
            synthetic_changepoint_series,
            model="rbf",
            min_size=3,
            n_permutations=10,  # Reduce for test speed
        )

        assert len(result.changepoint_indices) > 0
        # At least one changepoint should be near index 20
        near_20 = any(
            abs(cp - 20) <= 3 for cp in result.changepoint_indices
        )
        assert near_20, (
            f"No changepoint near index 20. "
            f"Detected: {result.changepoint_indices}"
        )

    def test_significance_scores_valid(self, synthetic_changepoint_series):
        """Significance scores are in [0, 1]."""
        try:
            import ruptures  # noqa: F401
        except ImportError:
            pytest.skip("ruptures not installed")

        result = _run_pelt(
            synthetic_changepoint_series,
            n_permutations=10,
        )

        for sig in result.significance_scores:
            assert 0.0 <= sig <= 1.0

    def test_no_changepoint_in_constant(self):
        """Constant series produces no changepoints."""
        try:
            import ruptures  # noqa: F401
        except ImportError:
            pytest.skip("ruptures not installed")

        values = np.ones(40, dtype=np.float64) * 10
        result = _run_pelt(values)
        assert len(result.changepoint_indices) == 0

    def test_too_short_series(self):
        """Series shorter than 2*min_size returns empty result."""
        values = np.array([1, 2, 3], dtype=np.float64)
        result = _run_pelt(values, min_size=3)
        assert len(result.changepoint_indices) == 0


# ---------------------------------------------------------------------------
# Test: T32 Prophet Forecast
# ---------------------------------------------------------------------------

class TestProphetForecast:
    """Tests for Prophet forecast (T32)."""

    @pytest.mark.slow
    def test_prophet_produces_forecast(self, synthetic_30day_series):
        """Prophet generates forecasts for 30-day series."""
        try:
            from prophet import Prophet  # noqa: F401
        except ImportError:
            pytest.skip("prophet not installed")

        dates, values = synthetic_30day_series
        from src.analysis.stage5_timeseries import _run_prophet

        result = _run_prophet(dates, values, horizon=7)
        assert result is not None
        assert len(result.dates) == len(dates) + 7
        assert len(result.forecast) == len(dates) + 7
        assert len(result.lower) == len(dates) + 7
        assert len(result.upper) == len(dates) + 7

    def test_prophet_insufficient_data(self, base_date):
        """Prophet returns None when data is too short."""
        dates = [base_date + timedelta(days=i) for i in range(5)]
        values = np.arange(5, dtype=np.float32)

        from src.analysis.stage5_timeseries import _run_prophet

        result = _run_prophet(dates, values, horizon=7)
        assert result is None


# ---------------------------------------------------------------------------
# Test: T33 Wavelet Analysis
# ---------------------------------------------------------------------------

class TestWaveletAnalysis:
    """Tests for wavelet analysis (T33)."""

    def test_wavelet_decomposition(self):
        """Wavelet decomposition produces coefficients."""
        try:
            import pywt  # noqa: F401
        except ImportError:
            pytest.skip("pywt not installed")

        values = np.random.default_rng(42).normal(10, 2, size=64).astype(np.float32)
        result = _run_wavelet(values, wavelet="db4", level=4)

        assert result is not None
        assert len(result.coefficients) > 0
        assert result.energy_by_scale  # Non-empty dict

    def test_wavelet_short_signal(self):
        """Wavelet returns None for signal shorter than 2^level."""
        values = np.array([1, 2, 3], dtype=np.float32)
        result = _run_wavelet(values, level=4)
        assert result is None

    def test_wavelet_energy_positive(self):
        """All wavelet energies are non-negative."""
        try:
            import pywt  # noqa: F401
        except ImportError:
            pytest.skip("pywt not installed")

        values = np.random.default_rng(42).normal(10, 2, size=64).astype(np.float32)
        result = _run_wavelet(values)
        assert result is not None
        for energy in result.energy_by_scale.values():
            assert energy >= 0


# ---------------------------------------------------------------------------
# Test: T34 ARIMA Modeling
# ---------------------------------------------------------------------------

class TestARIMA:
    """Tests for ARIMA modeling (T34)."""

    def test_arima_fit(self):
        """ARIMA fits and produces forecast."""
        try:
            from statsmodels.tsa.arima.model import ARIMA  # noqa: F401
        except ImportError:
            pytest.skip("statsmodels not installed")

        from src.analysis.stage5_timeseries import _run_arima

        rng = np.random.default_rng(42)
        values = 10 + np.cumsum(rng.normal(0, 1, size=50)).astype(np.float32)
        result = _run_arima(values, forecast_steps=7)

        if result is not None:
            assert len(result.forecast) == 7
            assert len(result.order) == 3
            assert not math.isnan(result.aic)

    def test_arima_too_short(self):
        """ARIMA returns None for very short series."""
        from src.analysis.stage5_timeseries import _run_arima

        values = np.array([1, 2, 3], dtype=np.float32)
        result = _run_arima(values)
        assert result is None


# ---------------------------------------------------------------------------
# Test: T35 Moving Average Crossover
# ---------------------------------------------------------------------------

class TestMAcrossover:
    """Tests for Moving Average Crossover (T35)."""

    def test_basic_ma(self):
        """Short and long MA are computed correctly."""
        values = np.arange(20, dtype=np.float32)
        ma_short, ma_long, signals = _compute_ma_crossover(values, short_window=3, long_window=5)

        # ma_short should be valid from index 2 onward
        assert not np.isnan(ma_short[2])
        assert np.isnan(ma_short[0])

        # ma_long should be valid from index 4 onward
        assert not np.isnan(ma_long[4])
        assert np.isnan(ma_long[0])

    def test_ma_short_value(self):
        """Short MA is the correct rolling mean."""
        values = np.array([1, 2, 3, 4, 5], dtype=np.float32)
        ma_short, _, _ = _compute_ma_crossover(values, short_window=3, long_window=14)

        # At index 2: mean(1, 2, 3) = 2.0
        assert abs(ma_short[2] - 2.0) < 1e-5
        # At index 3: mean(2, 3, 4) = 3.0
        assert abs(ma_short[3] - 3.0) < 1e-5

    def test_crossover_rising(self):
        """Detects 'rising' signal when short MA crosses above long MA."""
        # Create a series where short MA starts below, then crosses above
        n = 20
        values = np.zeros(n, dtype=np.float32)
        # First half: low values -> short MA < long MA
        values[:10] = 1.0
        # Second half: high values -> short MA crosses above long MA
        values[10:] = 20.0

        _, _, signals = _compute_ma_crossover(
            values, short_window=3, long_window=5
        )

        # Should have a "rising" signal after the jump
        assert "rising" in signals

    def test_crossover_declining(self):
        """Detects 'declining' signal when short MA crosses below long MA."""
        n = 20
        values = np.zeros(n, dtype=np.float32)
        values[:10] = 20.0
        values[10:] = 1.0

        _, _, signals = _compute_ma_crossover(
            values, short_window=3, long_window=5
        )

        assert "declining" in signals

    def test_short_series(self):
        """Short series returns NaN MAs."""
        values = np.array([1.0], dtype=np.float32)
        ma_short, ma_long, signals = _compute_ma_crossover(values)
        assert all(np.isnan(ma_short))
        assert all(np.isnan(ma_long))


# ---------------------------------------------------------------------------
# Test: T36 Seasonality Detection
# ---------------------------------------------------------------------------

class TestSeasonalityDetection:
    """Tests for periodogram-based seasonality detection (T36)."""

    def test_weekly_seasonality(self):
        """Detects weekly (7-day) periodicity in synthetic signal."""
        n = 60
        t = np.arange(n, dtype=np.float64)
        # Weekly sinusoidal component
        signal = 10 + 5 * np.sin(2 * np.pi * t / 7)
        signal = signal.astype(np.float32)

        result = _detect_seasonality(signal)
        assert len(result.periods) > 0

        # Check that at least one period is near 7 days
        near_weekly = any(abs(p - 7.0) < 2.0 for p in result.periods)
        assert near_weekly, f"No period near 7 days. Found: {result.periods}"

    def test_no_seasonality_noise(self):
        """White noise produces no strong seasonalities."""
        rng = np.random.default_rng(42)
        noise = rng.normal(0, 1, size=60).astype(np.float32)
        result = _detect_seasonality(noise)

        # May or may not detect spurious peaks, but none should be very strong
        # relative to the noise floor. This is a soft check.
        if result.significant:
            n_significant = sum(result.significant)
            # With 60 points, we should not get many false positives at p<0.05
            assert n_significant < len(result.periods) * 0.5

    def test_empty_series(self):
        """Empty or very short series returns empty result."""
        result = _detect_seasonality(np.array([], dtype=np.float32))
        assert len(result.periods) == 0

        result = _detect_seasonality(np.array([1, 2], dtype=np.float32))
        assert len(result.periods) == 0


# ---------------------------------------------------------------------------
# Test: Time Series Construction
# ---------------------------------------------------------------------------

class TestBuildDailySeries:
    """Tests for daily time series construction."""

    def test_basic_construction(self, base_date):
        """Constructs volume series from article data."""
        article_ids = ["a1", "a2", "a3", "a4"]
        dates = [
            base_date,
            base_date,
            base_date + timedelta(days=1),
            base_date + timedelta(days=2),
        ]
        topic_assignments = {"a1": 0, "a2": 0, "a3": 0, "a4": 1}
        sentiment_scores = {"a1": 0.5, "a2": -0.3, "a3": 0.1, "a4": 0.8}
        emotion_scores = {
            aid: {ecol: 0.5 for ecol in EMOTION_COLUMNS}
            for aid in article_ids
        }

        series = _build_daily_series(
            article_ids, dates, topic_assignments,
            sentiment_scores, emotion_scores,
        )

        # Should have volume series for topics 0, 1, and -1 (aggregate)
        assert "topic_0_volume" in series
        assert "topic_1_volume" in series
        assert "topic_-1_volume" in series

        # Topic 0 on day 0: 2 articles (a1, a2)
        assert series["topic_0_volume"][base_date] == 2.0

        # Topic 0 on day 1: 1 article (a3)
        assert series["topic_0_volume"][base_date + timedelta(days=1)] == 1.0

    def test_zero_fill_missing_days(self, base_date):
        """Missing days in volume series are zero-filled."""
        article_ids = ["a1", "a2"]
        dates = [base_date, base_date + timedelta(days=5)]
        topic_assignments = {"a1": 0, "a2": 0}
        sentiment_scores = {"a1": 0.1, "a2": 0.2}
        emotion_scores = {
            aid: {ecol: 0.5 for ecol in EMOTION_COLUMNS}
            for aid in article_ids
        }

        series = _build_daily_series(
            article_ids, dates, topic_assignments,
            sentiment_scores, emotion_scores,
        )

        # Days 1-4 should be zero-filled for volume
        for i in range(1, 5):
            day = base_date + timedelta(days=i)
            assert series["topic_0_volume"][day] == 0.0

    def test_sentiment_nan_for_missing_days(self, base_date):
        """Sentiment for days with no articles is NaN."""
        article_ids = ["a1", "a2"]
        dates = [base_date, base_date + timedelta(days=2)]
        topic_assignments = {"a1": 0, "a2": 0}
        sentiment_scores = {"a1": 0.5, "a2": -0.3}
        emotion_scores = {
            aid: {ecol: 0.5 for ecol in EMOTION_COLUMNS}
            for aid in article_ids
        }

        series = _build_daily_series(
            article_ids, dates, topic_assignments,
            sentiment_scores, emotion_scores,
        )

        # Day 1 should be NaN for sentiment (no articles)
        day1 = base_date + timedelta(days=1)
        assert math.isnan(series["topic_0_sentiment"][day1])

    def test_empty_input(self):
        """Empty input produces empty series."""
        series = _build_daily_series([], [], {}, {}, {})
        assert series == {}


class TestParseSeriesId:
    """Tests for series_id parsing."""

    def test_volume_series(self):
        """Parses volume series ID."""
        tid, mt = _parse_series_id("topic_3_volume")
        assert tid == 3
        assert mt == "volume"

    def test_aggregate_volume(self):
        """Parses aggregate (topic -1) volume series."""
        tid, mt = _parse_series_id("topic_-1_volume")
        assert tid == -1
        assert mt == "volume"

    def test_sentiment_series(self):
        """Parses sentiment series ID."""
        tid, mt = _parse_series_id("topic_5_sentiment")
        assert tid == 5
        assert mt == "sentiment"

    def test_emotion_series(self):
        """Parses emotion series ID."""
        tid, mt = _parse_series_id("topic_2_emotion_joy")
        assert tid == 2
        assert mt == "emotion_joy"


# ---------------------------------------------------------------------------
# Test: Parquet Schema Compliance
# ---------------------------------------------------------------------------

class TestTimeseriesSchema:
    """Tests for TIMESERIES_SCHEMA compliance."""

    def test_schema_column_count(self):
        """Schema has exactly 17 columns."""
        assert len(TIMESERIES_SCHEMA) == 17

    def test_schema_column_names(self):
        """Schema contains all expected column names."""
        expected = [
            "series_id", "topic_id", "metric_type", "date", "value",
            "trend", "seasonal", "residual", "burst_score",
            "is_changepoint", "changepoint_significance",
            "prophet_forecast", "prophet_lower", "prophet_upper",
            "ma_short", "ma_long", "ma_signal",
        ]
        actual = [f.name for f in TIMESERIES_SCHEMA]
        assert actual == expected

    def test_non_nullable_columns(self):
        """Verify which columns are non-nullable."""
        non_nullable = {
            f.name for f in TIMESERIES_SCHEMA if not f.nullable
        }
        assert "series_id" in non_nullable
        assert "topic_id" in non_nullable
        assert "metric_type" in non_nullable
        assert "date" in non_nullable
        assert "value" in non_nullable
        assert "is_changepoint" in non_nullable

    def test_nullable_columns(self):
        """Verify nullable columns."""
        nullable = {f.name for f in TIMESERIES_SCHEMA if f.nullable}
        assert "trend" in nullable
        assert "seasonal" in nullable
        assert "residual" in nullable
        assert "burst_score" in nullable
        assert "prophet_forecast" in nullable
        assert "ma_signal" in nullable

    def test_date_type(self):
        """Date column is UTC microsecond timestamp."""
        date_field = TIMESERIES_SCHEMA.field("date")
        assert date_field.type == pa.timestamp("us", tz="UTC")


# ---------------------------------------------------------------------------
# Test: Output Validation
# ---------------------------------------------------------------------------

class TestValidateOutput:
    """Tests for validate_output()."""

    def test_valid_empty_table(self):
        """Empty table passes validation."""
        table = Stage5TimeseriesAnalyzer._build_empty_table()
        errors = validate_output(table)
        assert errors == []

    def test_missing_column(self):
        """Missing column is detected."""
        # Create table with one column removed
        table = pa.table(
            {
                "series_id": pa.array(["s1"], type=pa.utf8()),
                "topic_id": pa.array([1], type=pa.int32()),
            },
            schema=pa.schema([
                pa.field("series_id", pa.utf8()),
                pa.field("topic_id", pa.int32()),
            ]),
        )
        errors = validate_output(table)
        assert len(errors) > 0
        assert any("Missing column" in e or "columns" in e for e in errors)


# ---------------------------------------------------------------------------
# Test: Full Pipeline Integration
# ---------------------------------------------------------------------------

class TestStage5Integration:
    """Integration tests for the full Stage 5 pipeline."""

    def test_run_with_synthetic_data(self, tmp_path):
        """Full pipeline run with synthetic Parquet inputs."""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        articles_path, article_ids, dates = _make_articles_parquet(
            tmp_path, n_articles=50, n_days=30, base_date=base_date
        )
        topics_path = _make_topics_parquet(tmp_path, article_ids, n_topics=5)
        analysis_path = _make_analysis_parquet(tmp_path, article_ids)
        output_path = tmp_path / "analysis" / "timeseries.parquet"

        # Use reduced permutations for speed
        config = Stage5Config(pelt_permutation_iter=5)
        analyzer = Stage5TimeseriesAnalyzer(config=config)

        # Patch Prophet to avoid slow fit
        with patch(
            "src.analysis.stage5_timeseries._run_prophet", return_value=None
        ):
            table = analyzer.run(
                articles_path=articles_path,
                topics_path=topics_path,
                analysis_path=analysis_path,
                output_path=output_path,
            )

        # Verify output
        assert table.num_rows > 0
        assert table.num_columns == 17

        # Verify file was written
        assert output_path.exists()

        # Verify schema compliance
        errors = validate_output(table)
        assert errors == [], f"Schema validation errors: {errors}"

        # Verify metrics
        assert analyzer.metrics.n_topics > 0
        assert analyzer.metrics.n_series > 0
        assert analyzer.metrics.n_dates > 0
        assert analyzer.metrics.elapsed_seconds > 0

    def test_run_with_empty_articles(self, tmp_path):
        """Pipeline handles empty articles gracefully."""
        articles_path, _, _ = _make_articles_parquet(
            tmp_path, n_articles=0, n_days=1
        )
        # Need topics and analysis parquets even if empty
        schema_topics = pa.schema([
            pa.field("article_id", pa.utf8()),
            pa.field("topic_id", pa.int32()),
            pa.field("topic_label", pa.utf8()),
            pa.field("topic_probability", pa.float32()),
            pa.field("hdbscan_cluster_id", pa.int32()),
            pa.field("nmf_topic_id", pa.int32()),
            pa.field("lda_topic_id", pa.int32()),
            pa.field("published_at", pa.timestamp("us", tz="UTC")),
            pa.field("source", pa.utf8()),
        ])
        topics_path = tmp_path / "analysis" / "topics.parquet"
        topics_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(
            pa.table(
                {
                    "article_id": [],
                    "topic_id": pa.array([], type=pa.int32()),
                    "topic_label": [],
                    "topic_probability": pa.array([], type=pa.float32()),
                    "hdbscan_cluster_id": pa.array([], type=pa.int32()),
                    "nmf_topic_id": pa.array([], type=pa.int32()),
                    "lda_topic_id": pa.array([], type=pa.int32()),
                    "published_at": pa.array([], type=pa.timestamp("us", tz="UTC")),
                    "source": [],
                },
                schema=schema_topics,
            ),
            str(topics_path),
        )

        schema_fields = [
            pa.field("article_id", pa.utf8()),
            pa.field("sentiment_label", pa.utf8()),
            pa.field("sentiment_score", pa.float32()),
        ]
        for ecol in EMOTION_COLUMNS:
            schema_fields.append(pa.field(ecol, pa.float32()))
        schema_fields.append(pa.field("steeps_category", pa.utf8()))
        schema_fields.append(pa.field("importance_score", pa.float32()))

        analysis_path = tmp_path / "analysis" / "article_analysis.parquet"
        columns = {"article_id": [], "sentiment_label": [],
                    "sentiment_score": pa.array([], type=pa.float32())}
        for ecol in EMOTION_COLUMNS:
            columns[ecol] = pa.array([], type=pa.float32())
        columns["steeps_category"] = []
        columns["importance_score"] = pa.array([], type=pa.float32())
        pq.write_table(
            pa.table(columns, schema=pa.schema(schema_fields)),
            str(analysis_path),
        )

        output_path = tmp_path / "analysis" / "timeseries.parquet"

        analyzer = Stage5TimeseriesAnalyzer()
        table = analyzer.run(
            articles_path=articles_path,
            topics_path=topics_path,
            analysis_path=analysis_path,
            output_path=output_path,
        )

        assert table.num_rows == 0
        assert table.num_columns == 17
        errors = validate_output(table)
        assert errors == []

    def test_run_stage5_convenience(self, tmp_path):
        """Convenience function run_stage5() works with data_dir."""
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        data_dir = tmp_path / "data"
        _make_articles_parquet(
            data_dir, n_articles=30, n_days=20, base_date=base_date
        )
        article_ids = [f"art-{i:04d}" for i in range(30)]
        _make_topics_parquet(data_dir, article_ids, n_topics=3)
        _make_analysis_parquet(data_dir, article_ids)

        output_dir = data_dir / "analysis"

        config = Stage5Config(pelt_permutation_iter=5)

        with patch(
            "src.analysis.stage5_timeseries._run_prophet", return_value=None
        ):
            table = run_stage5(
                data_dir=str(data_dir),
                output_dir=str(output_dir),
                config=config,
            )

        assert table.num_rows > 0
        assert table.num_columns == 17
        assert (output_dir / "timeseries.parquet").exists()


# ---------------------------------------------------------------------------
# Test: Config and Metrics dataclasses
# ---------------------------------------------------------------------------

class TestConfigAndMetrics:
    """Tests for Stage5Config and Stage5Metrics."""

    def test_default_config(self):
        """Default config has expected values."""
        config = Stage5Config()
        assert config.stl_period == 7
        assert config.kleinberg_s == 2.0
        assert config.kleinberg_gamma == 1.0
        assert config.pelt_model == "rbf"
        assert config.prophet_top_k == 20
        assert config.ma_short_window == 3
        assert config.ma_long_window == 14
        assert config.wavelet_family == "db4"
        assert config.wavelet_level == 4

    def test_custom_config(self):
        """Custom config overrides defaults."""
        config = Stage5Config(stl_period=14, prophet_top_k=10)
        assert config.stl_period == 14
        assert config.prophet_top_k == 10
        # Others remain default
        assert config.kleinberg_s == 2.0

    def test_metrics_default(self):
        """Default metrics are all zero."""
        metrics = Stage5Metrics()
        assert metrics.n_topics == 0
        assert metrics.n_series == 0
        assert metrics.elapsed_seconds == 0.0


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_single_day_data(self, base_date):
        """Single day of data produces valid (sparse) output."""
        article_ids = ["a1"]
        dates = [base_date]
        topic_assignments = {"a1": 0}
        sentiment_scores = {"a1": 0.5}
        emotion_scores = {"a1": {ecol: 0.5 for ecol in EMOTION_COLUMNS}}

        series = _build_daily_series(
            article_ids, dates, topic_assignments,
            sentiment_scores, emotion_scores,
        )

        assert "topic_0_volume" in series
        assert len(series["topic_0_volume"]) == 1
        assert series["topic_0_volume"][base_date] == 1.0

    def test_all_nan_sentiment(self, base_date):
        """All-NaN sentiment series is handled gracefully."""
        article_ids = ["a1", "a2"]
        dates = [base_date, base_date + timedelta(days=1)]
        topic_assignments = {"a1": 0, "a2": 0}
        sentiment_scores = {"a1": float("nan"), "a2": float("nan")}
        emotion_scores = {
            aid: {ecol: float("nan") for ecol in EMOTION_COLUMNS}
            for aid in article_ids
        }

        series = _build_daily_series(
            article_ids, dates, topic_assignments,
            sentiment_scores, emotion_scores,
        )

        # Sentiment values should be NaN
        for day in [base_date, base_date + timedelta(days=1)]:
            val = series["topic_0_sentiment"][day]
            assert math.isnan(val)

    def test_missing_input_file(self, tmp_path):
        """Pipeline raises PipelineStageError for missing inputs."""
        analyzer = Stage5TimeseriesAnalyzer()

        with pytest.raises(PipelineStageError):
            analyzer.run(
                articles_path=tmp_path / "nonexistent.parquet",
                topics_path=tmp_path / "nonexistent2.parquet",
                analysis_path=tmp_path / "nonexistent3.parquet",
            )

    def test_data_class_fields(self):
        """TimeSeriesRecord has all expected fields."""
        rec = TimeSeriesRecord(
            series_id="test",
            topic_id=0,
            metric_type="volume",
            date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            value=10.0,
        )
        assert rec.series_id == "test"
        assert rec.topic_id == 0
        assert rec.trend is None
        assert rec.seasonal is None
        assert rec.is_changepoint is False
        assert rec.ma_signal is None
