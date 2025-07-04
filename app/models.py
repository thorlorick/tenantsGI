from sqlalchemy import (
    Column, Integer, String, Float, Date, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)

    students = relationship("Student", back_populates="tenant", cascade="all, delete")
    teachers = relationship("Teacher", back_populates="tenant", cascade="all, delete")
    assignments = relationship("Assignment", back_populates="tenant", cascade="all, delete")
    grades = relationship("Grade", back_populates="tenant", cascade="all, delete")


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)

    tenant = relationship("Tenant", back_populates="students")
    grades = relationship("Grade", back_populates="student", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_student_email_tenant"),
    )


class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)

    tenant = relationship("Tenant", back_populates="teachers")
    grades = relationship("Grade", back_populates="teacher", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("name", "tenant_id", name="uq_teacher_name_tenant"),
    )


class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    max_points = Column(Float, nullable=False, default=100.0)
    date = Column(Date, nullable=True)

    tenant = relationship("Tenant", back_populates="assignments")
    grades = relationship("Grade", back_populates="assignment", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("name", "tenant_id", name="uq_assignment_name_tenant"),
    )


class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)
    score = Column(Float, nullable=False)
    class_tag = Column(String, nullable=True)

    tenant = relationship("Tenant", back_populates="grades")
    student = relationship("Student", back_populates="grades")
    assignment = relationship("Assignment", back_populates="grades")
    teacher = relationship("Teacher", back_populates="grades")

    __table_args__ = (
        UniqueConstraint("student_id", "assignment_id", "tenant_id", name="uq_grade_per_student_assignment"),
    )
