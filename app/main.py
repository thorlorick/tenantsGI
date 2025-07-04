from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import pandas as pd
import os

from database import get_db, get_tenant_from_host, Grade, Student, Teacher, create_tables

app = FastAPI(title="Grade Insight")

# Create tables on startup
create_tables()

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    tenant_id = get_tenant_from_host(request.headers.get("host"))
    
    # Get all students for this tenant
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
    
    # Read CSV
    content = await file.read()
    df = pd.read_csv(pd.StringIO(content.decode('utf-8')))
    
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
    
    # Process each row
    for _, row in df.iterrows():
        # Get or create student
        student = db.query(Student).filter(
            Student.name == row['Student Name'],
            Student.tenant_id == tenant_id
        ).first()
        
        if not student:
            student = Student(name=row['Student Name'], tenant_id=tenant_id)
            db.add(student)
            db.commit()
            db.refresh(student)
        
        # Create grade record
        grade = Grade(
            student_id=student.id,
            teacher_id=teacher.id,
            assignment=row['Assignment'],
            grade=row['Grade'],
            class_tag=class_tag,
            tenant_id=tenant_id
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
