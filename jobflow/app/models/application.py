from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from jobflow.app.core.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    status = Column(Text, default="Submitted")
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
