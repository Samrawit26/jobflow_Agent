from fastapi import FastAPI, UploadFile, File, Depends
import shutil
import os

from sqlalchemy.orm import Session

from jobflow.app.core.database import get_db
from jobflow.resume.parser import parse_resume
from jobflow.app.models.candidate import Candidate
from execution.parse_resume_data import parse_resume_data

app = FastAPI(title="JobFlow AI Career Engine")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload-resume/")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    print("🔥 UPLOAD ENDPOINT HIT")
    content = await file.read()

    parsed = parse_resume_data(content, file.filename or "resume.txt")

    print("TEXT:", parsed["resume_text"][:500])
    print("SKILLS FOUND:", parsed["skills"])

    new_candidate = Candidate(
        name=parsed["name"] or "Unknown",
        email=parsed["email"] or "unknown@example.com",
        skills=parsed["skills"],
        experience_years=parsed["experience_years"],
        resume_text=parsed["resume_text"],
    )

    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)

    return {
        "message": "Resume uploaded successfully",
        "candidate_id": new_candidate.id,
        "skills": parsed["skills"],
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
