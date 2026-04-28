from sqlalchemy import Column, Integer, Text, ARRAY
from jobflow.app.core.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text)
    email = Column(Text)
    phone = Column(Text)
    skills = Column(ARRAY(Text))
    experience_years = Column(Integer)
    resume_text = Column(Text)