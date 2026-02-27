"""Unit tests for self_recovery module.

Tests cover:
    - LockFileManager: acquire/release/stale detection/concurrent protection
    - HealthChecker: all health check pass/fail scenarios
    - CheckpointManager: save/load/resume/clear
    - CleanupManager: stale temps, old logs, incomplete runs
    - RecoveryOrchestrator: integration of all subsystems
    - TimeoutHandler: timeout context manager
    - Edge cases: disk full simulation, permission errors, corrupted files

Test count target: >= 30 tests
"""

import json
import os
import signal
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.self_recovery import (
    CheckpointManager,
    CleanupManager,
    HealthChecker,
    HealthReport,
    LockFileManager,
    PipelineCheckpoint,
    RecoveryOrchestrator,
    TimeoutHandler,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def lock_dir(tmp_path):
    """Temporary directory for lock files."""
    d = tmp_path / "locks"
    d.mkdir()
    return d


@pytest.fixture
def project_dir(tmp_path):
    """Temporary project directory with data structure."""
    proj = tmp_path / "project"
    proj.mkdir()
    (proj / "data" / "raw").mkdir(parents=True)
    (proj / "data" / "processed").mkdir(parents=True)
    (proj / "data" / "logs").mkdir(parents=True)
    (proj / "data" / "config").mkdir(parents=True)
    # Create a minimal sources.yaml
    (proj / "data" / "config" / "sources.yaml").write_text(
        "sources:\n  test_site:\n    name: Test\n"
    )
    return proj


@pytest.fixture
def lock_mgr(lock_dir, project_dir):
    """LockFileManager with temp directories."""
    return LockFileManager(
        lock_name="test",
        lock_dir=lock_dir,
        project_root=project_dir,
    )


@pytest.fixture
def health_checker(project_dir):
    """HealthChecker with temp project."""
    return HealthChecker(project_root=project_dir, min_disk_gb=0.001)


@pytest.fixture
def checkpoint_mgr(project_dir):
    """CheckpointManager with temp project."""
    return CheckpointManager(project_root=project_dir)


@pytest.fixture
def cleanup_mgr(project_dir):
    """CleanupManager with temp project."""
    return CleanupManager(project_root=project_dir)


@pytest.fixture
def orchestrator(project_dir):
    """RecoveryOrchestrator with temp project."""
    return RecoveryOrchestrator(project_root=project_dir)


# =============================================================================
# LockFileManager Tests
# =============================================================================

class TestLockFileManager:
    """Tests for LockFileManager."""

    def test_acquire_and_release(self, lock_mgr):
        """Lock can be acquired and released."""
        assert lock_mgr.acquire() is True
        assert lock_mgr.lock_path.exists()
        assert lock_mgr.release() is True
        assert not lock_mgr.lock_path.exists()

    def test_acquire_twice_fails(self, lock_mgr):
        """Second acquire fails while lock is held."""
        assert lock_mgr.acquire() is True
        assert lock_mgr.acquire() is False
        lock_mgr.release()

    def test_is_locked(self, lock_mgr):
        """is_locked returns correct state."""
        assert lock_mgr.is_locked() is False
        lock_mgr.acquire()
        assert lock_mgr.is_locked() is True
        lock_mgr.release()
        assert lock_mgr.is_locked() is False

    def test_stale_lock_dead_pid(self, lock_dir, project_dir):
        """Stale lock with dead PID is cleaned and reacquirable."""
        mgr = LockFileManager(
            lock_name="stale_test",
            lock_dir=lock_dir,
            project_root=project_dir,
        )
        # Write a lock file with a definitely-dead PID
        mgr.lock_path.write_text(json.dumps({
            "pid": 999999999,  # Extremely unlikely to be running
            "acquired_at": "2020-01-01T00:00:00Z",
            "lock_name": "stale_test",
        }))

        # Should detect stale lock and acquire
        assert mgr.acquire() is True
        mgr.release()

    def test_stale_lock_old_age(self, lock_dir, project_dir):
        """Lock older than threshold is detected as stale."""
        mgr = LockFileManager(
            lock_name="old_test",
            lock_dir=lock_dir,
            stale_threshold_seconds=1,  # 1 second threshold
            project_root=project_dir,
        )
        mgr.acquire()
        time.sleep(1.1)
        assert mgr._is_stale() is True
        mgr.release()

    def test_force_release(self, lock_mgr):
        """Force release removes lock regardless of holder."""
        lock_mgr.acquire()
        assert lock_mgr.force_release() is True
        assert not lock_mgr.lock_path.exists()

    def test_release_not_our_lock(self, lock_dir, project_dir):
        """Release fails if lock held by another PID."""
        mgr = LockFileManager(
            lock_name="foreign",
            lock_dir=lock_dir,
            project_root=project_dir,
        )
        mgr.lock_path.write_text(json.dumps({
            "pid": os.getpid() + 99999,
            "acquired_at": "2026-01-01T00:00:00Z",
            "lock_name": "foreign",
        }))
        assert mgr.release() is False

    def test_lock_file_content(self, lock_mgr):
        """Lock file contains correct PID and metadata."""
        lock_mgr.acquire()
        data = json.loads(lock_mgr.lock_path.read_text())
        assert data["pid"] == os.getpid()
        assert data["lock_name"] == "test"
        assert "acquired_at" in data
        lock_mgr.release()

    def test_release_nonexistent_lock(self, lock_mgr):
        """Releasing a non-existent lock succeeds."""
        assert lock_mgr.release() is True

    def test_is_process_running_self(self):
        """Current process is detected as running."""
        assert LockFileManager._is_process_running(os.getpid()) is True

    def test_is_process_running_dead(self):
        """Dead PID is detected as not running."""
        assert LockFileManager._is_process_running(999999999) is False

    def test_is_process_running_invalid(self):
        """Invalid PID returns False."""
        assert LockFileManager._is_process_running(0) is False
        assert LockFileManager._is_process_running(-1) is False


# =============================================================================
# HealthChecker Tests
# =============================================================================

class TestHealthChecker:
    """Tests for HealthChecker."""

    def test_all_checks_pass(self, health_checker):
        """All health checks pass with valid project structure."""
        report = health_checker.run_all_checks()
        assert report.healthy is True
        assert all(v[0] for v in report.checks.values()), (
            f"Failed checks: {[(k, v) for k, v in report.checks.items() if not v[0]]}"
        )

    def test_disk_space_check(self, health_checker):
        """Disk space check passes with minimal threshold."""
        passed, detail = health_checker._check_disk_space()
        assert passed is True
        assert "free=" in detail

    def test_disk_space_insufficient(self, project_dir):
        """Disk space check fails with unreasonably high threshold."""
        checker = HealthChecker(project_root=project_dir, min_disk_gb=999999)
        passed, detail = checker._check_disk_space()
        assert passed is False

    def test_python_version_check(self, health_checker):
        """Python version check passes on current interpreter."""
        passed, detail = health_checker._check_python_version()
        assert passed is True

    def test_critical_deps_check(self, health_checker):
        """Critical deps check verifies yaml package."""
        passed, detail = health_checker._check_critical_deps()
        assert passed is True
        assert "OK" in detail

    def test_data_dirs_check(self, health_checker):
        """Data directories check passes with existing dirs."""
        passed, detail = health_checker._check_data_dirs()
        assert passed is True

    def test_config_files_check(self, health_checker):
        """Config files check passes with sources.yaml present."""
        passed, detail = health_checker._check_config_files()
        assert passed is True

    def test_config_files_missing(self, tmp_path):
        """Config files check fails when sources.yaml missing."""
        proj = tmp_path / "empty_proj"
        proj.mkdir()
        checker = HealthChecker(project_root=proj)
        passed, detail = checker._check_config_files()
        assert passed is False
        assert "missing" in detail

    def test_log_dir_writable(self, health_checker):
        """Log dir write check passes."""
        passed, detail = health_checker._check_log_dir()
        assert passed is True

    def test_health_report_to_dict(self, health_checker):
        """HealthReport serializes to dict correctly."""
        report = health_checker.run_all_checks()
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "healthy" in d
        assert "checks" in d
        assert "python_version" in d


# =============================================================================
# CheckpointManager Tests
# =============================================================================

class TestCheckpointManager:
    """Tests for CheckpointManager."""

    def test_save_and_load(self, checkpoint_mgr):
        """Checkpoint can be saved and loaded."""
        cp = PipelineCheckpoint(
            pipeline_type="full",
            date="2026-02-26",
            current_phase="crawl",
            status="running",
        )
        checkpoint_mgr.save(cp)
        loaded = checkpoint_mgr.load()
        assert loaded is not None
        assert loaded.pipeline_type == "full"
        assert loaded.date == "2026-02-26"
        assert loaded.status == "running"

    def test_load_nonexistent(self, checkpoint_mgr):
        """Loading non-existent checkpoint returns None."""
        assert checkpoint_mgr.load() is None

    def test_clear(self, checkpoint_mgr):
        """Clearing removes checkpoint file."""
        cp = PipelineCheckpoint(date="2026-02-26", status="running")
        checkpoint_mgr.save(cp)
        assert checkpoint_mgr.checkpoint_path.exists()
        checkpoint_mgr.clear()
        assert not checkpoint_mgr.checkpoint_path.exists()

    def test_update_crawl_progress_success(self, checkpoint_mgr):
        """Crawl progress updates sites_completed."""
        cp = PipelineCheckpoint(date="2026-02-26", status="running", current_phase="crawl")
        checkpoint_mgr.save(cp)
        checkpoint_mgr.update_crawl_progress("chosun", success=True)
        loaded = checkpoint_mgr.load()
        assert "chosun" in loaded.sites_completed

    def test_update_crawl_progress_failure(self, checkpoint_mgr):
        """Failed crawl adds to sites_failed."""
        cp = PipelineCheckpoint(date="2026-02-26", status="running", current_phase="crawl")
        checkpoint_mgr.save(cp)
        checkpoint_mgr.update_crawl_progress("broken_site", success=False)
        loaded = checkpoint_mgr.load()
        assert "broken_site" in loaded.sites_failed

    def test_update_analysis_stage(self, checkpoint_mgr):
        """Analysis stage update tracks progress."""
        cp = PipelineCheckpoint(
            date="2026-02-26", status="running",
            current_phase="analyze", crawl_completed=True,
        )
        checkpoint_mgr.save(cp)
        checkpoint_mgr.update_analysis_stage(3, success=True)
        loaded = checkpoint_mgr.load()
        assert loaded.analysis_stage == 3

    def test_mark_completed(self, checkpoint_mgr):
        """mark_completed sets status correctly."""
        cp = PipelineCheckpoint(date="2026-02-26", status="running")
        checkpoint_mgr.save(cp)
        checkpoint_mgr.mark_completed()
        loaded = checkpoint_mgr.load()
        assert loaded.status == "completed"

    def test_mark_failed(self, checkpoint_mgr):
        """mark_failed records error message."""
        cp = PipelineCheckpoint(date="2026-02-26", status="running")
        checkpoint_mgr.save(cp)
        checkpoint_mgr.mark_failed("Stage 5 OOM")
        loaded = checkpoint_mgr.load()
        assert loaded.status == "failed"
        assert "OOM" in loaded.error_message

    def test_get_resume_args_crawl(self, checkpoint_mgr):
        """Resume args for interrupted crawl."""
        # Write checkpoint directly to avoid save() overwriting PID
        data = {
            "pipeline_type": "full",
            "date": "2026-02-26",
            "started_at": "2026-02-26T00:00:00Z",
            "last_updated": "2026-02-26T00:00:00Z",
            "current_phase": "crawl",
            "crawl_completed": False,
            "analysis_stage": 0,
            "sites_completed": [],
            "sites_failed": ["broken_site"],
            "status": "running",
            "error_message": "",
            "pid": 999999999,  # dead PID
        }
        checkpoint_mgr.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_mgr.checkpoint_path.write_text(json.dumps(data))
        args = checkpoint_mgr.get_resume_args()
        assert args is not None
        assert args["mode"] == "full"
        assert "broken_site" in args.get("retry_sites", [])

    def test_get_resume_args_analysis(self, checkpoint_mgr):
        """Resume args for interrupted analysis."""
        # Write checkpoint directly to avoid save() overwriting PID
        data = {
            "pipeline_type": "full",
            "date": "2026-02-26",
            "started_at": "2026-02-26T00:00:00Z",
            "last_updated": "2026-02-26T00:00:00Z",
            "current_phase": "analyze",
            "crawl_completed": True,
            "analysis_stage": 4,
            "sites_completed": [],
            "sites_failed": [],
            "status": "running",
            "error_message": "",
            "pid": 999999999,  # dead PID
        }
        checkpoint_mgr.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_mgr.checkpoint_path.write_text(json.dumps(data))
        args = checkpoint_mgr.get_resume_args()
        assert args is not None
        assert args["mode"] == "analyze"
        assert args["start_stage"] == 5

    def test_get_resume_args_completed(self, checkpoint_mgr):
        """No resume args for completed checkpoint."""
        cp = PipelineCheckpoint(date="2026-02-26", status="completed")
        checkpoint_mgr.save(cp)
        args = checkpoint_mgr.get_resume_args()
        assert args is None

    def test_corrupted_checkpoint(self, checkpoint_mgr):
        """Corrupted checkpoint file returns None on load."""
        checkpoint_mgr.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_mgr.checkpoint_path.write_text("not valid json {{{")
        loaded = checkpoint_mgr.load()
        assert loaded is None

    def test_checkpoint_to_dict(self):
        """PipelineCheckpoint serializes correctly."""
        cp = PipelineCheckpoint(
            pipeline_type="full", date="2026-02-26",
            sites_completed=["a", "b"],
        )
        d = cp.to_dict()
        assert d["pipeline_type"] == "full"
        assert d["sites_completed"] == ["a", "b"]

    def test_checkpoint_from_dict(self):
        """PipelineCheckpoint deserializes correctly."""
        data = {
            "pipeline_type": "analyze",
            "date": "2026-02-26",
            "analysis_stage": 5,
            "unknown_field": "ignored",
        }
        cp = PipelineCheckpoint.from_dict(data)
        assert cp.pipeline_type == "analyze"
        assert cp.analysis_stage == 5


# =============================================================================
# CleanupManager Tests
# =============================================================================

class TestCleanupManager:
    """Tests for CleanupManager."""

    def test_cleanup_stale_temps(self, cleanup_mgr, project_dir):
        """Stale temp files are removed."""
        temp_file = project_dir / "data" / "raw" / "test.tmp"
        temp_file.write_text("stale data")
        # Set mtime to 48 hours ago
        old_time = time.time() - 48 * 3600
        os.utime(str(temp_file), (old_time, old_time))
        removed = cleanup_mgr.cleanup_stale_temps(max_age_hours=24)
        assert removed >= 1
        assert not temp_file.exists()

    def test_cleanup_fresh_temps_preserved(self, cleanup_mgr, project_dir):
        """Fresh temp files are NOT removed."""
        temp_file = project_dir / "data" / "raw" / "fresh.tmp"
        temp_file.write_text("fresh data")
        removed = cleanup_mgr.cleanup_stale_temps(max_age_hours=24)
        assert temp_file.exists()

    def test_rotate_old_logs(self, cleanup_mgr, project_dir):
        """Old rotated log files are removed."""
        log_dir = project_dir / "data" / "logs"
        old_log = log_dir / "crawl.log.3"
        old_log.write_text("old log data")
        old_time = time.time() - 60 * 86400  # 60 days old
        os.utime(str(old_log), (old_time, old_time))
        removed = cleanup_mgr.rotate_old_logs(max_age_days=30)
        assert removed >= 1
        assert not old_log.exists()

    def test_active_logs_preserved(self, cleanup_mgr, project_dir):
        """Active log files (without numeric suffix) are NOT removed."""
        log_dir = project_dir / "data" / "logs"
        active_log = log_dir / "crawl.log"
        active_log.write_text("active log")
        old_time = time.time() - 60 * 86400
        os.utime(str(active_log), (old_time, old_time))
        cleanup_mgr.rotate_old_logs(max_age_days=30)
        assert active_log.exists()

    def test_disk_usage_report(self, cleanup_mgr):
        """Disk usage report contains expected keys."""
        report = cleanup_mgr.get_disk_usage_report()
        assert "disk_free_gb" in report
        assert "disk_total_gb" in report
        assert "directories_mb" in report

    def test_run_all(self, cleanup_mgr):
        """run_all returns counts for each operation."""
        result = cleanup_mgr.run_all()
        assert "stale_temps" in result
        assert "old_logs" in result
        assert "incomplete_runs" in result


# =============================================================================
# RecoveryOrchestrator Tests
# =============================================================================

class TestRecoveryOrchestrator:
    """Tests for RecoveryOrchestrator."""

    def test_pre_run_check(self, orchestrator):
        """Pre-run check returns a HealthReport."""
        report = orchestrator.pre_run_check()
        assert isinstance(report, HealthReport)
        assert report.healthy is True

    def test_get_lock_manager(self, orchestrator):
        """Lock manager can be obtained for different names."""
        daily = orchestrator.get_lock_manager("daily")
        weekly = orchestrator.get_lock_manager("weekly")
        assert daily.lock_path != weekly.lock_path

    def test_get_status(self, orchestrator):
        """Full status report contains all sections."""
        status = orchestrator.get_status()
        assert "health" in status
        assert "locks" in status
        assert "checkpoint" in status
        assert "disk" in status
        assert "timestamp" in status

    def test_run_cleanup(self, orchestrator):
        """Cleanup returns operation counts."""
        result = orchestrator.run_cleanup()
        assert isinstance(result, dict)

    def test_attempt_recovery_no_issues(self, orchestrator):
        """Recovery reports no issues when system is clean."""
        result = orchestrator.attempt_recovery()
        assert result["strategy"] == "none" or result["recovery_needed"] is False


# =============================================================================
# TimeoutHandler Tests
# =============================================================================

class TestTimeoutHandler:
    """Tests for TimeoutHandler."""

    @pytest.mark.skipif(
        not hasattr(signal, "SIGALRM"),
        reason="SIGALRM not available on this platform",
    )
    def test_timeout_triggers(self):
        """Timeout raises TimeoutError after specified seconds."""
        with pytest.raises(TimeoutError):
            with TimeoutHandler(timeout_seconds=1, message="test timeout"):
                time.sleep(3)

    @pytest.mark.skipif(
        not hasattr(signal, "SIGALRM"),
        reason="SIGALRM not available on this platform",
    )
    def test_no_timeout_on_quick_operation(self):
        """Quick operations complete without timeout."""
        with TimeoutHandler(timeout_seconds=10, message="should not fire"):
            result = 1 + 1
        assert result == 2

    def test_timeout_context_manager_enter_exit(self):
        """Context manager enters and exits cleanly."""
        handler = TimeoutHandler(timeout_seconds=60)
        handler.__enter__()
        handler.__exit__(None, None, None)


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Edge case and error condition tests."""

    def test_lock_with_corrupt_json(self, lock_dir, project_dir):
        """Lock file with corrupt JSON is treated as stale."""
        mgr = LockFileManager(
            lock_name="corrupt",
            lock_dir=lock_dir,
            project_root=project_dir,
        )
        mgr.lock_path.write_text("this is not json!")
        # _read_lock_pid should return -1
        assert mgr._read_lock_pid() == -1
        # Lock should be considered stale (PID -1 is not running)
        assert mgr._is_stale() is True
        # Should be able to acquire
        assert mgr.acquire() is True
        mgr.release()

    def test_checkpoint_atomic_write(self, checkpoint_mgr):
        """Checkpoint uses atomic write (temp + rename)."""
        cp = PipelineCheckpoint(date="2026-02-26", status="running")
        checkpoint_mgr.save(cp)
        # Verify no .tmp file lingering
        tmp_path = checkpoint_mgr.checkpoint_path.with_suffix(".tmp")
        assert not tmp_path.exists()
        # Verify actual file exists and is valid JSON
        data = json.loads(checkpoint_mgr.checkpoint_path.read_text())
        assert data["date"] == "2026-02-26"

    def test_cleanup_empty_dirs(self, cleanup_mgr, project_dir):
        """Cleanup handles empty directories gracefully."""
        result = cleanup_mgr.run_all()
        assert all(v >= 0 for v in result.values())

    def test_health_report_unhealthy(self, tmp_path):
        """HealthReport reflects unhealthy state correctly."""
        proj = tmp_path / "bad_proj"
        proj.mkdir()
        checker = HealthChecker(project_root=proj, min_disk_gb=0.001)
        report = checker.run_all_checks()
        # Should fail on config_files at minimum
        assert report.checks["config_files"][0] is False
        assert report.healthy is False

    def test_lock_concurrent_detection(self, lock_dir, project_dir):
        """Two lock managers for the same name detect each other."""
        mgr1 = LockFileManager(lock_name="shared", lock_dir=lock_dir, project_root=project_dir)
        mgr2 = LockFileManager(lock_name="shared", lock_dir=lock_dir, project_root=project_dir)
        assert mgr1.acquire() is True
        assert mgr2.acquire() is False
        mgr1.release()
        assert mgr2.acquire() is True
        mgr2.release()

    def test_different_lock_names_independent(self, lock_dir, project_dir):
        """Locks with different names do not interfere."""
        daily = LockFileManager(lock_name="daily", lock_dir=lock_dir, project_root=project_dir)
        weekly = LockFileManager(lock_name="weekly", lock_dir=lock_dir, project_root=project_dir)
        assert daily.acquire() is True
        assert weekly.acquire() is True
        daily.release()
        weekly.release()
