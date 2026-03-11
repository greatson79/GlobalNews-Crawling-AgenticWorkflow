"""Integration tests — Full SOT Lifecycle Simulation.

Tests simulate realistic workflow execution sequences:
- Full 5-step lifecycle: init → record → advance → pacs → team
- Error recovery paths
- Multi-step progression
- Team lifecycle (create → partial → all_completed)
"""

import json
import os

import pytest


def _create_gate_evidence(project_dir, step_num, pacs_score=75):
    """Helper: create verification + pACS log files for SM5 gate checks."""
    for d in ("verification-logs", "pacs-logs"):
        os.makedirs(os.path.join(project_dir, d), exist_ok=True)
    with open(os.path.join(project_dir, "verification-logs", f"step-{step_num}-verify.md"), "w") as f:
        f.write(f"# Verification — Step {step_num}\n\nAll criteria: PASS\n")
    with open(os.path.join(project_dir, "pacs-logs", f"step-{step_num}-pacs.md"), "w") as f:
        f.write(f"# pACS — Step {step_num}\n\npACS = {pacs_score}\n")


# ============================================================================
# Full Lifecycle
# ============================================================================

class TestFullLifecycle:
    """Simulate a realistic multi-step workflow execution."""

    def test_three_step_workflow(self, sot_mod, tmp_project, create_output):
        """Run through 3 steps with all quality gates."""
        pd = str(tmp_project)

        # Init
        result = sot_mod.cmd_init(pd, "Integration Test WF", 5)
        assert result["valid"]

        for step in range(1, 4):
            # Verify current step
            read = sot_mod.cmd_read(pd)
            assert read["workflow"]["current_step"] == step

            # Create output
            outpath = f"output/step-{step}.md"
            create_output(pd, outpath)

            # Record output
            result = sot_mod.cmd_record_output(pd, step, outpath)
            assert result["valid"], f"Record step {step} failed: {result}"

            # Update pACS
            result = sot_mod.cmd_update_pacs(pd, step, 80, 75, 82)
            assert result["valid"]
            assert result["zone"] == "GREEN"

            # SM5: Create gate evidence files
            _create_gate_evidence(pd, step, pacs_score=75)

            # Advance
            result = sot_mod.cmd_advance_step(pd, step)
            assert result["valid"], f"Advance step {step} failed: {result}"
            assert result["current_step"] == step + 1

        # Verify final state
        read = sot_mod.cmd_read(pd)
        wf = read["workflow"]
        assert wf["current_step"] == 4
        assert "step-1" in wf["outputs"]
        assert "step-2" in wf["outputs"]
        assert "step-3" in wf["outputs"]
        assert "step-1" in wf["pacs"]["history"]
        assert "step-3" in wf["pacs"]["history"]

    def test_cannot_skip_steps(self, sot_mod, tmp_project, create_output):
        """Verify steps must be executed in order (no skipping)."""
        pd = str(tmp_project)
        sot_mod.cmd_init(pd, "No Skip WF", 10)

        # Try to record output for step 3 when current is 1
        create_output(pd, "output/skip.md")
        result = sot_mod.cmd_record_output(pd, 3, "output/skip.md")
        assert result["valid"] is False  # SM-R3: future step

        # Try to advance step 3 when current is 1
        result = sot_mod.cmd_advance_step(pd, 3)
        assert result["valid"] is False  # SM3: wrong current step


# ============================================================================
# Team Lifecycle
# ============================================================================

class TestTeamLifecycle:
    """Simulate a (team) step with multiple teammates."""

    def test_team_partial_to_complete(self, sot_mod, tmp_project_with_sot):
        """Team starts partial, members report in, then all_completed."""
        pd = str(tmp_project_with_sot)

        # Create team with 3 tasks
        team_json = json.dumps({
            "name": "adapter-team",
            "status": "partial",
            "tasks_completed": [],
            "tasks_pending": ["kr-major", "kr-tech", "english"],
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"]

        # First teammate completes
        team_json = json.dumps({
            "name": "adapter-team",
            "status": "partial",
            "tasks_completed": ["kr-major"],
            "tasks_pending": ["kr-tech", "english"],
            "completed_summaries": {"kr-major": {"adapters": 11}},
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"]

        # Second teammate completes
        team_json = json.dumps({
            "name": "adapter-team",
            "status": "partial",
            "tasks_completed": ["kr-major", "kr-tech"],
            "tasks_pending": ["english"],
            "completed_summaries": {
                "kr-major": {"adapters": 11},
                "kr-tech": {"adapters": 8},
            },
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"]

        # Third teammate completes — team done
        team_json = json.dumps({
            "name": "adapter-team",
            "status": "all_completed",
            "tasks_completed": ["kr-major", "kr-tech", "english"],
            "tasks_pending": [],
            "completed_summaries": {
                "kr-major": {"adapters": 11},
                "kr-tech": {"adapters": 8},
                "english": {"adapters": 12},
            },
        })
        result = sot_mod.cmd_update_team(pd, team_json)
        assert result["valid"]

        # Verify team moved to completed_teams
        read = sot_mod.cmd_read(pd)
        wf = read["workflow"]
        assert len(wf["completed_teams"]) == 1
        assert wf["completed_teams"][0]["name"] == "adapter-team"

    def test_team_overlap_detected_mid_lifecycle(self, sot_mod, tmp_project_with_sot):
        """Task overlap should be caught even during a realistic update."""
        pd = str(tmp_project_with_sot)

        # Initial team setup
        sot_mod.cmd_update_team(pd, json.dumps({
            "name": "buggy-team",
            "status": "partial",
            "tasks_completed": [],
            "tasks_pending": ["t1", "t2"],
        }))

        # Buggy update: t1 appears in both lists
        result = sot_mod.cmd_update_team(pd, json.dumps({
            "name": "buggy-team",
            "status": "partial",
            "tasks_completed": ["t1"],
            "tasks_pending": ["t1", "t2"],  # BUG: t1 still in pending
        }))
        assert result["valid"] is False
        assert "SM-R4" in result["error"]


# ============================================================================
# pACS History Progression
# ============================================================================

class TestPacsHistory:
    """Test pACS score history across multiple steps."""

    def test_history_accumulates(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)

        # Score 3 steps
        sot_mod.cmd_update_pacs(pd, 1, 80, 75, 85)
        sot_mod.cmd_update_pacs(pd, 2, 90, 85, 80)
        sot_mod.cmd_update_pacs(pd, 3, 70, 65, 75)

        read = sot_mod.cmd_read(pd)
        history = read["workflow"]["pacs"]["history"]

        assert len(history) == 3
        assert history["step-1"]["score"] == 75
        assert history["step-2"]["score"] == 80
        assert history["step-3"]["score"] == 65
        assert history["step-3"]["weak"] == "C"

    def test_current_score_reflects_latest(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)

        sot_mod.cmd_update_pacs(pd, 1, 80, 75, 85)
        sot_mod.cmd_update_pacs(pd, 2, 60, 90, 55)

        read = sot_mod.cmd_read(pd)
        pacs = read["workflow"]["pacs"]

        # Current should reflect step 2 (last update)
        assert pacs["current_step_score"] == 55
        assert pacs["weak_dimension"] == "L"


# ============================================================================
# Error Recovery
# ============================================================================

class TestErrorRecovery:
    """Test that errors leave SOT in a consistent state."""

    def test_failed_advance_preserves_state(self, sot_mod, tmp_project_with_sot):
        """A failed advance should not change current_step."""
        pd = str(tmp_project_with_sot)

        # Try to advance without output (should fail)
        sot_mod.cmd_advance_step(pd, 1)

        # State should be unchanged
        read = sot_mod.cmd_read(pd)
        assert read["workflow"]["current_step"] == 1

    def test_failed_record_preserves_state(self, sot_mod, tmp_project_with_sot):
        """A failed record should not pollute outputs."""
        pd = str(tmp_project_with_sot)

        # Try to record nonexistent file
        sot_mod.cmd_record_output(pd, 1, "nonexistent.md")

        # Outputs should be empty
        read = sot_mod.cmd_read(pd)
        assert read["workflow"]["outputs"] == {}

    def test_status_transition(self, sot_mod, tmp_project_with_sot):
        """Status transitions should work correctly.

        SM-ST1: 'completed' requires current_step >= total_steps.
        Test paused ↔ in_progress first, then advance to final step for completed.
        """
        pd = str(tmp_project_with_sot)

        assert sot_mod.cmd_read(pd)["workflow"]["status"] == "in_progress"

        sot_mod.cmd_set_status(pd, "paused")
        assert sot_mod.cmd_read(pd)["workflow"]["status"] == "paused"

        sot_mod.cmd_set_status(pd, "in_progress")
        assert sot_mod.cmd_read(pd)["workflow"]["status"] == "in_progress"

        # SM-ST1: Must advance to final step before setting "completed"
        total = sot_mod.cmd_read(pd)["workflow"]["total_steps"]
        human_steps = {4, 8, 18}
        for step in range(1, total + 1):
            out_path = os.path.join(pd, f"step-{step}-output.md")
            with open(out_path, "w") as f:
                f.write(f"# Step {step} output\n" + "x" * 200)
            sot_mod.cmd_record_output(pd, step, out_path)
            if step not in human_steps:
                _create_gate_evidence(pd, step, pacs_score=75)
            sot_mod.cmd_advance_step(pd, step)

        sot_mod.cmd_set_status(pd, "completed")
        assert sot_mod.cmd_read(pd)["workflow"]["status"] == "completed"


# ============================================================================
# Schema Validation
# ============================================================================

class TestSchemaWarnings:
    """Test that schema validation catches issues."""

    def test_clean_sot_no_warnings(self, sot_mod, tmp_project_with_sot):
        pd = str(tmp_project_with_sot)
        read = sot_mod.cmd_read(pd)
        assert read["schema_warnings"] == []
