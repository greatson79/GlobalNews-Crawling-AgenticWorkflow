"""Unit tests for src/analysis/pipeline.py -- Analysis Pipeline Orchestrator.

Tests cover:
    - AnalysisPipelineResult and StageResult dataclass construction
    - MemoryMonitor: RSS reading, cleanup, threshold enforcement
    - AnalysisPipeline: directory setup, dependency checking, path remapping
    - Stage execution: success path, error handling, skipping logic
    - Checkpoint support: resume from a specific stage
    - Full pipeline integration (with mocked stages)
    - run_analysis_pipeline convenience function
"""

from __future__ import annotations

import gc
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.pipeline import (
    INDEPENDENT_STAGES,
    MEMORY_ABORT_THRESHOLD_GB,
    MEMORY_WARNING_THRESHOLD_GB,
    STAGE_DEPENDENCIES,
    STAGE_NAMES,
    AnalysisPipeline,
    AnalysisPipelineResult,
    MemoryMonitor,
    StageResult,
    run_analysis_pipeline,
)
from src.utils.error_handler import (
    AnalysisError,
    MemoryLimitError,
    ModelLoadError,
    PipelineStageError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with date-partitioned subdirectories."""
    data_dir = tmp_path / "data"
    date = "2026-02-25"
    for subdir in [f"raw/{date}", f"processed/{date}", f"features/{date}",
                   f"analysis/{date}", f"output/{date}"]:
        (data_dir / subdir).mkdir(parents=True)
    return data_dir


@pytest.fixture
def pipeline(tmp_data_dir):
    """Create an AnalysisPipeline with a temporary data directory."""
    return AnalysisPipeline(
        data_dir=str(tmp_data_dir),
        date="2026-02-25",
        memory_abort_gb=10.0,
        memory_warning_gb=5.0,
    )


@pytest.fixture
def populated_data_dir(tmp_data_dir):
    """Create a data directory with dummy stage outputs for checkpoint testing.

    Files are placed in date-partitioned subdirectories matching the pipeline's
    _remap_path() expectations (data/{category}/2026-02-25/{file}).
    """
    date = "2026-02-25"
    # Stage 1 output
    (tmp_data_dir / "processed" / date / "articles.parquet").write_bytes(b"PARQUET_DUMMY" * 100)
    # Stage 2 outputs
    (tmp_data_dir / "features" / date / "embeddings.parquet").write_bytes(b"EMBED_DUMMY" * 100)
    (tmp_data_dir / "features" / date / "tfidf.parquet").write_bytes(b"TFIDF_DUMMY" * 100)
    (tmp_data_dir / "features" / date / "ner.parquet").write_bytes(b"NER_DUMMY" * 100)
    # Stage 3 output
    (tmp_data_dir / "analysis" / date / "article_analysis.parquet").write_bytes(b"AA_DUMMY" * 100)
    # Stage 4 outputs
    (tmp_data_dir / "analysis" / date / "topics.parquet").write_bytes(b"TOPICS_DUMMY" * 100)
    (tmp_data_dir / "analysis" / date / "networks.parquet").write_bytes(b"NET_DUMMY" * 100)
    # Stage 5 output
    (tmp_data_dir / "analysis" / date / "timeseries.parquet").write_bytes(b"TS_DUMMY" * 100)
    # Stage 6 output
    (tmp_data_dir / "analysis" / date / "cross_analysis.parquet").write_bytes(b"CROSS_DUMMY" * 100)
    # Stage 7 output
    (tmp_data_dir / "output" / date / "signals.parquet").write_bytes(b"SIGNALS_DUMMY" * 100)
    return tmp_data_dir


# =============================================================================
# StageResult Tests
# =============================================================================

class TestStageResult:
    """Tests for the StageResult dataclass."""

    def test_default_values(self):
        sr = StageResult()
        assert sr.stage_number == 0
        assert sr.stage_name == ""
        assert sr.success is False
        assert sr.elapsed_seconds == 0.0
        assert sr.peak_memory_gb == 0.0
        assert sr.article_count == 0
        assert sr.output_paths == []
        assert sr.error_message == ""
        assert sr.error_type == ""
        assert sr.skipped is False
        assert sr.skip_reason == ""

    def test_successful_stage(self):
        sr = StageResult(
            stage_number=2,
            stage_name="Feature Extraction",
            success=True,
            elapsed_seconds=45.3,
            peak_memory_gb=2.1,
            article_count=1000,
            output_paths=["/data/features/embeddings.parquet"],
        )
        assert sr.success is True
        assert sr.stage_number == 2
        assert sr.article_count == 1000

    def test_failed_stage(self):
        sr = StageResult(
            stage_number=3,
            stage_name="Article Analysis",
            success=False,
            error_message="SBERT model not found",
            error_type="ModelLoadError",
        )
        assert sr.success is False
        assert sr.error_type == "ModelLoadError"

    def test_skipped_stage(self):
        sr = StageResult(
            stage_number=7,
            stage_name="Signal Classification",
            skipped=True,
            skip_reason="Upstream stage failure",
        )
        assert sr.skipped is True
        assert "Upstream" in sr.skip_reason


# =============================================================================
# AnalysisPipelineResult Tests
# =============================================================================

class TestAnalysisPipelineResult:
    """Tests for the AnalysisPipelineResult dataclass."""

    def test_default_values(self):
        result = AnalysisPipelineResult()
        assert result.success is False
        assert result.stages == {}
        assert result.stages_completed == []
        assert result.stages_failed == []
        assert result.stages_skipped == []
        assert result.final_output_paths == {}
        assert result.date == ""

    def test_successful_pipeline(self):
        result = AnalysisPipelineResult(
            success=True,
            stages_completed=[1, 2, 3, 4, 5, 6, 7, 8],
            total_elapsed_seconds=300.0,
            peak_memory_gb=2.4,
            date="2026-02-25",
        )
        assert result.success is True
        assert len(result.stages_completed) == 8
        assert result.peak_memory_gb == 2.4


# =============================================================================
# MemoryMonitor Tests
# =============================================================================

class TestMemoryMonitor:
    """Tests for the MemoryMonitor class."""

    def test_get_rss_gb_returns_positive(self):
        rss = MemoryMonitor.get_rss_gb()
        assert rss > 0
        assert isinstance(rss, float)

    def test_check_and_log_normal(self):
        monitor = MemoryMonitor(abort_threshold_gb=100.0, warning_threshold_gb=50.0)
        rss = monitor.check_and_log("test_context")
        assert rss > 0
        assert monitor.peak_gb >= rss

    def test_check_and_log_abort_threshold(self):
        # Set a very low abort threshold to trigger the error
        monitor = MemoryMonitor(abort_threshold_gb=0.0001, warning_threshold_gb=0.00001)
        with pytest.raises(MemoryLimitError):
            monitor.check_and_log("test_abort")

    def test_peak_tracking(self):
        monitor = MemoryMonitor(abort_threshold_gb=100.0, warning_threshold_gb=50.0)
        monitor.check_and_log("first")
        first_peak = monitor.peak_gb
        monitor.check_and_log("second")
        assert monitor.peak_gb >= first_peak

    def test_cleanup_runs_gc(self):
        """Verify that cleanup() calls gc.collect()."""
        with patch("src.analysis.pipeline.gc.collect") as mock_gc:
            MemoryMonitor.cleanup()
            mock_gc.assert_called_once()

    def test_cleanup_handles_missing_torch(self):
        """cleanup() should not raise even if torch is not installed."""
        # This test simply verifies no exception is raised
        MemoryMonitor.cleanup()


# =============================================================================
# AnalysisPipeline Construction Tests
# =============================================================================

class TestAnalysisPipelineConstruction:
    """Tests for AnalysisPipeline initialization."""

    def test_default_construction(self, tmp_data_dir):
        pipe = AnalysisPipeline(data_dir=str(tmp_data_dir))
        assert pipe._data_dir == tmp_data_dir
        assert pipe._date  # Should be set to today

    def test_custom_date(self, tmp_data_dir):
        pipe = AnalysisPipeline(data_dir=str(tmp_data_dir), date="2025-12-31")
        assert pipe._date == "2025-12-31"
        assert pipe._raw_dir == tmp_data_dir / "raw" / "2025-12-31"

    def test_custom_memory_thresholds(self, tmp_data_dir):
        pipe = AnalysisPipeline(
            data_dir=str(tmp_data_dir),
            memory_abort_gb=8.0,
            memory_warning_gb=4.0,
        )
        assert pipe._memory._abort_threshold_gb == 8.0
        assert pipe._memory._warning_threshold_gb == 4.0


# =============================================================================
# Directory Management Tests
# =============================================================================

class TestDirectoryManagement:
    """Tests for directory creation and path remapping."""

    def test_ensure_directories(self, pipeline, tmp_data_dir):
        # Remove one directory to test creation
        import shutil
        features_dir = tmp_data_dir / "features"
        if features_dir.exists():
            shutil.rmtree(features_dir)
        assert not features_dir.exists()

        pipeline._ensure_directories()
        assert features_dir.exists()

    def test_remap_path(self, pipeline, tmp_data_dir):
        from src.config.constants import ARTICLES_PARQUET_PATH, DATA_DIR
        remapped = pipeline._remap_path(ARTICLES_PARQUET_PATH)
        # _remap_path inserts the date subdirectory for date-partitioned categories
        expected = tmp_data_dir / "processed" / "2026-02-25" / "articles.parquet"
        assert remapped == expected

    def test_remap_path_non_data_dir(self, pipeline):
        # Path not under DATA_DIR should return as-is
        foreign_path = Path("/some/other/path/file.parquet")
        assert pipeline._remap_path(foreign_path) == foreign_path


# =============================================================================
# Dependency Checking Tests
# =============================================================================

class TestDependencyChecking:
    """Tests for checkpoint dependency validation."""

    def test_stage1_no_dependencies(self, pipeline):
        missing = pipeline._check_dependencies(1)
        assert missing == []

    def test_stage2_missing_articles(self, pipeline):
        missing = pipeline._check_dependencies(2)
        assert len(missing) == 1
        assert "articles.parquet" in str(missing[0])

    def test_stage2_dependencies_met(self, pipeline, tmp_data_dir):
        # Create the required file in date-partitioned directory
        (tmp_data_dir / "processed" / "2026-02-25" / "articles.parquet").write_bytes(b"dummy")
        missing = pipeline._check_dependencies(2)
        assert missing == []

    def test_stage5_dependencies(self, populated_data_dir):
        pipe = AnalysisPipeline(data_dir=str(populated_data_dir), date="2026-02-25")
        missing = pipe._check_dependencies(5)
        assert missing == []

    def test_all_stages_have_dependency_entries(self):
        for stage in range(1, 9):
            assert stage in STAGE_DEPENDENCIES


# =============================================================================
# Stage Execution Tests (Mocked)
# =============================================================================

class TestStageExecution:
    """Tests for individual stage execution with mocked stage runners."""

    def test_successful_stage_execution(self, pipeline):
        """Verify successful stage execution returns correct StageResult."""
        mock_output = {"article_count": 500, "output_paths": ["/data/out.parquet"]}

        with patch.object(pipeline, "_get_stage_runner") as mock_runner:
            mock_runner.return_value = MagicMock(return_value=mock_output)
            with patch.object(pipeline._memory, "check_and_log", return_value=1.5):
                result = pipeline._run_stage(1)

        assert result.success is True
        assert result.article_count == 500
        assert result.output_paths == ["/data/out.parquet"]
        assert result.elapsed_seconds >= 0

    def test_pipeline_stage_error(self, pipeline):
        """Verify PipelineStageError is handled gracefully."""
        def failing_runner(input_path=None):
            raise PipelineStageError("Stage failed", stage_name="test")

        with patch.object(pipeline, "_get_stage_runner", return_value=failing_runner):
            with patch.object(pipeline._memory, "check_and_log", return_value=1.0):
                result = pipeline._run_stage(1)

        assert result.success is False
        assert result.error_type == "PipelineStageError"
        assert "Stage failed" in result.error_message

    def test_model_load_error(self, pipeline):
        """Verify ModelLoadError is handled gracefully."""
        def failing_runner(input_path=None):
            raise ModelLoadError("SBERT not found", model_name="sbert")

        with patch.object(pipeline, "_get_stage_runner", return_value=failing_runner):
            with patch.object(pipeline._memory, "check_and_log", return_value=1.0):
                result = pipeline._run_stage(2)

        assert result.success is False
        assert result.error_type == "ModelLoadError"

    def test_file_not_found_error(self, pipeline):
        """Verify FileNotFoundError is handled gracefully."""
        def failing_runner(input_path=None):
            raise FileNotFoundError("articles.parquet not found")

        with patch.object(pipeline, "_get_stage_runner", return_value=failing_runner):
            with patch.object(pipeline._memory, "check_and_log", return_value=1.0):
                result = pipeline._run_stage(1)

        assert result.success is False
        assert result.error_type == "FileNotFoundError"

    def test_unexpected_error(self, pipeline):
        """Verify unexpected exceptions are caught and logged."""
        def failing_runner(input_path=None):
            raise RuntimeError("Something unexpected")

        with patch.object(pipeline, "_get_stage_runner", return_value=failing_runner):
            with patch.object(pipeline._memory, "check_and_log", return_value=1.0):
                result = pipeline._run_stage(3)

        assert result.success is False
        assert result.error_type == "RuntimeError"
        assert "unexpected" in result.error_message.lower()

    def test_memory_limit_error_before_stage(self, pipeline):
        """Verify MemoryLimitError before stage start is handled."""
        with patch.object(
            pipeline._memory, "check_and_log",
            side_effect=MemoryLimitError("OOM", current_gb=11.0, limit_gb=10.0),
        ):
            result = pipeline._run_stage(1)

        assert result.success is False
        assert result.error_type == "MemoryLimitError"

    def test_invalid_stage_number(self, pipeline):
        """Verify ValueError for invalid stage numbers."""
        with pytest.raises(ValueError, match="Invalid stage number"):
            pipeline._get_stage_runner(0)
        with pytest.raises(ValueError, match="Invalid stage number"):
            pipeline._get_stage_runner(9)


# =============================================================================
# Full Pipeline Run Tests (Mocked Stages)
# =============================================================================

class TestFullPipelineRun:
    """Tests for the full pipeline.run() method with mocked stages."""

    def _mock_stage_runner(self, pipeline, success=True, article_count=100):
        """Create a mock that makes all stage runners succeed or fail."""
        mock_output = {"article_count": article_count, "output_paths": []}
        if success:
            runner = MagicMock(return_value=mock_output)
        else:
            def runner(input_path=None):
                raise PipelineStageError("Failed")
        return runner

    def test_all_stages_succeed(self, pipeline):
        """Full pipeline run with all stages succeeding."""
        mock_output = {"article_count": 100, "output_paths": []}

        with patch.object(pipeline, "_run_stage") as mock_run:
            mock_run.return_value = StageResult(
                stage_number=1,
                stage_name="Test",
                success=True,
                article_count=100,
            )
            with patch.object(pipeline._memory, "check_and_log", return_value=1.0):
                result = pipeline.run(stages=[1, 2, 3])

        assert result.success is True
        assert result.stages_completed == [1, 2, 3]
        assert result.stages_failed == []

    def test_critical_stage_failure_blocks_later_stages(self, pipeline):
        """When a critical stage fails, later non-independent stages are skipped."""
        call_count = 0

        def mock_run_stage(stage_num, input_path=None):
            nonlocal call_count
            call_count += 1
            if stage_num == 2:
                return StageResult(
                    stage_number=2, stage_name="Feature Extraction",
                    success=False, error_message="Failed",
                    error_type="PipelineStageError",
                )
            return StageResult(
                stage_number=stage_num,
                stage_name=STAGE_NAMES.get(stage_num, ""),
                success=True,
            )

        with patch.object(pipeline, "_run_stage", side_effect=mock_run_stage):
            with patch.object(pipeline._memory, "check_and_log", return_value=1.0):
                result = pipeline.run(stages=[1, 2, 3, 4])

        assert result.success is False
        assert 2 in result.stages_failed
        # Stage 3 and 4 should be skipped because 2 (critical) failed
        assert 3 in result.stages_skipped
        assert 4 in result.stages_skipped

    def test_independent_stage_failure_does_not_block(self, pipeline, populated_data_dir):
        """Stages 5 and 6 (independent) can fail without blocking stage 7+."""
        # Re-create pipeline with populated data directory
        pipe = AnalysisPipeline(data_dir=str(populated_data_dir), date="2026-02-25")

        def mock_run_stage(stage_num, input_path=None):
            if stage_num == 5:
                return StageResult(
                    stage_number=5, stage_name="Time Series",
                    success=False, error_message="prophet not installed",
                    error_type="ImportError",
                )
            return StageResult(
                stage_number=stage_num,
                stage_name=STAGE_NAMES.get(stage_num, ""),
                success=True,
            )

        with patch.object(pipe, "_run_stage", side_effect=mock_run_stage):
            with patch.object(pipe._memory, "check_and_log", return_value=1.0):
                # Stage 5 is independent; stage 6 should still run
                # but stage 7 depends on stage 5 output, so it depends on
                # whether the output file exists (populated data has it)
                result = pipe.run(stages=[5, 6])

        assert 5 in result.stages_failed
        assert 6 in result.stages_completed

    def test_checkpoint_resume_from_stage3(self, populated_data_dir):
        """Starting from stage 3 should work if stages 1-2 outputs exist."""
        pipe = AnalysisPipeline(data_dir=str(populated_data_dir), date="2026-02-25")

        with patch.object(pipe, "_run_stage") as mock_run:
            mock_run.return_value = StageResult(
                stage_number=3, stage_name="Article Analysis",
                success=True, article_count=500,
            )
            with patch.object(pipe._memory, "check_and_log", return_value=1.0):
                result = pipe.run(stages=[3])

        assert result.success is True
        assert 3 in result.stages_completed

    def test_checkpoint_resume_fails_missing_deps(self, tmp_data_dir):
        """Starting from stage 3 without stage 1-2 outputs should fail."""
        pipe = AnalysisPipeline(data_dir=str(tmp_data_dir), date="2026-02-25")
        result = pipe.run(stages=[3])

        assert result.success is False
        assert 3 in result.stages_failed
        assert "missing prior outputs" in result.stages[3].error_message.lower()

    def test_pipeline_result_has_timing(self, pipeline):
        """Pipeline result should include timing information."""
        with patch.object(pipeline, "_run_stage") as mock_run:
            mock_run.return_value = StageResult(
                stage_number=1, stage_name="Test", success=True,
            )
            with patch.object(pipeline._memory, "check_and_log", return_value=0.5):
                result = pipeline.run(stages=[1])

        assert result.total_elapsed_seconds >= 0
        assert result.started_at != ""
        assert result.finished_at != ""
        assert result.date == "2026-02-25"


# =============================================================================
# Inter-Stage Cleanup Tests
# =============================================================================

class TestInterStageCleanup:
    """Tests for inter-stage memory cleanup."""

    def test_cleanup_calls_gc_and_memory_check(self, pipeline):
        with patch("src.analysis.pipeline.MemoryMonitor.cleanup") as mock_cleanup:
            with patch.object(pipeline._memory, "check_and_log", return_value=1.0):
                pipeline._inter_stage_cleanup(1)

        mock_cleanup.assert_called_once()

    def test_cleanup_handles_high_memory_gracefully(self, pipeline):
        """High memory after cleanup logs warning but does not raise."""
        with patch("src.analysis.pipeline.MemoryMonitor.cleanup"):
            with patch.object(
                pipeline._memory, "check_and_log",
                side_effect=MemoryLimitError("high", current_gb=11.0, limit_gb=10.0),
            ):
                # Should not raise
                pipeline._inter_stage_cleanup(2)


# =============================================================================
# Final Output Collection Tests
# =============================================================================

class TestFinalOutputCollection:
    """Tests for collecting final output paths."""

    def test_no_outputs(self, pipeline):
        outputs = pipeline._collect_final_outputs()
        assert outputs == {}

    def test_with_outputs(self, pipeline, tmp_data_dir):
        (tmp_data_dir / "output" / "2026-02-25" / "analysis.parquet").write_bytes(b"data")
        (tmp_data_dir / "output" / "2026-02-25" / "signals.parquet").write_bytes(b"data")
        outputs = pipeline._collect_final_outputs()
        assert "analysis.parquet" in outputs
        assert "signals.parquet" in outputs
        assert "topics.parquet" not in outputs  # Not created


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestRunAnalysisPipeline:
    """Tests for the run_analysis_pipeline() convenience function."""

    def test_calls_pipeline_run(self, tmp_data_dir):
        with patch("src.analysis.pipeline.AnalysisPipeline.run") as mock_run:
            mock_run.return_value = AnalysisPipelineResult(success=True)
            result = run_analysis_pipeline(
                data_dir=str(tmp_data_dir),
                date="2026-02-25",
                stages=[1],
            )
        assert result.success is True
        mock_run.assert_called_once()


# =============================================================================
# Constants Validation Tests
# =============================================================================

class TestConstants:
    """Tests for pipeline constants and configuration."""

    def test_all_stages_have_names(self):
        for i in range(1, 9):
            assert i in STAGE_NAMES
            assert isinstance(STAGE_NAMES[i], str)
            assert len(STAGE_NAMES[i]) > 0

    def test_all_stages_have_dependencies(self):
        for i in range(1, 9):
            assert i in STAGE_DEPENDENCIES
            assert isinstance(STAGE_DEPENDENCIES[i], list)

    def test_stage1_has_no_parquet_dependencies(self):
        """Stage 1 reads from JSONL, not from prior Parquet outputs."""
        assert STAGE_DEPENDENCIES[1] == []

    def test_independent_stages(self):
        assert 5 in INDEPENDENT_STAGES
        assert 6 in INDEPENDENT_STAGES
        assert 1 not in INDEPENDENT_STAGES
        assert 7 not in INDEPENDENT_STAGES

    def test_memory_thresholds(self):
        assert MEMORY_ABORT_THRESHOLD_GB > MEMORY_WARNING_THRESHOLD_GB
        assert MEMORY_WARNING_THRESHOLD_GB > 0


# =============================================================================
# Stage Runner Dispatch Tests
# =============================================================================

class TestStageRunnerDispatch:
    """Tests for _get_stage_runner dispatch."""

    def test_all_stages_have_runners(self, pipeline):
        for i in range(1, 9):
            runner = pipeline._get_stage_runner(i)
            assert callable(runner)

    def test_stage_runners_are_distinct(self, pipeline):
        runners = [pipeline._get_stage_runner(i) for i in range(1, 9)]
        # Each stage should have a distinct runner method
        runner_ids = [id(r) for r in runners]
        assert len(set(runner_ids)) == 8


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_stages_list_runs_all(self, pipeline):
        """Passing stages=None should attempt all 8 stages.

        Note: Stage 7 has a dependency check that runs before _run_stage;
        since mocked stages do not create files, stage 7 may be skipped.
        We verify that stages 1-6 and 8 are attempted (7 run + 1 skipped = 8 total).
        """
        with patch.object(pipeline, "_run_stage") as mock_run:
            mock_run.return_value = StageResult(
                stage_number=1, stage_name="Test", success=True,
            )
            with patch.object(pipeline._memory, "check_and_log", return_value=0.5):
                result = pipeline.run(stages=None)

        # All 8 stages should be accounted for (run or skipped)
        total_accounted = (
            len(result.stages_completed)
            + len(result.stages_failed)
            + len(result.stages_skipped)
        )
        assert total_accounted == 8

    def test_single_stage_run(self, pipeline):
        """Running a single stage should work correctly."""
        with patch.object(pipeline, "_run_stage") as mock_run:
            mock_run.return_value = StageResult(
                stage_number=1, stage_name="Preprocessing", success=True,
            )
            with patch.object(pipeline._memory, "check_and_log", return_value=0.5):
                result = pipeline.run(stages=[1])

        assert result.success is True
        assert len(result.stages) == 1
        assert 1 in result.stages

    def test_stages_are_sorted(self, pipeline):
        """Stages should be executed in numerical order regardless of input order."""
        call_order = []

        def track_stage(stage_num, input_path=None):
            call_order.append(stage_num)
            return StageResult(
                stage_number=stage_num, stage_name="Test", success=True,
            )

        with patch.object(pipeline, "_run_stage", side_effect=track_stage):
            with patch.object(pipeline._memory, "check_and_log", return_value=0.5):
                pipeline.run(stages=[3, 1, 2])

        assert call_order == [1, 2, 3]
