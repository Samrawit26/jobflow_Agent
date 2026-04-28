def analyze_skill_gap(resume_skills, job_skills):
    required = job_skills.get("required", [])
    optional = job_skills.get("optional", [])

    matched_required = [s for s in required if s in resume_skills]
    matched_optional = [s for s in optional if s in resume_skills]

    missing_required = [s for s in required if s not in resume_skills]
    missing_optional = [s for s in optional if s not in resume_skills]

    return {
        "matched_skills": matched_required + matched_optional,
        "missing_required": missing_required,
        "missing_optional": missing_optional
    }