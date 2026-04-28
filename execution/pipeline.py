"""
Resume Intelligence + Job Matching Pipeline

Self-contained script that ties together:
  - text normalisation
  - name / email extraction
  - skill detection
  - job matching

Run from terminal to verify the full pipeline:
    python execution/pipeline.py
"""

import re


# ─────────────────────────────────────────────
# 1. TEXT NORMALISATION
# ─────────────────────────────────────────────

def normalizeText(text: str) -> str:
    return (
        text.lower()
        .replace("\n", " ")
        .replace("\x00", "")
        .strip()
    )


# ─────────────────────────────────────────────
# 2. EMAIL EXTRACTION
# ─────────────────────────────────────────────

def extractEmail(text: str) -> str | None:
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+", text)
    return match.group(0) if match else None


# ─────────────────────────────────────────────
# 3. NAME EXTRACTION
# ─────────────────────────────────────────────

def extractName(text: str) -> str | None:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:5]:
        if (
            line.isalpha() or " " in line
        ) and "@" not in line and len(line.split()) <= 4:
            return line
    return None


# ─────────────────────────────────────────────
# 4. SKILL DETECTION
# ─────────────────────────────────────────────

SKILLS = [
    "power bi", "sql", "python", "aws", "docker", "kubernetes",
    "tableau", "ssis", "ssrs", "etl", "data warehouse",
    "snowflake", "git", "excel", "dax", "jira",
    "postgresql", "power query", "data lake", "business intelligence",
]

# Aliases that resolve to a canonical skill in SKILLS.
# If an alias is found in text the canonical skill is added to results.
SKILL_SYNONYMS: dict[str, list[str]] = {
    "power bi": ["powerbi", "power-bi"],
    "sql":      ["structured query language"],
    "python":   ["py"],
    "tableau":  ["data visualization"],
    "etl":      ["data pipeline"],
    "aws":      ["amazon web services"],
}

# Context phrases → skills to infer when the phrase appears in job text.
# These are BI-domain signals broad enough to justify inferring the tools.
CONTEXT_RULES: dict[str, list[str]] = {
    "dashboard":         ["power bi", "tableau"],
    "reporting":         ["power bi", "ssrs"],
    "data visualization":["power bi", "tableau"],
    "build reports":     ["power bi", "ssrs"],
    "create reports":    ["power bi", "ssrs"],
}


def matchSkill(text: str, skill: str) -> bool:
    pattern = rf"\b{re.escape(skill)}\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


def detectSkills(text: str) -> list[str]:
    normalized = normalizeText(text)
    found: list[str] = []
    seen: set[str] = set()

    def _add(skill: str) -> None:
        if skill not in seen:
            found.append(skill)
            seen.add(skill)

    # Step 1 — exact keyword match
    for skill in SKILLS:
        if len(skill) >= 3 and matchSkill(normalized, skill):
            _add(skill)

    # Step 2 — synonym match → add canonical skill
    for canonical, aliases in SKILL_SYNONYMS.items():
        if canonical not in seen:
            for alias in aliases:
                if matchSkill(normalized, alias):
                    _add(canonical)
                    break

    # Step 3 — context inference → infer BI tools from domain phrases.
    # Uses substring search (not word boundaries) so "dashboards" matches "dashboard".
    for phrase, inferred_skills in CONTEXT_RULES.items():
        if phrase in normalized:
            for skill in inferred_skills:
                _add(skill)

    return found


# ─────────────────────────────────────────────
# 5. JOB MATCHING (WEIGHTED)
# ─────────────────────────────────────────────

def matchResumeToJob(
    candidateSkills: list[str],
    jobSkills: dict[str, list[str]],
) -> dict:
    """
    Score a candidate against a job using weighted required/optional skills.

    Args:
        candidateSkills: Skills extracted from the resume.
        jobSkills: Dict with keys "required" and "optional" (both list[str]).

    Returns:
        {
            "score":           int   # 0-100 weighted percentage
            "requiredMatches": list  # required skills the candidate has
            "optionalMatches": list  # optional skills the candidate has
            "missingRequired": list  # required skills the candidate lacks
        }

    Scoring formula:
        required_score * 0.7 + optional_score * 0.3
    """
    required = jobSkills.get("required", [])
    optional = jobSkills.get("optional", [])
    candidate_set = set(candidateSkills)

    required_matches = [s for s in required if s in candidate_set]
    optional_matches = [s for s in optional if s in candidate_set]
    missing_required = [s for s in required if s not in candidate_set]

    required_score = len(required_matches) / len(required) if required else 0
    optional_score = len(optional_matches) / len(optional) if optional else 0

    score = int((required_score * 0.7 + optional_score * 0.3) * 100)

    return {
        "score": score,
        "requiredMatches": required_matches,
        "optionalMatches": optional_matches,
        "missingRequired": missing_required,
    }


# ─────────────────────────────────────────────
# 6. TERMINAL TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    candidateSkills = ["python", "sql", "power bi", "aws"]
    jobSkills = {
        "required": ["python", "sql"],
        "optional": ["aws", "power bi"],
    }

    result = matchResumeToJob(candidateSkills, jobSkills)

    print("WEIGHTED MATCH RESULT:", result)
