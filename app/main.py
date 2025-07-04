from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import pandas as pd
import io

from database import get_db, get_tenant_from_host
from models import Grade, Student, Teacher, Assignment, Tenant, Base, create_tables  # Adjust import if create_tables is in database.py

app = FastAPI(title="Grade Insight")

# Create tables on startup
create_tables()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    tenant_id = get_tenant_from_host(request.headers.get("host"))

    students = db.query(Student).filter(Student.tenant_id == tenant_id).all()

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "students": students, "tenant": tenant_id}
    )


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    teacher_name: str = Form(...),
    class_tag: str = Form(...),
    db: Session = Depends(get_db)
):
    tenant_id = get_tenant_from_host(request.headers.get("host"))

    # Read CSV content
    content = await file.read()
    df = pd.read_csv(io.StringIO(content.decode('utf-8')))

    # Get or create teacher
    teacher = db.query(Teacher).filter(
        Teacher.name == teacher_name,
        Teacher.tenant_id == tenant_id
    ).first()

    if not teacher:
        teacher = Teacher(name=teacher_name, tenant_id=tenant_id)
        db.add(teacher)
        db.commit()
        db.refresh(teacher)

    # Determine assignment columns (exclude 'Last Name', 'First Name', 'Email')
    assignment_columns = [col for col in df.columns if col not in ("Last Name", "First Name", "Email")]

    # You may need max_points info - assume separate rows or set to None for now
    # For this example, max_points is not handled and defaults to 100
    DEFAULT_MAX_POINTS = 100.0

    # Cache assignments by name for this tenant to avoid repeated queries
    assignments_cache = {}

    for col in assignment_columns:
        assignment = db.query(Assignment).filter(
            Assignment.name == col,
            Assignment.tenant_id == tenant_id
        ).first()
        if not assignment:
            assignment = Assignment(
                name=col,
                tenant_id=tenant_id,
                max_points=DEFAULT_MAX_POINTS
            )
            db.add(assignment)
            db.commit()
            db.refresh(assignment)
        assignments_cache[col] = assignment

    # Process each row (student)
    for _, row in df.iterrows():
        first_name = row["First Name"]
        last_name = row["Last Name"]
        email = row["Email"]

        # Get or create student by email + tenant
        student = db.query(Student).filter(
            Student.email == email,
            Student.tenant_id == tenant_id
        ).first()

        if not student:
            student = Student(
                first_name=first_name,
                last_name=last_name,
                email=email,
                tenant_id=tenant_id
            )
            db.add(student)
            db.commit()
            db.refresh(student)

        # Create grades for each assignment column
        for assignment_name in assignment_columns:
            score_value = row[assignment_name]
            if pd.isna(score_value):
                continue  # skip if no grade

            assignment = assignments_cache[assignment_name]

            # Check if grade already exists (unique constraint)
            existing_grade = db.query(Grade).filter(
                Grade.student_id == student.id,
                Grade.assignment_id == assignment.id,
                Grade.tenant_id == tenant_id
            ).first()

            if existing_grade:
                # Update existing grade
                existing_grade.score = float(score_value)
                existing_grade.teacher_id = teacher.id
                existing_grade.class_tag = class_tag
            else:
                # New grade
                grade = Grade(
                    student_id=student.id,
                    teacher_id=teacher.id,
                    assignment_id=assignment.id,
                    tenant_id=tenant_id,
                    score=float(score_value),
                    class_tag=class_tag
                )
                db.add(grade)

    db.commit()
    return {"message": "CSV uploaded successfully"}


@app.get("/api/student/{student_id}/grades")
async def get_student_grades(student_id: int, request: Request, db: Session = Depends(get_db)):
    tenant_id = get_tenant_from_host(request.headers.get("host"))

    grades = db.query(Grade).filter(
        Grade.student_id == student_id,
        Grade.tenant_id == tenant_id
    ).all()

    return grades


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
