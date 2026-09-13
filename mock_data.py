"""
Mock data generator providing sample folders and exam/evaluation datasets
for demonstration and offline testing.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_mock_folders():
    """Returns a list of mock folder metadata dictionaries."""
    return [
        {"id": "mock_folder_midterm", "name": "📁 Midterm Exam 2026"},
        {"id": "mock_folder_final", "name": "📁 Final Semester Exams 2026"},
        {"id": "mock_folder_cie", "name": "📁 Continuous Internal Evaluation (CIE)"},
        {"id": "mock_folder_placement", "name": "📁 Aptitude & Placement Mock Tests"}
    ]

def get_mock_folder_data(folder_id: str) -> pd.DataFrame:
    """Generates synthetic dataframe mimicking realistic institutional exam performance."""
    np.random.seed(abs(hash(folder_id)) % (2**32))
    
    departments = ["Computer Engineering", "Information Technology", "Data Science", "AI & ML", "Electronics & Telecom"]
    divisions = ["Div A", "Div B", "Div C"]
    
    if folder_id == "mock_folder_midterm":
        subjects = ["Data Structures & Algorithms", "Database Management Systems", "Operating Systems", "Discrete Mathematics"]
        n_records = 180
        score_mean, score_std = 68, 14
        max_marks = 100
        pass_cutoff = 40
    elif folder_id == "mock_folder_final":
        subjects = ["Cloud Computing", "Machine Learning", "Computer Networks", "Cybersecurity", "Software Engineering"]
        n_records = 240
        score_mean, score_std = 72, 12
        max_marks = 100
        pass_cutoff = 40
    elif folder_id == "mock_folder_cie":
        subjects = ["Lab Assignment 1", "Mini Project Phase 1", "Quiz 1", "Technical Presentation"]
        n_records = 150
        score_mean, score_std = 21, 3.5
        max_marks = 25
        pass_cutoff = 10
    else:  # placement
        subjects = ["Quantitative Aptitude", "Logical Reasoning", "Verbal Ability", "Coding Round"]
        n_records = 200
        score_mean, score_std = 58, 18
        max_marks = 100
        pass_cutoff = 50

    records = []
    base_date = datetime.now() - timedelta(days=60)
    
    for i in range(1, n_records + 1):
        student_id = f"SVKM-2026-{1000 + i}"
        dept = np.random.choice(departments)
        div = np.random.choice(divisions)
        subj = np.random.choice(subjects)
        
        # Raw score bounded between 0 and max_marks
        raw_score = np.random.normal(score_mean, score_std)
        score = int(np.clip(raw_score, 5, max_marks))
        
        pct = (score / max_marks) * 100
        if pct >= 80:
            grade = "A+ (Distinction)"
        elif pct >= 70:
            grade = "A (First Class)"
        elif pct >= 60:
            grade = "B+ (Higher Second)"
        elif pct >= 50:
            grade = "B (Second Class)"
        elif pct >= pass_cutoff:
            grade = "C (Pass)"
        else:
            grade = "F (Fail)"
            
        status = "Pass" if score >= pass_cutoff else "Fail"
        attendance_pct = int(np.clip(np.random.normal(82, 11), 35, 100))
        exam_date = (base_date + timedelta(days=int(np.random.randint(0, 45)))).strftime("%Y-%m-%d")
        
        records.append({
            "Student_ID": student_id,
            "Department": dept,
            "Division": div,
            "Subject": subj,
            "Marks_Obtained": score,
            "Max_Marks": max_marks,
            "Percentage": round(pct, 1),
            "Grade": grade,
            "Result_Status": status,
            "Attendance_Rate_%": attendance_pct,
            "Exam_Date": exam_date
        })
        
    df = pd.DataFrame(records)
    return df
