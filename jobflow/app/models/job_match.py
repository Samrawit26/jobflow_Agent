from sqlalchemy import Column, Integer, Text, Float, ForeignKey
from jobflow.app.core.database import Base


class JobMatch(Base):
    __tablename__ = "job_matches"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    job_title = Column(Text)
    company = Column(Text)
    match_score = Column(Float)