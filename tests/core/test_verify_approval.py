"""
Unit tests for the explicit approval-state enforcement in verify_approval.

These tests cover the three behaviors added to verify_approval:
  1. approval missing "approved" key → (False, ...)
  2. approval["approved"] is False → (False, "Approval not granted")
  3. approval["approved"] is True with a valid, matching artifact → (True, "OK")

Note: create_approval() does not emit an "approved" key, so artifacts are
constructed manually to keep these tests self-contained and deterministic.
"""

from jobflow.app.core.approval_artifact import compute_plan_hash, verify_approval


PLAN = {"pipeline_name": "job_discovery", "steps": ["step1"], "risks": [], "assumptions": []}


def _base_approval(approved: bool) -> dict:
    """Return a fully-populated, hash-correct approval artifact."""
    return {
        "plan_hash": compute_plan_hash(PLAN),
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00",
        "approved": approved,
    }


def test_verify_approval_missing_approved_key():
    """Approval without the 'approved' key should be rejected."""
    approval = {
        "plan_hash": compute_plan_hash(PLAN),
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00",
        # "approved" intentionally omitted
    }

    valid, reason = verify_approval(PLAN, approval)

    assert valid is False
    assert "missing required keys" in reason
    assert "approved" in reason


def test_verify_approval_approved_false_returns_not_granted():
    """Approval with approved=False should return (False, 'Approval not granted')."""
    approval = _base_approval(approved=False)

    valid, reason = verify_approval(PLAN, approval)

    assert valid is False
    assert reason == "Approval not granted"


def test_verify_approval_approved_true_valid_artifact_returns_ok():
    """Approval with approved=True and a valid, matching artifact should return (True, 'OK')."""
    approval = _base_approval(approved=True)

    valid, reason = verify_approval(PLAN, approval)

    assert valid is True
    assert reason == "OK"
