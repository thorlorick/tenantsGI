from fastapi import FastAPI, Request, HTTPException, Depends, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
import io
from datetime import datetime

from database import get_db, get_tenant_from_host
from models import Grade, create_tables

app = FastAPI(title="Grade Insight")

# Create tables on startup
create_tables()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    tenant_id = get_tenant_from_host(request.headers.get("host"))
    
    # Get basic stats
    total_students = db.query(func.count(func.distinct(Grade.email))).filter(Grade.tenant_id == tenant_id).scalar() or 0
    total_assignments = db.query(func.count(func.distinct(Grade.assignment))).filter(Grade.tenant_id == tenant_id).scalar() or 0
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request, 
            "tenant_id": tenant_id,
            "total_students": total_students,
            "total_assignments": total_assignments
        }
    )

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def upload_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    tenant_id = get_tenant_from_host(request.headers.get("host"))
    
    try:
        # Read CSV content
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # Process the 3-row format from README
        # Row 1: Assignment names (headers)
        # Row 2: Dates (optional)
        # Row 3: Max points
        # Row 4+: Student data
        
        # Get assignment columns (exclude student info columns)
        assignment_columns = [col for col in df.columns if col not in ['last_name', 'first_name', 'email']]
        
        # Extract dates and points from special rows
        dates_row = None
        points_row = None
        
        # Look for DATE and POINTS rows
        for idx, row in df.iterrows():
            if str(row.get('last_name', '')).upper() == 'DATE':
                dates_row = row
                df = df.drop(idx)
            elif str(row.get('last_name', '')).upper() == 'POINTS':
                points_row = row
                df = df.drop(idx)
        
        # Reset index after dropping rows
        df = df.reset_index(drop=True)
        
        # Process each student row
        records_processed = 0
        for _, row in df.iterrows():
            # Skip empty rows
            if pd.isna(row.get('last_name')) or pd.isna(row.get('first_name')) or pd.isna(row.get('email')):
                continue
                
            student_info = {
                'last_name': str(row['last_name']).strip(),
                'first_name': str(row['first_name']).strip(),
                'email': str(row['email']).strip().lower()
            }
            
            # Process each assignment
            for assignment_name in assignment_columns:
                mark = row.get(assignment_name)
                if pd.isna(mark) or mark == '':
                    continue
                
                # Get assignment date if available
                assignment_date = None
                if dates_row is not None and assignment_name in dates_row:
                    date_str = str(dates_row[assignment_name])
                    if date_str and date_str != 'nan' and date_str != '-':
                        try:
                            assignment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        except:
                            pass
                
                # Get max points if available
                max_points = 100.0  # default
                if points_row is not None and assignment_name in points_row:
                    points_str = str(points_row[assignment_name])
                    if points_str and points_str != 'nan' and points_str != '-':
                        try:
                            max_points = float(points_str)
                        except:
                            pass
                
                # Check if grade already exists
                existing_grade = db.query(Grade).filter(
                    Grade.email == student_info['email'],
                    Grade.assignment == assignment_name,
                    Grade.tenant_id == tenant_id
                ).first()
                
                if existing_grade:
                    # Update existing grade
                    existing_grade.mark = float(mark)
                    existing_grade.max_points = max_points
                    existing_grade.assignment_date = assignment_date
                    existing_grade.last_name = student_info['last_name']
                    existing_grade.first_name = student_info['first_name']
                else:
                    # Create new grade
                    grade = Grade(
                        last_name=student_info['last_name'],
                        first_name=student_info['first_name'],
                        email=student_info['email'],
                        assignment=assignment_name,
                        assignment_date=assignment_date,
                        max_points=max_points,
                        mark=float(mark),
                        tenant_id=tenant_id
                    )
                    db.add(grade)
                
                records_processed += 1
        
        db.commit()
        
        return JSONResponse({
            "message": f"Successfully processed {records_processed} grade records",
            "status": "success"
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

@app.get("/api/student/{email}/grades")
async def get_student_grades(email: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = get_tenant_from_host(request.headers.get("host"))
    
    grades = db.query(Grade).filter(
        Grade.email == email.lower(),
        Grade.tenant_id == tenant_id
    ).all()
    
    if not grades:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Calculate summary stats
    total_points = sum(grade.mark for grade in grades)
    total_possible = sum(grade.max_points for grade in grades)
    overall_percentage = (total_points / total_possible * 100) if total_possible > 0 else 0
    
    return {
        "first_name": grades[0].first_name,
        "last_name": grades[0].last_name,
        "email": grades[0].email,
        "total_assignments": len(grades),
        "total_points": total_points,
        "max_possible": total_possible,
        "overall_percentage": round(overall_percentage, 1),
        "grades": [
            {
                "assignment": grade.assignment,
                "date": grade.assignment_date.isoformat() if grade.assignment_date else None,
                "score": grade.mark,
                "max_points": grade.max_points
            }
            for grade in grades
        ]
    }

@app.get("/api/grades-table")
async def get_grades_table(request: Request, db: Session = Depends(get_db)):
    tenant_id = get_tenant_from_host(request.headers.get("host"))
    
    grades = db.query(Grade).filter(Grade.tenant_id == tenant_id).all()
    
    # Group by student
    students_dict = {}
    for grade in grades:
        student_key = grade.email
        if student_key not in students_dict:
            students_dict[student_key] = {
                "first_name": grade.first_name,
                "last_name": grade.last_name,
                "email": grade.email,
                "grades": []
            }
        
        students_dict[student_key]["grades"].append({
            "assignment": grade.assignment,
            "date": grade.assignment_date.isoformat() if grade.assignment_date else None,
            "score": grade.mark,
            "max_points": grade.max_points
        })
    
    return {"students": list(students_dict.values())}

@app.get("/student-portal", response_class=HTMLResponse)
async def student_portal(request: Request):
    return templates.TemplateResponse("student_portal.html", {"request": request})

@app.get("/teacher-student-view", response_class=HTMLResponse)
async def teacher_student_view(request: Request, email: str = None):
    return templates.TemplateResponse("teacher_student_view.html", {
        "request": request,
        "student_email": email
    })

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
