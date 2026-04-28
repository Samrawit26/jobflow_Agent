def rank_jobs(resume_skills, jobs):
    ranked_results = []

    for job in jobs:
        title = job["title"]
        jobSkills = job["skills"]

        required = jobSkills.get("required", [])
        optional = jobSkills.get("optional", [])

        # scoring (reuse your logic idea)
        required_matches = [s for s in required if s in resume_skills]
        optional_matches = [s for s in optional if s in resume_skills]

        score = (len(required_matches) * 2) + len(optional_matches)

        # missing skills
        missing_required = [s for s in required if s not in resume_skills]

        # explanation
        if score > 0:
            reason = f"Matched {len(required_matches)} required skills, missing {len(missing_required)}"
        else:
            reason = "Low match — missing most required skills"

        ranked_results.append({
            "job_title": title,
            "score": score,
            "reason": reason
        })

    # 🔥 SORT (MOST IMPORTANT)
    ranked_results.sort(key=lambda x: x["score"], reverse=True)

    return ranked_results