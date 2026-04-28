"""
Job matching execution script.

Scores a candidate's skills against a job's required skills.

One responsibility: compare two skill lists → structured match result.

Importable and testable. No I/O, no DB, no external APIs.
"""


def match_resume_to_job(
    candidate_skills: list[str],
    job_skills: list[str],
) -> dict:
    """
    Score a candidate against a job based on skill overlap.

    Matching is case-insensitive and normalises whitespace so that
    "Power BI" and "power bi" are treated as the same skill.

    Args:
        candidate_skills: Skills extracted from the candidate's resume.
        job_skills:        Skills required by the job posting.

    Returns:
        {
            "score":          int    # 0-100, percentage of job skills matched
            "matched_skills": list   # skills present in both lists
            "missing_skills": list   # job skills not found in candidate
        }
    """
    if not job_skills:
        return {"score": 0, "matched_skills": [], "missing_skills": []}

    candidate_set = {_normalize(s) for s in candidate_skills}

    matched = []
    missing = []

    for skill in job_skills:
        if _normalize(skill) in candidate_set:
            matched.append(skill)
        else:
            missing.append(skill)

    score = round((len(matched) / len(job_skills)) * 100)

    return {
        "score": score,
        "matched_skills": matched,
        "missing_skills": missing,
    }


def _normalize(skill: str) -> str:
    """Lowercase and collapse whitespace for comparison."""
    return " ".join(skill.lower().split())
