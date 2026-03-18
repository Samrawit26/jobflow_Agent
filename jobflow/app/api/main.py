from fastapi import FastAPI, UploadFile, File, Depends
import shutil
import os

from sqlalchemy.orm import Session

from jobflow.app.core.database import get_db
from jobflow.resume.parser import parse_resume
from jobflow.app.models.candidate import Candidate

app = FastAPI(title="JobFlow AI Career Engine")


@app.get("/health")
def health():
    return {"status": "ok"}


KNOWN_SKILLS = [
    "python", "sql", "fastapi", "machine learning",
    "aws", "docker", "java", "javascript",
]


@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    resume_text = content.decode("utf-8", errors="ignore")

    text_lower = resume_text.lower()
    skills = [skill for skill in KNOWN_SKILLS if skill in text_lower]

    candidate = Candidate(
        name="Unknown",
        email="unknown@example.com",
        skills=skills,
        experience_years=0,
        resume_text=resume_text,
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return {
        "message": "Resume uploaded successfully",
        "candidate_id": candidate.id,
        "skills": skills,
    }


@app.post("/parse-resume")
async def parse_resume_endpoint(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_location = f"temp_{file.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        parsed_data = parse_resume(file_location)
    finally:
        os.remove(file_location)

    candidate = Candidate(
        name=parsed_data.get("name"),
        email=parsed_data.get("email"),
        skills=parsed_data.get("skills"),
        experience_years=parsed_data.get("experience_years"),
        resume_text=parsed_data.get("resume_text"),
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return parsed_data
