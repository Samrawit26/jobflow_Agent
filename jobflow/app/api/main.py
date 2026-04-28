from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from jobflow.app.core.database import get_db
from jobflow.app.models.candidate import Candidate
from execution.parse_resume_data import parse_resume_data
from execution.pipeline import matchResumeToJob, detectSkills
from jobflow.app.models.job_match import JobMatch
from jobflow.app.models.application import Application
from jobflow.app.services.skill_gap_analyzer import analyze_skill_gap
from jobflow.app.services.job_ranker import rank_jobs

app = FastAPI(title="JobFlow AI Career Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload-resume/")
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = Form(default=""),
    db: Session = Depends(get_db),
):
    content = await file.read()
    parsed = parse_resume_data(content, file.filename or "resume.txt")
    resume_skills = parsed["skills"]

    # Job catalog — replace with DB query when ready
    job_catalog = [
        {"title": "Data Analyst",  "skills": {"required": ["sql", "python"],            "optional": ["power bi", "excel"]}},
        {"title": "Data Engineer", "skills": {"required": ["aws", "spark"],             "optional": ["docker"]}},
        {"title": "ML Engineer",   "skills": {"required": ["python", "machine learning"], "optional": ["pandas", "docker"]}},
        {"title": "Backend Dev",   "skills": {"required": ["python", "fastapi"],        "optional": ["aws", "docker"]}},
    ]

    # If a job description was provided, use it to build job_skills for single-job matching.
    # Otherwise fall back to the catalog so the score is never 0 due to empty skill lists.
    if job_description.strip():
        detected = detectSkills(job_description)
        job_skills = {"required": detected[:2], "optional": detected[2:]}
    else:
        # Use best-matched catalog job as the reference for match_result / gap
        ranked_jobs = rank_jobs(resume_skills, job_catalog)
        best = next((j for j in job_catalog if j["title"] == ranked_jobs[0]["job_title"]), job_catalog[0])
        job_skills = best["skills"]

    ranked_jobs = rank_jobs(resume_skills, job_catalog)
    match_result = matchResumeToJob(resume_skills, job_skills)
    gap = analyze_skill_gap(resume_skills, job_skills)

    new_candidate = Candidate(
        name=parsed["name"] or "Unknown",
        email=parsed["email"] or "unknown@example.com",
        skills=resume_skills,
        experience_years=parsed["experience_years"],
        resume_text=parsed["resume_text"],
    )

    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)

    return {
        "message": "Resume uploaded successfully",
        "candidate_id": new_candidate.id,
        "name": new_candidate.name,
        "email": new_candidate.email,
        "skills": resume_skills,
        "jobSkills": job_skills,
        "match": match_result,
        "analysis": gap,
        "ranked_jobs": ranked_jobs,
    }


@app.post("/auto-fill/")
def auto_fill(db: Session = Depends(get_db)):
    candidate = db.query(Candidate).order_by(Candidate.id.desc()).first()
    if not candidate:
        return {"error": "No candidates found"}

    match = (
        db.query(JobMatch)
        .filter(JobMatch.candidate_id == candidate.id)
        .order_by(JobMatch.id.desc())
        .first()
    )

    skills = candidate.skills or []
    top_skills = ", ".join(skills[:3]) if skills else "various technologies"

    response = {
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "skills": skills,
        "summary": f"Experienced professional with expertise in {top_skills}.",
    }

    if match:
        response.update({
            "match_score": match.match_score,
            "required_matches": match.required_matches or [],
            "optional_matches": match.optional_matches or [],
        })

    return response


# -----------------------------
# Auto Apply (Simulated)
# -----------------------------

@app.post("/apply/{job_id}/{candidate_id}")
async def auto_apply(job_id: int, candidate_id: int, db: Session = Depends(get_db)):
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error during candidate lookup: {e}")

    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    await asyncio.sleep(2)

    applied_at = datetime.now(timezone.utc)

    try:
        application = Application(
            job_id=job_id,
            candidate_id=candidate_id,
            status="Submitted",
            applied_at=applied_at,
        )
        db.add(application)
        db.commit()
        db.refresh(application)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save application: {e}")

    return {
        "message": "Application submitted successfully",
        "application": {
            "job_id": job_id,
            "status": "Submitted",
            "applied_at": applied_at.isoformat(),
            "candidate": {
                "name": candidate.name,
                "email": candidate.email,
                "skills": candidate.skills or [],
            },
        },
    }


# -----------------------------
# Full Auto-Apply Flow
# -----------------------------

# Demo job catalog — replace with DB query when ready
_DEMO_JOBS = [
    {"id": 1, "title": "Data Analyst",   "skills": {"required": ["sql", "python"],      "optional": ["power bi", "excel"]}},
    {"id": 2, "title": "Data Engineer",  "skills": {"required": ["aws", "spark"],       "optional": ["docker"]}},
    {"id": 3, "title": "ML Engineer",    "skills": {"required": ["python", "machine learning"], "optional": ["pandas", "docker"]}},
    {"id": 4, "title": "Backend Dev",    "skills": {"required": ["python", "fastapi"],  "optional": ["aws", "docker"]}},
]


@app.post("/auto-apply/{candidate_id}")
async def auto_apply_best_job(candidate_id: int, db: Session = Depends(get_db)):
    # 1. Fetch candidate
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error fetching candidate: {e}")

    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    resume_skills = candidate.skills or []

    # 2. Rank jobs against candidate skills
    ranked = rank_jobs(resume_skills, _DEMO_JOBS)

    if not ranked or ranked[0]["score"] == 0:
        raise HTTPException(
            status_code=404,
            detail="No suitable jobs found for this candidate's skill set.",
        )

    best = ranked[0]

    # Resolve job_id from the original catalog by title match
    job_id = next(
        (j["id"] for j in _DEMO_JOBS if j["title"] == best["job_title"]),
        0,
    )

    # 3. Simulate processing delay
    await asyncio.sleep(2)

    # 4. Save application record
    applied_at = datetime.now(timezone.utc)

    try:
        application = Application(
            job_id=job_id,
            candidate_id=candidate_id,
            status="Submitted",
            applied_at=applied_at,
        )
        db.add(application)
        db.commit()
        db.refresh(application)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save application: {e}")

    # 5. Return structured response
    return {
        "message": "Application submitted successfully",
        "application": {
            "id": application.id,
            "status": "Submitted",
            "applied_at": applied_at.isoformat(),
            "best_job": {
                "job_id": job_id,
                "title": best["job_title"],
                "match_score": best["score"],
                "reason": best["reason"],
            },
            "candidate": {
                "id": candidate_id,
                "name": candidate.name,
                "email": candidate.email,
                "skills": resume_skills,
            },
        },
    }


