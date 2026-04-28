"""
JobFlow Demo Backend — SQLite edition
Run: uvicorn jobflow.demo.backend:app --port 9000 --reload
"""

import os
import re
import tempfile

import pdfplumber
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from jobflow.demo.database import Base, engine, get_db
from jobflow.demo.models import Application, Candidate

# Create tables on startup
Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────
# App + CORS
# ─────────────────────────────────────────────

app = FastAPI(title="JobFlow Demo", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

KNOWN_SKILLS = [
    "python", "sql", "fastapi", "machine learning", "aws",
    "docker", "java", "javascript", "pandas", "spark",
    "excel", "power bi", "git", "react", "tensorflow",
]

DEMO_JOBS = [
    {"title": "Data Analyst",  "required": ["sql", "python"],              "optional": ["power bi", "excel"]},
    {"title": "Data Engineer", "required": ["aws", "spark"],               "optional": ["docker"]},
    {"title": "ML Engineer",   "required": ["python", "machine learning"], "optional": ["pandas", "docker"]},
    {"title": "Backend Dev",   "required": ["python", "fastapi"],          "optional": ["aws", "docker"]},
]


def _extract_text(path: str) -> str:
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    return text


def _parse_name(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if 2 <= len(line.split()) <= 4 and re.match(r"^[A-Za-z\s\-\.]+$", line):
            return line
    return "Unknown"


def _parse_email(text: str) -> str:
    m = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
    return m.group(0) if m else "unknown@example.com"


def _parse_skills(text: str) -> list[str]:
    lower = text.lower()
    return [s for s in KNOWN_SKILLS if s in lower]


def _rank_jobs(skills: list[str]) -> list[dict]:
    results = []
    for job in DEMO_JOBS:
        req = [s for s in job["required"] if s in skills]
        opt = [s for s in job["optional"] if s in skills]
        missing = [s for s in job["required"] if s not in skills]
        score = len(req) * 2 + len(opt)
        reason = (
            f"Matched {len(req)} required skill(s), missing {len(missing)}"
            if score > 0 else "Low match — missing most required skills"
        )
        results.append({"job_title": job["title"], "score": score, "reason": reason})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class ApplyRequest(BaseModel):
    candidate_id: int
    job_title: str
    score: int = 0

# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        text = _extract_text(temp_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")
    finally:
        os.unlink(temp_path)

    name = _parse_name(text)
    email = _parse_email(text)
    skills = _parse_skills(text)

    # Save candidate to database
    try:
        candidate = Candidate(name=name, email=email, skills=",".join(skills))
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return {
        "message": "Resume uploaded successfully",
        "candidate_id": candidate.id,
        "name": name,
        "email": email,
        "skills": skills,
        "ranked_jobs": _rank_jobs(skills),
    }


@app.post("/apply/")
def apply(payload: ApplyRequest, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {payload.candidate_id} not found.")

    try:
        application = Application(
            candidate_id=payload.candidate_id,
            job_title=payload.job_title,
            score=payload.score,
        )
        db.add(application)
        db.commit()
        db.refresh(application)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return {
        "message": "Application submitted successfully",
        "application_id": application.id,
        "candidate_id": payload.candidate_id,
        "job_title": payload.job_title,
        "score": payload.score,
    }
