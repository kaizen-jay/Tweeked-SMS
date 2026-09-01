"""
Student Management System — FastAPI backend.

This file exposes a small CRUD API over a JSON file (students.json) that
acts as a simple flat-file database. It is meant to be run standalone with:

    uvicorn sms:app --reload

and consumed by a separate client (e.g. the Streamlit frontend), so this
file has NO frontend / UI imports — it only depends on FastAPI + Pydantic.
"""

import json
import os
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Student Management System")

# ---------------------------------------------------------------------------
# DATA FILE CONFIG
# ---------------------------------------------------------------------------
# Centralizing the filename in one constant avoids typos/mismatches between
# load_data() and save_data(), and makes it trivial to change later
# (e.g. point to a different file per environment).
DATA_FILE = "students.json"


# ---------------------------------------------------------------------------
# PYDANTIC MODELS
# ---------------------------------------------------------------------------
class Student(BaseModel):
    """Full student record — used when creating (POST /add) and internally
    when re-validating a record after an update."""

    enroll: Annotated[
        str, Field(..., description="Enrollment no. of the student", examples=["LNCFBTC00001"])
    ]
    roll_no: Annotated[str, Field(..., description="Roll no. of the student", examples=["001"])]
    name: Annotated[str, Field(..., description="First name of the student")]
    age: Annotated[int, Field(..., gt=0, lt=30, description="Age of the student")]
    gender: Annotated[
        Literal["Male", "Female", "Others"], Field(..., description="Gender of the student")
    ]
    contact_no: Annotated[int, Field(..., description="Contact no. of the student")]
    father_name: Annotated[str, Field(..., description="Father's name")]
    mother_name: Annotated[str, Field(..., description="Mother's name")]
    course: Annotated[
        str,
        Field(..., description="Course which student pursues", examples=["B.Tech", "BBA", "B.Com"]),
    ]
    city: Annotated[str, Field(..., description="City where student lives in")]


class StudentUpdate(BaseModel):
    """Partial student record — every field is optional, used for PUT /edit.
    Only the fields the client actually sends get overwritten
    (see `exclude_unset=True` in update_student)."""

    roll_no: Annotated[Optional[str], Field(default=None)]
    name: Annotated[Optional[str], Field(default=None)]
    age: Annotated[Optional[int], Field(default=None, gt=0, lt=30)]
    gender: Annotated[Optional[Literal["Male", "Female", "Others"]], Field(default=None)]
    contact_no: Annotated[Optional[int], Field(default=None)]
    father_name: Annotated[Optional[str], Field(default=None)]
    mother_name: Annotated[Optional[str], Field(default=None)]
    course: Annotated[Optional[str], Field(default=None)]
    city: Annotated[Optional[str], Field(default=None)]


# ---------------------------------------------------------------------------
# DATA ACCESS HELPERS
# ---------------------------------------------------------------------------
def load_data() -> dict:
    """
    Load the student database from disk.

    Handles two edge cases the original version didn't:
    - File doesn't exist yet (first run) -> returns an empty dict instead
      of crashing with FileNotFoundError.
    - File exists but is empty/corrupted -> returns an empty dict instead
      of crashing with json.JSONDecodeError.
    """
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Corrupted or empty file — fail safe rather than crash the app.
        return {}


def save_data(data: dict) -> None:
    """Persist the student database to disk as pretty-printed JSON."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------------------------------------------------------------------------
# ROOT / HEALTH CHECKKK
# ---------------------------------------------------------------------------
@app.get("/")
def hello():
    """Simple landing endpoint — useful to confirm the API is up."""
    return {"message": "STUDENT MANAGEMENT SYSTEM"}


# ---------------------------------------------------------------------------
# READ endpoints
# ---------------------------------------------------------------------------
@app.get("/view")
def view():
    """Return every student record, keyed by enrollment number."""
    return load_data()


@app.get("/student/{student_enroll}")
def view_student(student_enroll: str):
    """Return a single student's record by enrollment number."""
    data = load_data()
    if student_enroll in data:
        return data[student_enroll]
    # Fixed: original message said "Patient not found" (copy-paste leftover).
    raise HTTPException(status_code=404, detail="Student not found")


# ---------------------------------------------------------------------------
# CREATE endpoint
# ---------------------------------------------------------------------------
@app.post("/add", status_code=201)
def add_student(student: Student):
    """Add a new student. Fails with 400 if the enrollment no. already exists."""
    data = load_data()

    if student.enroll in data:
        raise HTTPException(status_code=400, detail="Student already exists")

    # enroll is the dict KEY, so we don't store it again inside the value.
    data[student.enroll] = student.model_dump(exclude={"enroll"})
    save_data(data)

    return JSONResponse(status_code=201, content={"message": "Student created successfully"})


# ---------------------------------------------------------------------------
# UPDATE endpoint
# ---------------------------------------------------------------------------
@app.put("/edit/{student_enroll}")
def update_student(student_enroll: str, student_update: StudentUpdate):
    """
    Partially update an existing student.

    Only fields present in the request body overwrite the stored record
    (exclude_unset=True). After merging, the result is re-validated through
    the full `Student` model so a partial update can never leave the record
    in an invalid state (e.g. age out of range).
    """
    data = load_data()
    if student_enroll not in data:
        raise HTTPException(status_code=404, detail="Student not found")

    existing_student_info = data[student_enroll]
    update_student_info = student_update.model_dump(exclude_unset=True)

    for key, value in update_student_info.items():
        existing_student_info[key] = value

    # Re-validate the merged record as a full Student to catch any
    # inconsistency introduced by the partial update.
    existing_student_info["enroll"] = student_enroll
    student_pydantic_object = Student(**existing_student_info)
    existing_student_info = student_pydantic_object.model_dump(exclude={"enroll"})

    data[student_enroll] = existing_student_info
    save_data(data)

    return JSONResponse(status_code=200, content={"message": "Student updated"})


# ---------------------------------------------------------------------------
# DELETE endpoint
# ---------------------------------------------------------------------------
@app.delete("/delete/{student_enroll}")
def delete_student(student_enroll: str):
    """Delete a student record by enrollment number."""
    data = load_data()
    if student_enroll not in data:
        raise HTTPException(status_code=404, detail="Student not found")

    del data[student_enroll]
    save_data(data)

    return JSONResponse(status_code=200, content={"message": "Student deleted"})


# ---------------------------------------------------------------------------
# LOCAL DEV ENTRYPOINT
# ---------------------------------------------------------------------------
# Lets you run `python sms.py` directly as an alternative to typing out the
# full `uvicorn sms:app --reload` command every time.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("sms:app", host="127.0.0.1", port=8000, reload=True)
