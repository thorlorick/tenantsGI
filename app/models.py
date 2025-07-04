from sqlalchemy import (
    Column, Integer, String, Float, Date, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Tenant(Base):
    __tablename__ = 'tenants'
    id = Column(String, primary_key=True)  # e.g., "lincoln_high"
    name = Column(String, nullable=False, unique=True)

    students = relationship("Student", back_populates="tenant", cascade="all, delete-orphan")
    teachers = relationship("Teacher", back_populates="tenant", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="tenant", cascade="all, delete-orphan")
    grades = relationship("Grade", back_populates="tenant", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, nullable=False)
    tenant_id = Column(String, ForeignKey('tenants.id'), nullable=False)

    __table_args__ = (UniqueConstraint('email', 'tenant_id', name='uq_student_email_per_tenant'),)

    tenant = relationship("Tenant", back_populates="students")
    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")


class Teacher(Base):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    tenant_id = Column(String, ForeignKey('tenants.id'), nullable=False)

    __table_args__ = (UniqueConstraint('name', 'tenant_id', name='uq_teacher_name_per_tenant'),)

    tenant = relationship("Tenant", back_populates="teachers")
    grades = relationship("Grade", back_populates="teacher")


class Assignment(Base):
    __tablename__ = 'assignments'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    date = Column(Date, nullable=True)
    max_points = Column(Float, nullable=False)
    tenant_id = Column(String, ForeignKey('tenants.id'), nullable=False)

    __table_args__ = (UniqueConstraint('name', 'tenant_id', name='uq_assignment_name_per_tenant'),)

    tenant = relationship("Tenant", back_populates="assignments")
    grades = relationship("Grade", back_populates="assignment")


class Grade(Base):
    __tablename__ = 'grades'
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    assignment_id = Column(Integer, ForeignKey('assignments.id'), nullable=False)
    tenant_id = Column(String, ForeignKey('tenants.id'), nullable=False)
    score = Column(Float, nullable=False)
    class_tag = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint('student_id', 'assignment_id', 'tenant_id', name='uq_grade_per_student_assignment'),
    )

    tenant = relationship("Tenant", back_populates="grades")
    student = relationship("Student", back_populates="grades")
    teacher = relationship("Teacher", back_populates="grades")
    assignment = relationship("Assignment", back_populates="grades")
