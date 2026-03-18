"""
Approval Policy - Policy-based auto-approval rules.
"""

from typing import Set


ALLOWED_PIPELINES: Set[str] = {
    "job_discovery",
}

FORBIDDEN_KEYWORDS: Set[str] = {
    "write",
    "delete",
    "update",
    "send",
    "apply",
    "http",
    "api",
}


def evaluate_policy(plan: dict) -> bool:
    if not isinstance(plan, dict):
        return False

    pipeline_name = plan.get("pipeline_name", "")
    if not _is_pipeline_allowed(pipeline_name):
        return False

    risks = plan.get("risks", [])
    if not _are_risks_acceptable(risks):
        return False

    steps = plan.get("steps", [])
    if not _are_steps_safe(steps):
        return False

    return True


def _is_pipeline_allowed(pipeline_name: str) -> bool:
    if not isinstance(pipeline_name, str):
        return False

    if not pipeline_name:
        return False

    return pipeline_name in ALLOWED_PIPELINES


def _are_risks_acceptable(risks: list) -> bool:
    if not isinstance(risks, list):
        return False

    return len(risks) == 0


def _are_steps_safe(steps: list) -> bool:
    if not isinstance(steps, list):
        return False

    for step in steps:
        if isinstance(step, dict):
            action = step.get("action", "")
            step_text = str(action).lower()
        elif isinstance(step, str):
            step_text = step.lower()
        else:
            return False

        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in step_text:
                return False

    return True


def get_policy_failure_reason(plan: dict) -> str:
    if not isinstance(plan, dict):
        return "Plan is not a valid dictionary"

    reasons = []

    pipeline_name = plan.get("pipeline_name", "")
    if not _is_pipeline_allowed(pipeline_name):
        reasons.append(
            f"Pipeline '{pipeline_name}' is not in the allowlist. "
            f"Allowed pipelines: {sorted(ALLOWED_PIPELINES)}"
        )

    risks = plan.get("risks", [])
    if not _are_risks_acceptable(risks):
        reasons.append(
            f"Plan has {len(risks)} identified risk(s). "
            f"Auto-approval requires zero risks. Risks: {risks}"
        )

    steps = plan.get("steps", [])
    if not _are_steps_safe(steps):
        reasons.append(
            f"Plan steps contain forbidden keywords. "
            f"Steps must not contain: {sorted(FORBIDDEN_KEYWORDS)}"
        )

    if not reasons:
        return "Plan passed all policies (unexpected - should not be called)"

    return " | ".join(reasons)
