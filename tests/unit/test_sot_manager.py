"""Unit tests for sot_manager.py — Phase A: SOT Safety.

Tests cover:
- CR-1: Step range validation (_validate_step_num)
- CR-2: Concurrent access locking (_SOTLock)
- CR-3: Task overlap check (cmd_update_team)
- HI-1: Future step prevention (cmd_record_output)
- MD-1: Total steps bound (cmd_advance_step)
- Existing functionality preservation (init, read, advance, record, pacs, team, status)
"""

import json
import multiprocessing
import os
import time

import pytest


def _create_gate_evidence(project_dir, step_num, pacs_score=75):
    """Helper: create verification + pACS log files for SM5 gate checks."""
    for d in ("verification-logs", "pacs-logs"):
        os.makedirs(os.path.join(project_dir, d), exist_ok=True)
    verify_path = os.path.join(
        project_dir, "verification-logs", f"step-{step_num}-verify.md"
    )
    with open(verify_path, "w") as f:
        f.write(f"# Verification — Step {step_num}\n\nAll criteria: PASS\n")
    pacs_path = os.path.join(
        project_dir, "pacs-logs", f"step-{step_num}-pacs.md"
    )
    with open(pacs_path, "w") as f:
        f.write(f"# pACS — Step {step_num}\n\npACS = {pacs_score}\n")


# ============================================================================
# CR-1: Step range validation
# ============================================================================

class TestValidateStepNum:
    """Tests for _validate_step_num helper."""

    def test_valid_step_num(self, sot_mod):
        wf = {"total_steps": 20}
        assert sot_mod._validate_step_num(wf, 1) is None
        assert sot_mod._validate_step_num(wf, 10) is None
        assert sot_mod._validate_step_num(wf, 20) is None

    def test_step_zero_rejected(self, sot_mod):
        wf = {"total_steps": 20}
        err = sot_mod._validate_step_num(wf, 0)
        assert err is not None
        assert err["valid"] is False
        assert "SM-R1" in err["error"]

    def test_negative_step_rejected(self, sot_mod):
        wf = {"total_steps": 20}
        err = sot_mod._validate_step_num(wf, -5)
        assert err is not None
        assert err["valid"] is False

    def test_step_exceeds_total_rejected(self, sot_mod):
        wf = {"total_steps": 20}
        err = sot_mod._validate_step_num(wf, 21)
        assert err is not None
        assert "exceeds total_steps" in err["error"]

    def test_step_at_total_accepted(self, sot_mod):
        wf = {"total_steps": 20}
        assert sot_mod._validate_step_num(wf, 20) is None

    def test_no_total_steps_allows_any_positive(self, sot_mod):
        wf = {}
        assert sot_mod._validate_step_num(wf, 1) is None
        assert sot_mod._validate_step_num(wf, 999) is None

    def test_string_step_rejected(self, sot_mod):
        wf = {"total_steps": 20}
        err = sot_mod._validate_step_num(wf, "3")
        assert err is not None
        assert err["valid"] is False


# ============================================================================
# SOT Init & Read
# ============================================================================

class TestCmdInit:
    """Tests for cmd_init."""

    def test_init_creates_sot(self, sot_mod, tmp_project):
        result = sot_mod.cmd_init(str(tmp_project), "Test WF", 20)
        assert result["valid"] is True
        assert os.path.exists(result["sot_path"])

    def test_init_refuses_duplicate(self, sot_mod, tmp_project_with_sot):
        result = sot_mod.cmd_init(str(tmp_project_with_sot), "Test WF", 20)
        assert result["valid"] is False
        assert "already exists" in result["error"]

    def test_init_sets_correct_structure(self, sot_mod, tmp_project):
        sot_mod.cmd_init(str(tmp_project), "My Workflow", 15)
        read_result = sot_mod.cmd_read(str(tmp_project))
        assert read_result["valid"] is True
        wf = read_result["workflow"]
        assert wf["name"] == "My Workflow"
        assert wf["current_step"] == 1
        assert wf["total_steps"] == 15
        assert wf["status"] == "in_progress"
        assert isinstance(wf["outputs"], dict)
        assert isinstance(wf["pacs"], dict)


class TestCmdRead:
    """Tests for cmd_read."""

    def test_read_valid_sot(self, sot_mod, tmp_project_with_sot):
        result = sot_mod.cmd_read(str(tmp_project_with_sot))
        assert result["valid"] is True
        assert "workflow" in result

    def test_read_nonexistent_sot(self, sot_mod, tmp_project):
        result = sot_mod.cmd_read(str(tmp_project))
        assert result["valid"] is False
        assert "not found" in result["error"]


# ============================================================================
# cmd_advance_step — CR-1 + MD-1
# ============================================================================

class TestCmdAdvanceStep:
    """Tests for cmd_advance_step including safety validations."""

    def test_advance_success(self, sot_mod, tmp_project_with_sot, create_output):
        pd = str(tmp_project_with_sot)
        create_output(pd, "research/output.md")
        sot_mod.cmd_record_output(pd, 1, "research/output.md")
        _create_gate_evidence(pd, 1)  # SM5: gate evidence required
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is True
        assert result["current_step"] == 2

    def test_advance_wrong_current_step(self, sot_mod, tmp_project_with_sot, create_output):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_advance_step(pd, 5)
        assert result["valid"] is False
        assert "SM3" in result["error"]

    def test_advance_without_output(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is False
        assert "SM4" in result["error"]

    def test_advance_zero_step_rejected(self, sot_mod, tmp_project_with_sot):
        """CR-1: step 0 should be rejected by range validation."""
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_advance_step(pd, 0)
        assert result["valid"] is False
        assert "SM-R1" in result["error"]

    def test_advance_negative_step_rejected(self, sot_mod, tmp_project_with_sot):
        """CR-1: negative step should be rejected."""
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_advance_step(pd, -1)
        assert result["valid"] is False

    def test_advance_past_total_steps(self, sot_mod, tmp_project):
        """MD-1: Cannot advance past total_steps."""
        pd = str(tmp_project)
        # Init with 3 steps
        sot_mod.cmd_init(pd, "Small WF", 3)
        # Manually set current_step to 3 and record outputs for steps 1-3
        data, sot = sot_mod._read_sot(pd)
        wf = sot_mod._extract_wf(data)
        wf["current_step"] = 3

        # Create outputs for step-1, step-2, step-3
        for i in range(1, 4):
            outpath = f"output/step-{i}.md"
            full = os.path.join(pd, outpath)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f:
                f.write("x" * 200)
            wf.setdefault("outputs", {})[f"step-{i}"] = outpath

        sot_mod._write_sot_atomic(sot, data)

        # SM5: gate evidence required for non-human step 3
        _create_gate_evidence(pd, 3)

        # Now try to advance step 3 (would go to step 4, but total is 3)
        # step_num=3 is within total_steps, and 3+1=4 is allowed (step 4 = "done" state)
        result = sot_mod.cmd_advance_step(pd, 3)
        # This should succeed (advancing to step 4 when total is 3 means workflow is done)
        assert result["valid"] is True

    def test_advance_step_exceeds_total_rejected(self, sot_mod, tmp_project_with_sot):
        """CR-1: step_num=25 when total=20 should be rejected."""
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_advance_step(pd, 25)
        assert result["valid"] is False
        assert "SM-R1" in result["error"]


# ============================================================================
# SM5: Quality Gate Evidence Guard (P1 Hallucination Prevention)
# ============================================================================

class TestSM5GateEvidence:
    """Tests for SM5 quality gate evidence checks in cmd_advance_step.

    SM5 makes it physically impossible to advance a step without quality
    gate evidence files, preventing the most critical hallucination vector.
    """

    def _setup_step(self, sot_mod, pd, step_num=1):
        """Helper: record output for step so SM3/SM4 pass, leaving SM5 as the gate."""
        outpath = f"output/step-{step_num}.md"
        full = os.path.join(pd, outpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write("x" * 200)
        sot_mod.cmd_record_output(pd, step_num, outpath)

    def test_sm5a_no_verification_log_blocked(self, sot_mod, tmp_project_with_sot):
        """SM5a: Advance blocked when verification log is missing."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is False
        assert "SM5a" in result["error"]
        assert "verification" in result["error"]

    def test_sm5b_no_pacs_log_blocked(self, sot_mod, tmp_project_with_sot):
        """SM5b: Advance blocked when pACS log is missing (verification exists)."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        # Create only verification log, no pACS
        vdir = os.path.join(pd, "verification-logs")
        os.makedirs(vdir, exist_ok=True)
        with open(os.path.join(vdir, "step-1-verify.md"), "w") as f:
            f.write("# Verification\nAll: PASS\n")
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is False
        assert "SM5b" in result["error"]
        assert "pACS" in result["error"]

    def test_sm5c_red_zone_blocked(self, sot_mod, tmp_project_with_sot):
        """SM5c: Advance blocked when pACS score is RED (< 50)."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        _create_gate_evidence(pd, 1, pacs_score=35)  # RED zone
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is False
        assert "SM5c" in result["error"]
        assert "RED" in result["error"]

    def test_sm5c_yellow_zone_passes(self, sot_mod, tmp_project_with_sot):
        """SM5c: pACS score 50-69 (YELLOW) should pass — only RED blocks."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        _create_gate_evidence(pd, 1, pacs_score=55)
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is True

    def test_sm5d_review_fail_blocked(self, sot_mod, tmp_project_with_sot):
        """SM5d: Advance blocked when review verdict is FAIL."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        _create_gate_evidence(pd, 1, pacs_score=75)
        # Create review log with FAIL verdict
        rdir = os.path.join(pd, "review-logs")
        os.makedirs(rdir, exist_ok=True)
        with open(os.path.join(rdir, "step-1-review.md"), "w") as f:
            f.write("# Review\n\nVerdict: **FAIL**\n\n- Critical issue found\n")
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is False
        assert "SM5d" in result["error"]

    def test_sm5d_review_pass_allowed(self, sot_mod, tmp_project_with_sot):
        """SM5d: Review with PASS verdict should not block."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        _create_gate_evidence(pd, 1, pacs_score=75)
        rdir = os.path.join(pd, "review-logs")
        os.makedirs(rdir, exist_ok=True)
        with open(os.path.join(rdir, "step-1-review.md"), "w") as f:
            f.write("# Review\n\nVerdict: **PASS**\n\nNo issues.\n")
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is True

    def test_sm5d_no_review_log_allowed(self, sot_mod, tmp_project_with_sot):
        """SM5d: Absent review log should not block (review is optional)."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        _create_gate_evidence(pd, 1, pacs_score=75)
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is True

    def test_sm5_human_step_exempt(self, sot_mod, tmp_project_with_sot, create_output):
        """SM5: Human steps (4, 8, 18) are exempt from gate evidence checks."""
        pd = str(tmp_project_with_sot)
        # Advance to step 4 by setting up steps 1-3 with gate evidence
        data, sot = sot_mod._read_sot(pd)
        wf = sot_mod._extract_wf(data)
        wf["current_step"] = 4
        for i in range(1, 4):
            outpath = f"output/step-{i}.md"
            full = os.path.join(pd, outpath)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f:
                f.write("x" * 200)
            wf.setdefault("outputs", {})[f"step-{i}"] = outpath
        sot_mod._write_sot_atomic(sot, data)
        # Record output for step 4 (human step — no gate evidence needed)
        create_output(pd, "output/step-4.md")
        sot_mod.cmd_record_output(pd, 4, "output/step-4.md")
        # Advance step 4 WITHOUT gate evidence — should succeed (human step)
        result = sot_mod.cmd_advance_step(pd, 4)
        assert result["valid"] is True
        assert result["current_step"] == 5

    def test_sm5_force_bypasses_gates(self, sot_mod, tmp_project_with_sot):
        """SM5: --force flag bypasses gate evidence checks with warning."""
        pd = str(tmp_project_with_sot)
        outpath = "output/step-1.md"
        full = os.path.join(pd, outpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write("x" * 200)
        sot_mod.cmd_record_output(pd, 1, outpath)
        # No gate evidence — but force=True
        result = sot_mod.cmd_advance_step(pd, 1, force=True)
        assert result["valid"] is True
        assert "warning" in result
        assert "SM5" in result["warning"]

    def test_sm5_all_gates_pass(self, sot_mod, tmp_project_with_sot):
        """SM5: All gate evidence present + GREEN pACS → advance succeeds."""
        pd = str(tmp_project_with_sot)
        outpath = "output/step-1.md"
        full = os.path.join(pd, outpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write("x" * 200)
        sot_mod.cmd_record_output(pd, 1, outpath)
        _create_gate_evidence(pd, 1, pacs_score=85)
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is True
        assert result["current_step"] == 2

    def test_sm5c_min_formula_red_blocked(self, sot_mod, tmp_project_with_sot):
        """C1-fix: SM5c must parse 'pACS = min(F, C, L) = 35' correctly as RED."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        # Create verification log
        vdir = os.path.join(pd, "verification-logs")
        os.makedirs(vdir, exist_ok=True)
        with open(os.path.join(vdir, "step-1-verify.md"), "w") as f:
            f.write("# Verification\nAll: PASS\n")
        # Create pACS log with min formula — this is the real-world format
        pdir = os.path.join(pd, "pacs-logs")
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "step-1-pacs.md"), "w") as f:
            f.write(
                "# pACS — Step 1\n\n"
                "| F | 40 |\n| C | 35 |\n| L | 45 |\n\n"
                "pACS = min(F, C, L) = 35\n"
            )
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is False
        assert "SM5c" in result["error"]
        assert "35" in result["error"]

    def test_sm5c_min_formula_green_passes(self, sot_mod, tmp_project_with_sot):
        """C1-fix: SM5c must parse 'pACS = min(F, C, L) = 75' correctly as GREEN."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        vdir = os.path.join(pd, "verification-logs")
        os.makedirs(vdir, exist_ok=True)
        with open(os.path.join(vdir, "step-1-verify.md"), "w") as f:
            f.write("# Verification\nAll: PASS\n")
        pdir = os.path.join(pd, "pacs-logs")
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "step-1-pacs.md"), "w") as f:
            f.write(
                "# pACS — Step 1\n\n"
                "| F | 80 |\n| C | 75 |\n| L | 82 |\n\n"
                "pACS = min(F, C, L) = 75\n"
            )
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is True

    def test_sm5c_unparseable_warns(self, sot_mod, tmp_project_with_sot):
        """H1-fix: Unparseable pACS log should warn but not block."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        vdir = os.path.join(pd, "verification-logs")
        os.makedirs(vdir, exist_ok=True)
        with open(os.path.join(vdir, "step-1-verify.md"), "w") as f:
            f.write("# Verification\nAll: PASS\n")
        pdir = os.path.join(pd, "pacs-logs")
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "step-1-pacs.md"), "w") as f:
            f.write("# pACS — Step 1\n\nNo score here, just text.\n")
        result = sot_mod.cmd_advance_step(pd, 1)
        assert result["valid"] is True
        assert "sm5_warnings" in result
        assert any("SM5c-warn" in w for w in result["sm5_warnings"])

    def test_sm5_force_creates_audit_log(self, sot_mod, tmp_project_with_sot):
        """H3-fix: --force should create an audit trail entry."""
        pd = str(tmp_project_with_sot)
        self._setup_step(sot_mod, pd)
        sot_mod.cmd_advance_step(pd, 1, force=True)
        audit_path = os.path.join(pd, "autopilot-logs", "sm5-force-audit.jsonl")
        assert os.path.exists(audit_path)
        with open(audit_path, "r") as f:
            content = f.read()
        assert '"step": 1' in content
        assert "SM5 gate bypass" in content


# ============================================================================
# cmd_record_output — CR-1 + HI-1
# ============================================================================

class TestCmdRecordOutput:
    """Tests for cmd_record_output including future step prevention."""

    def test_record_output_success(self, sot_mod, tmp_project_with_sot, create_output):
        pd = str(tmp_project_with_sot)
        create_output(pd, "research/out.md")
        result = sot_mod.cmd_record_output(pd, 1, "research/out.md")
        assert result["valid"] is True
        assert result["file_size"] >= 200

    def test_record_output_file_not_found(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_record_output(pd, 1, "nonexistent/file.md")
        assert result["valid"] is False
        assert "SM6" in result["error"]

    def test_record_output_file_too_small(self, sot_mod, tmp_project_with_sot, tmp_path):
        pd = str(tmp_project_with_sot)
        small_file = os.path.join(pd, "tiny.md")
        with open(small_file, "w") as f:
            f.write("x")
        result = sot_mod.cmd_record_output(pd, 1, "tiny.md")
        assert result["valid"] is False
        assert "too small" in result["error"]

    def test_record_future_step_blocked(self, sot_mod, tmp_project_with_sot, create_output):
        """HI-1: Recording output for step 5 when current_step=1 should fail."""
        pd = str(tmp_project_with_sot)
        create_output(pd, "future/out.md")
        result = sot_mod.cmd_record_output(pd, 5, "future/out.md")
        assert result["valid"] is False
        assert "SM-R3" in result["error"]
        assert "Future step" in result["error"]

    def test_record_current_step_allowed(self, sot_mod, tmp_project_with_sot, create_output):
        """Recording output for step 1 when current_step=1 should succeed."""
        pd = str(tmp_project_with_sot)
        create_output(pd, "output/step1.md")
        result = sot_mod.cmd_record_output(pd, 1, "output/step1.md")
        assert result["valid"] is True

    def test_record_zero_step_rejected(self, sot_mod, tmp_project_with_sot, create_output):
        """CR-1: step 0 should be rejected."""
        pd = str(tmp_project_with_sot)
        create_output(pd, "output/bad.md")
        result = sot_mod.cmd_record_output(pd, 0, "output/bad.md")
        assert result["valid"] is False
        assert "SM-R1" in result["error"]


# ============================================================================
# cmd_update_pacs — CR-1
# ============================================================================

class TestCmdUpdatePacs:
    """Tests for cmd_update_pacs including step validation."""

    def test_update_pacs_success(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_pacs(pd, 1, 85, 78, 80)
        assert result["valid"] is True
        assert result["pacs_score"] == 78
        assert result["weak_dimension"] == "C"
        assert result["zone"] == "GREEN"

    def test_pacs_red_zone(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_pacs(pd, 1, 45, 80, 70)
        assert result["zone"] == "RED"
        assert result["pacs_score"] == 45

    def test_pacs_yellow_zone(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_pacs(pd, 1, 60, 80, 65)
        assert result["zone"] == "YELLOW"

    def test_pacs_invalid_range(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_pacs(pd, 1, 105, 80, 70)
        assert result["valid"] is False
        assert "SM10" in result["error"]

    def test_pacs_negative_score(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_pacs(pd, 1, -5, 80, 70)
        assert result["valid"] is False

    def test_pacs_zero_step_rejected(self, sot_mod, tmp_project_with_sot):
        """CR-1: step 0 should be rejected."""
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_pacs(pd, 0, 85, 78, 80)
        assert result["valid"] is False
        assert "SM-R1" in result["error"]

    def test_pacs_exceeds_total_steps(self, sot_mod, tmp_project_with_sot):
        """CR-1: step 25 when total=20 should be rejected."""
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_pacs(pd, 25, 85, 78, 80)
        assert result["valid"] is False
        assert "SM-R1" in result["error"]

    def test_pacs_history_recorded(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        sot_mod.cmd_update_pacs(pd, 1, 85, 78, 80)
        read = sot_mod.cmd_read(pd)
        history = read["workflow"]["pacs"]["history"]
        assert "step-1" in history
        assert history["step-1"]["score"] == 78


# ============================================================================
# cmd_update_team — CR-3 (task overlap)
# ============================================================================

class TestCmdUpdateTeam:
    """Tests for cmd_update_team including task overlap check."""

    def test_update_team_success(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        team_json = json.dumps({
            "name": "test-team",
            "status": "partial",
            "tasks_completed": ["t1"],
            "tasks_pending": ["t2", "t3"],
            "completed_summaries": {"t1": {"summary": "done"}},
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"] is True
        assert result["tasks_completed_count"] == 1
        assert result["tasks_pending_count"] == 2

    def test_task_overlap_blocked(self, sot_mod, tmp_project_with_sot):
        """CR-3: Same task in completed AND pending should fail."""
        pd = str(tmp_project_with_sot)
        team_json = json.dumps({
            "name": "test-team",
            "status": "partial",
            "tasks_completed": ["t1", "t2"],
            "tasks_pending": ["t2", "t3"],
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"] is False
        assert "SM-R4" in result["error"]
        assert "t2" in result["error"]

    def test_task_overlap_multiple_items(self, sot_mod, tmp_project_with_sot):
        """CR-3: Multiple overlapping tasks should all be reported."""
        pd = str(tmp_project_with_sot)
        team_json = json.dumps({
            "name": "test-team",
            "status": "partial",
            "tasks_completed": ["t1", "t2", "t3"],
            "tasks_pending": ["t2", "t3"],
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"] is False
        assert "SM-R4" in result["error"]

    def test_no_overlap_passes(self, sot_mod, tmp_project_with_sot):
        """Disjoint sets should pass."""
        pd = str(tmp_project_with_sot)
        team_json = json.dumps({
            "name": "clean-team",
            "status": "partial",
            "tasks_completed": ["t1"],
            "tasks_pending": ["t2"],
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"] is True

    def test_invalid_team_json(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_team(pd, "not json")
        assert result["valid"] is False
        assert "Invalid JSON" in result["error"]

    def test_missing_team_name(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_team(pd, json.dumps({"status": "partial"}))
        assert result["valid"] is False
        assert "SM8" in result["error"]

    def test_invalid_team_status(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_update_team(pd, json.dumps({
            "name": "team", "status": "invalid"
        }))
        assert result["valid"] is False

    def test_all_completed_moves_to_history(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        team_json = json.dumps({
            "name": "done-team",
            "status": "all_completed",
            "tasks_completed": ["t1", "t2"],
            "tasks_pending": [],
            "completed_summaries": {"t1": {}, "t2": {}},
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"] is True
        read = sot_mod.cmd_read(pd)
        wf = read["workflow"]
        assert "completed_teams" in wf
        assert len(wf["completed_teams"]) == 1

    def test_completed_summaries_key_validation(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        team_json = json.dumps({
            "name": "team",
            "status": "partial",
            "tasks_completed": ["t1"],
            "tasks_pending": ["t2"],
            "completed_summaries": {"t3": {"summary": "orphan"}},
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"] is False
        assert "SM9b" in result["error"]


# ============================================================================
# cmd_set_status
# ============================================================================

class TestCmdSetStatus:
    """Tests for cmd_set_status."""

    def test_set_status_success(self, sot_mod, tmp_project_with_sot):
        """Non-completion status changes always succeed."""
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_set_status(pd, "paused")
        assert result["valid"] is True
        assert result["new_status"] == "paused"

    def test_set_status_completed_at_final_step(self, sot_mod, tmp_project_with_sot):
        """SM-ST1: 'completed' succeeds when current_step >= total_steps."""
        pd = str(tmp_project_with_sot)
        human_steps = {4, 8, 18}
        # Create dummy output files and advance step by step to step 20
        for step in range(1, 20):
            out_path = os.path.join(pd, f"research/step-{step}.md")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w") as f:
                f.write("x" * 200)
            sot_mod.cmd_record_output(pd, step, f"research/step-{step}.md")
            if step not in human_steps:
                _create_gate_evidence(pd, step, pacs_score=75)
            res = sot_mod.cmd_advance_step(pd, step)
            assert res["valid"], f"Advance step {step} failed: {res}"
        result = sot_mod.cmd_set_status(pd, "completed")
        assert result["valid"] is True
        assert result["new_status"] == "completed"

    def test_set_status_completed_rejected_early(self, sot_mod, tmp_project_with_sot):
        """SM-ST1: 'completed' rejected when current_step < total_steps."""
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_set_status(pd, "completed")
        assert result["valid"] is False
        assert "SM-ST1" in result["error"]
        assert "current_step=1" in result["error"]

    def test_set_invalid_status(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_set_status(pd, "invalid_state")
        assert result["valid"] is False


# ============================================================================
# CR-2: Concurrent access locking
# ============================================================================

def _concurrent_team_update(project_dir, team_name, task_name):
    """Worker function for concurrent access test."""
    import importlib.util
    import sys
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    spec = importlib.util.spec_from_file_location(
        "sot_manager", os.path.join(scripts_dir, "sot_manager.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    team_json = json.dumps({
        "name": team_name,
        "status": "partial",
        "tasks_completed": [task_name],
        "tasks_pending": [],
        "completed_summaries": {task_name: {"result": f"done by {task_name}"}},
    })
    result = mod.cmd_update_team(project_dir, team_json)
    return result


class TestConcurrentAccess:
    """CR-2: Tests that fcntl locking prevents data corruption."""

    def test_sot_lock_context_manager(self, sot_mod, tmp_project_with_sot):
        """Verify _SOTLock context manager works."""
        sot_path = sot_mod._sot_path(str(tmp_project_with_sot))
        with sot_mod._SOTLock(sot_path, exclusive=True):
            # Should be able to read inside lock
            data, _ = sot_mod._read_sot_unlocked(str(tmp_project_with_sot))
            assert data is not None

    def test_sot_lock_creates_lock_file(self, sot_mod, tmp_project_with_sot):
        """Verify lock file is created."""
        sot_path = sot_mod._sot_path(str(tmp_project_with_sot))
        lock_path = sot_path + ".lock"
        with sot_mod._SOTLock(sot_path, exclusive=True):
            assert os.path.exists(lock_path)

    def test_sequential_updates_preserve_data(self, sot_mod, tmp_project_with_sot):
        """Multiple sequential updates should all succeed."""
        pd = str(tmp_project_with_sot)
        for i in range(5):
            team_json = json.dumps({
                "name": "seq-team",
                "status": "partial",
                "tasks_completed": [f"t{j}" for j in range(i + 1)],
                "tasks_pending": [f"t{j}" for j in range(i + 1, 5)],
            })
            result = sot_mod.cmd_update_team(pd, team_json)
            assert result["valid"] is True


# ============================================================================
# cmd_set_autopilot — SM-AP1
# ============================================================================

class TestCmdSetAutopilot:
    """Tests for cmd_set_autopilot."""

    def test_set_autopilot_true(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_set_autopilot(pd, "true")
        assert result["valid"] is True
        assert result["enabled"] is True
        # Verify persisted
        read = sot_mod.cmd_read(pd)
        assert read["workflow"]["autopilot"]["enabled"] is True

    def test_set_autopilot_false(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        sot_mod.cmd_set_autopilot(pd, "true")
        result = sot_mod.cmd_set_autopilot(pd, "false")
        assert result["valid"] is True
        assert result["enabled"] is False
        assert result["previous"] is True

    def test_set_autopilot_invalid_value(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        result = sot_mod.cmd_set_autopilot(pd, "yes")
        assert result["valid"] is False
        assert "SM-AP1" in result["error"]

    def test_set_autopilot_creates_section(self, sot_mod, tmp_project):
        """If autopilot section doesn't exist, it should be auto-created."""
        pd = str(tmp_project)
        sot_mod.cmd_init(pd, "Test", 5)
        # Remove autopilot section manually
        import yaml
        sot_path = sot_mod._sot_path(pd)
        with open(sot_path, "r") as f:
            data = yaml.safe_load(f)
        del data["workflow"]["autopilot"]
        with open(sot_path, "w") as f:
            yaml.dump(data, f)
        # Now set autopilot
        result = sot_mod.cmd_set_autopilot(pd, "true")
        assert result["valid"] is True
        assert result["enabled"] is True

    def test_set_autopilot_toggle(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        sot_mod.cmd_set_autopilot(pd, "true")
        sot_mod.cmd_set_autopilot(pd, "false")
        result = sot_mod.cmd_set_autopilot(pd, "true")
        assert result["valid"] is True
        assert result["previous"] is False
        assert result["enabled"] is True

    def test_set_autopilot_no_sot(self, sot_mod, tmp_project):
        pd = str(tmp_project)
        result = sot_mod.cmd_set_autopilot(pd, "true")
        assert result["valid"] is False


# ============================================================================
# cmd_add_auto_approved — SM-AA1~AA4
# ============================================================================

class TestCmdAddAutoApproved:
    """Tests for cmd_add_auto_approved."""

    def _enable_autopilot(self, sot_mod, pd):
        sot_mod.cmd_set_autopilot(pd, "true")

    def test_approve_human_step(self, sot_mod, tmp_project_with_sot):
        """SM-AA1: Human step 4 should be accepted."""
        pd = str(tmp_project_with_sot)
        self._enable_autopilot(sot_mod, pd)
        # Set current_step to 4 so step 4 is not future
        import yaml
        sot_path = sot_mod._sot_path(pd)
        with open(sot_path, "r") as f:
            data = yaml.safe_load(f)
        data["workflow"]["current_step"] = 4
        with open(sot_path, "w") as f:
            yaml.dump(data, f)
        result = sot_mod.cmd_add_auto_approved(pd, 4)
        assert result["valid"] is True
        assert result["action"] == "auto_approved"
        assert 4 in result["auto_approved_steps"]

    def test_reject_non_human_step(self, sot_mod, tmp_project_with_sot):
        """SM-AA1: Non-human step 5 should be rejected."""
        pd = str(tmp_project_with_sot)
        self._enable_autopilot(sot_mod, pd)
        result = sot_mod.cmd_add_auto_approved(pd, 5)
        assert result["valid"] is False
        assert "SM-AA1" in result["error"]

    def test_reject_when_autopilot_off(self, sot_mod, tmp_project_with_sot):
        """SM-AA2: Cannot add when autopilot is disabled."""
        pd = str(tmp_project_with_sot)
        # Autopilot is off by default after init
        result = sot_mod.cmd_add_auto_approved(pd, 4)
        assert result["valid"] is False
        assert "SM-AA2" in result["error"]

    def test_idempotent(self, sot_mod, tmp_project_with_sot):
        """SM-AA3: Adding same step twice should succeed (idempotent)."""
        pd = str(tmp_project_with_sot)
        self._enable_autopilot(sot_mod, pd)
        import yaml
        sot_path = sot_mod._sot_path(pd)
        with open(sot_path, "r") as f:
            data = yaml.safe_load(f)
        data["workflow"]["current_step"] = 8
        with open(sot_path, "w") as f:
            yaml.dump(data, f)
        sot_mod.cmd_add_auto_approved(pd, 8)
        result = sot_mod.cmd_add_auto_approved(pd, 8)
        assert result["valid"] is True
        assert result["action"] == "already_approved"

    def test_reject_future_step(self, sot_mod, tmp_project_with_sot):
        """SM-AA4: Cannot approve future steps."""
        pd = str(tmp_project_with_sot)
        self._enable_autopilot(sot_mod, pd)
        # current_step is 1, step 18 is future
        result = sot_mod.cmd_add_auto_approved(pd, 18)
        assert result["valid"] is False
        assert "SM-AA4" in result["error"]

    def test_sorted_output(self, sot_mod, tmp_project_with_sot):
        """auto_approved_steps should be sorted after insertion."""
        pd = str(tmp_project_with_sot)
        self._enable_autopilot(sot_mod, pd)
        import yaml
        sot_path = sot_mod._sot_path(pd)
        with open(sot_path, "r") as f:
            data = yaml.safe_load(f)
        data["workflow"]["current_step"] = 20
        with open(sot_path, "w") as f:
            yaml.dump(data, f)
        sot_mod.cmd_add_auto_approved(pd, 18)
        sot_mod.cmd_add_auto_approved(pd, 4)
        result = sot_mod.cmd_add_auto_approved(pd, 8)
        read = sot_mod.cmd_read(pd)
        aas = read["workflow"]["autopilot"]["auto_approved_steps"]
        assert aas == sorted(aas)


# ============================================================================
# _validate_schema — SM-AP1~AP4
# ============================================================================

class TestValidateSchemaAutopilot:
    """Tests for autopilot schema validation in _validate_schema."""

    def test_valid_autopilot_section(self, sot_mod):
        wf = {"autopilot": {"enabled": True, "auto_approved_steps": [4, 8]}}
        warnings = sot_mod._validate_schema(wf)
        ap_warnings = [w for w in warnings if "AP" in w]
        assert len(ap_warnings) == 0

    def test_autopilot_not_dict(self, sot_mod):
        wf = {"autopilot": "yes"}
        warnings = sot_mod._validate_schema(wf)
        assert any("SM-AP1" in w for w in warnings)

    def test_enabled_not_bool(self, sot_mod):
        wf = {"autopilot": {"enabled": "true", "auto_approved_steps": []}}
        warnings = sot_mod._validate_schema(wf)
        assert any("SM-AP2" in w for w in warnings)

    def test_auto_approved_not_list(self, sot_mod):
        wf = {"autopilot": {"enabled": True, "auto_approved_steps": "4,8"}}
        warnings = sot_mod._validate_schema(wf)
        assert any("SM-AP3" in w for w in warnings)

    def test_auto_approved_non_int(self, sot_mod):
        wf = {"autopilot": {"enabled": True, "auto_approved_steps": ["4"]}}
        warnings = sot_mod._validate_schema(wf)
        assert any("SM-AP3" in w and "non-int" in w for w in warnings)

    def test_auto_approved_non_human_step(self, sot_mod):
        wf = {"autopilot": {"enabled": True, "auto_approved_steps": [5]}}
        warnings = sot_mod._validate_schema(wf)
        assert any("SM-AP4" in w for w in warnings)

    def test_no_autopilot_section_no_warning(self, sot_mod):
        wf = {"current_step": 1, "outputs": {}}
        warnings = sot_mod._validate_schema(wf)
        ap_warnings = [w for w in warnings if "AP" in w]
        assert len(ap_warnings) == 0

    def test_init_includes_autopilot_section(self, sot_mod, tmp_project):
        """cmd_init should create SOT with autopilot section."""
        pd = str(tmp_project)
        sot_mod.cmd_init(pd, "Test", 10)
        read = sot_mod.cmd_read(pd)
        wf = read["workflow"]
        assert "autopilot" in wf
        assert wf["autopilot"]["enabled"] is False
        assert wf["autopilot"]["auto_approved_steps"] == []
        # Change 8: auto_approved_details must be in initial schema
        assert "auto_approved_details" in wf["autopilot"]
        assert wf["autopilot"]["auto_approved_details"] == {}


# ============================================================================
# Change 7: Activation Decision Log
# ============================================================================

class TestActivationDecisionLog:
    """Tests for activation decision log in cmd_set_autopilot."""

    def test_activation_log_created(self, sot_mod, tmp_project_with_sot):
        """First enable → activation log created with workflow info."""
        pd = str(tmp_project_with_sot)
        sot_mod.cmd_set_autopilot(pd, "true")
        log_path = os.path.join(pd, "autopilot-logs", "activation-decision.md")
        assert os.path.exists(log_path)
        with open(log_path, "r") as f:
            content = f.read()
        assert "Autopilot Activation" in content
        assert "Test Workflow" in content

    def test_activation_log_preserved_on_reenable(self, sot_mod, tmp_project_with_sot):
        """Re-enable → original log preserved (not overwritten)."""
        pd = str(tmp_project_with_sot)
        sot_mod.cmd_set_autopilot(pd, "true")
        log_path = os.path.join(pd, "autopilot-logs", "activation-decision.md")
        with open(log_path, "r") as f:
            original = f.read()
        sot_mod.cmd_set_autopilot(pd, "false")
        sot_mod.cmd_set_autopilot(pd, "true")
        with open(log_path, "r") as f:
            after = f.read()
        assert original == after

    def test_no_activation_log_on_disable(self, sot_mod, tmp_project_with_sot):
        """Disable only → no activation log."""
        pd = str(tmp_project_with_sot)
        sot_mod.cmd_set_autopilot(pd, "false")
        log_path = os.path.join(pd, "autopilot-logs", "activation-decision.md")
        assert not os.path.exists(log_path)


# ============================================================================
# Change 8: Auto-Approved Details Audit Trail
# ============================================================================

class TestAutoApprovedDetails:
    """Tests for auto_approved_details in cmd_add_auto_approved."""

    def test_details_recorded(self, sot_mod, tmp_project_with_sot):
        """Approval records timestamp and decision_log path."""
        import yaml
        pd = str(tmp_project_with_sot)
        sot_mod.cmd_set_autopilot(pd, "true")
        # Set current_step to 8 so approval is valid
        sot_path = sot_mod._sot_path(pd)
        with open(sot_path, "r") as f:
            data = yaml.safe_load(f)
        data["workflow"]["current_step"] = 8
        with open(sot_path, "w") as f:
            yaml.dump(data, f)
        sot_mod.cmd_add_auto_approved(pd, 8)
        read = sot_mod.cmd_read(pd)
        details = read["workflow"]["autopilot"]["auto_approved_details"]
        assert "8" in details
        assert "timestamp" in details["8"]

    def test_details_empty_in_initial_schema(self, sot_mod, tmp_project):
        """cmd_init creates empty auto_approved_details."""
        pd = str(tmp_project)
        sot_mod.cmd_init(pd, "Test", 20)
        read = sot_mod.cmd_read(pd)
        assert read["workflow"]["autopilot"]["auto_approved_details"] == {}
