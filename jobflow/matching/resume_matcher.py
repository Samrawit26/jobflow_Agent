from jobflow.matching.ai_matcher import ai_job_match

def calculate_job_match_score(resume, job):
    score = 0
    total_weight = 100

    # ---- Skill Matching (50 points) ----
    resume_skills = set(resume.get("skills", []))
    job_skills = set([s.lower() for s in job.get("skills", [])])

    if job_skills:
        skill_match_count = len(resume_skills.intersection(job_skills))
        skill_score = (skill_match_count / len(job_skills)) * 50
        score += skill_score

    # ---- Experience Matching (20 points) ----
    resume_years = resume.get("years_experience", 0)
    job_years = job.get("experience_required", 0)

    if job_years:
        if resume_years >= job_years:
            score += 20
        else:
            score += (resume_years / job_years) * 20

    # ---- Title Matching (15 points) ----
    resume_titles = [exp.get("title", "").lower() for exp in resume.get("work_experience", [])]
    job_title = job.get("title", "").lower()

    if any(job_title in t for t in resume_titles):
        score += 15

    # ---- Summary Keyword Matching (15 points) ----
    summary = (resume.get("summary") or "").lower()
    keyword_hits = sum(1 for skill in job_skills if skill in summary)

    if job_skills:
        score += (keyword_hits / len(job_skills)) * 15

    return round(score, 2)

def rank_jobs_for_resume(resume, jobs, use_ai=True):
    for job in jobs:
        rule_score = calculate_job_match_score(resume, job)
        job["rule_match_score"] = rule_score

        if use_ai:
            try:
                ai_result = ai_job_match(resume, job)
                ai_score = ai_result.get("match_score", 0)
                job["ai_match_score"] = ai_score
            except Exception:
                ai_score = 0
                job["ai_match_score"] = 0
        else:
            ai_score = 0

        # Combine scores
        final_score = (0.6 * rule_score) + (0.4 * ai_score)
        job["final_match_score"] = round(final_score, 2)

    return sorted(jobs, key=lambda x: x["final_match_score"], reverse=True)
