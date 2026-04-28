"""
Candidate ranking execution script.

Scores multiple candidates against a job and returns them sorted
highest-to-lowest.

One responsibility: list[candidate] + jobSkills → ranked list.

Importable and testable. No I/O, no DB, no external APIs.
"""

try:
    from execution.pipeline import matchResumeToJob
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from execution.pipeline import matchResumeToJob


def rankCandidates(
    candidates: list[dict],
    jobSkills: dict[str, list[str]],
) -> list[dict]:
    """
    Rank candidates against a job by weighted match score.

    Args:
        candidates: List of dicts, each with "name" (str) and "skills" (list[str]).
        jobSkills:  Dict with "required" and "optional" skill lists.

    Returns:
        List of result dicts sorted by score descending:
        [
            {
                "name":    str,
                "score":   int,       # 0-100 weighted score
                "details": dict       # full matchResumeToJob output
            },
            ...
        ]
    """
    results = []

    for candidate in candidates:
        match = matchResumeToJob(candidate["skills"], jobSkills)
        results.append({
            "name": candidate["name"],
            "score": match["score"],
            "details": match,
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)


# ─────────────────────────────────────────────
# TERMINAL TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    candidates = [
        {"name": "Alice",   "skills": ["python", "sql"]},
        {"name": "Bob",     "skills": ["python"]},
        {"name": "Charlie", "skills": ["python", "sql", "aws"]},
    ]

    jobSkills = {
        "required": ["python", "sql"],
        "optional": ["aws"],
    }

    ranked = rankCandidates(candidates, jobSkills)

    print("RANKED CANDIDATES:", ranked)
