from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Grade(Base):
    __tablename__ = 'grades'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Student info
    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    email = Column(String, nullable=False)  # Used as unique student ID
    
    # Assignment info
    assignment = Column(String, nullable=False)
    assignment_date = Column(Date, nullable=True)
    max_points = Column(Float, nullable=False)
    
    # Grade
    mark = Column(Float, nullable=False)
    
    # Multi-tenant
    tenant_id = Column(String, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('email', 'assignment', 'tenant_id', name='uq_grade_per_student_assignment'),
    )

def create_tables():
    from database import engine
    Base.metadata.create_all(bind=engine)
