"""
Streamlit frontend for the Student Management System (FastAPI backend).

This file is a pure frontend — it does NOT touch students.json directly.
Every action here calls your FastAPI endpoints over HTTP using `requests`.
Run your FastAPI server first (uvicorn sms:app --reload), then run this
file with: streamlit run streamlit_app.py
"""

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
# Base URL of your FastAPI server. Change this if you run uvicorn on a
# different host/port.
BASE_URL = "http://127.0.0.1:8000"

# st.set_page_config MUST be the first Streamlit command that runs.
# It controls the browser tab title, icon, and overall page layout.
st.set_page_config(
    page_title="Student Management System",
    page_icon="🎓",
    layout="centered",
)

# ---------------------------------------------------------------------------
# MINIMAL CUSTOM CSS
# ---------------------------------------------------------------------------
# Streamlit's default look is fine but plain. Injecting a small amount of
# CSS via st.markdown(unsafe_allow_html=True) is the standard way to make a
# Streamlit app feel more polished without leaving Python....
st.markdown(
    """
    <style>
    /* Center the main title block and give it breathing room */
    .main-title {
        text-align: center;
        padding-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        color: #808495;
        margin-bottom: 2rem;
    }
    /* Make buttons full width and slightly rounded for a cleaner grid */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    /* Card-like container for student detail views */
    .student-card {
        background-color: #f7f9fc;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 class='main-title'>🎓 Student Management System</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Add, view, update, and delete student records</p>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SMALL HELPERS
# ---------------------------------------------------------------------------
# Centralizing the request logic in one function means every page below
# handles connection errors and non-2xx responses the same way, instead of
# repeating try/except blocks everywhere.


def api_call(method: str, endpoint: str, **kwargs):
    """
    Wrapper around `requests` that talks to the FastAPI backend.

    Returns a tuple: (success: bool, payload: dict | str)
    - On success, payload is the parsed JSON body.
    - On failure, payload is a human-readable error message.
    """
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, timeout=5, **kwargs)
    except requests.exceptions.ConnectionError:
        return False, "Could not reach the API. Is `uvicorn sms:app --reload` running?"
    except requests.exceptions.Timeout:
        return False, "The request timed out."

    # FastAPI returns JSON bodies even for errors (e.g. {"detail": "..."}),
    # so we try to parse JSON regardless of status code.
    try:
        body = response.json()
    except ValueError:
        body = response.text

    if response.status_code >= 400:
        # HTTPException details from FastAPI land in body["detail"]
        detail = body.get("detail", body) if isinstance(body, dict) else body
        return False, str(detail)

    return True, body


def render_student_card(enroll: str, info: dict):
    """Pretty-print a single student's info inside a styled card."""
    st.markdown("<div class='student-card'>", unsafe_allow_html=True)
    st.markdown(f"**Enrollment No.:** {enroll}")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Name:** {info.get('name', '-')}")
        st.markdown(f"**Roll No.:** {info.get('roll_no', '-')}")
        st.markdown(f"**Age:** {info.get('age', '-')}")
        st.markdown(f"**Gender:** {info.get('gender', '-')}")
        st.markdown(f"**Contact No.:** {info.get('contact_no', '-')}")
    with col2:
        st.markdown(f"**Course:** {info.get('course', '-')}")
        st.markdown(f"**City:** {info.get('city', '-')}")
        st.markdown(f"**Father's Name:** {info.get('father_name', '-')}")
        st.markdown(f"**Mother's Name:** {info.get('mother_name', '-')}")
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------------------------
# st.radio in the sidebar acts as a simple page router — whatever option is
# selected decides which block of code below actually renders.
page = st.sidebar.radio(
    "Navigate",
    ["View All Students", "Add Student", "Update Student", "Delete Student", "Get Student"],
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Connected to: `{BASE_URL}`")

# ---------------------------------------------------------------------------
# PAGE: VIEW ALL STUDENTS  ->  GET /view
# ---------------------------------------------------------------------------
if page == "View All Students":
    st.subheader("📋 All Students")

    if st.button("Refresh List"):
        st.rerun()

    ok, data = api_call("GET", "/view")

    if not ok:
        st.error(data)
    elif not data:
        st.info("No students found yet. Add one from the 'Add Student' page.")
    else:
        # data is a dict of {enroll: {student fields}}
        for enroll, info in data.items():
            with st.expander(f"{info.get('name', 'Unknown')} — {enroll}"):
                render_student_card(enroll, info)

# ---------------------------------------------------------------------------
# PAGE: GET STUDENT  ->  GET /student/{student_enroll}
# ---------------------------------------------------------------------------
elif page == "Get Student":
    st.subheader("Look Up a Student")

    enroll = st.text_input("Enrollment No.", placeholder="e.g. LNCFBTC00001")

    if st.button("Search"):
        if not enroll.strip():
            st.warning("Please enter an enrollment number.")
        else:
            ok, data = api_call("GET", f"/student/{enroll.strip()}")
            if ok:
                render_student_card(enroll.strip(), data)
            else:
                st.error(data)

# ---------------------------------------------------------------------------
# PAGE: ADD STUDENT  ->  POST /add
# ---------------------------------------------------------------------------
elif page == "Add Student":
    st.subheader("Add a New Student")

    # st.form batches all inputs together so the API is only called once,
    # on submit — not on every keystroke/widget interaction.
    with st.form("add_student_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            enroll = st.text_input("Enrollment No.*", placeholder="LNCFBTC00001")
            roll_no = st.text_input("Roll No.*", placeholder="001")
            name = st.text_input("Student's Name*")
            age = st.number_input("Age*", min_value=1, max_value=29, step=1)
            gender = st.selectbox("Gender*", ["Male", "Female", "Others"])
        with col2:
            contact_no = st.text_input("Contact No.*", placeholder="1234567890")
            father_name = st.text_input("Father's Name*")
            mother_name = st.text_input("Mother's Name*")
            course = st.text_input("Course*", placeholder="B.Tech")#,,,
            city = st.text_input("City*")

        submitted = st.form_submit_button("Add Student")

    if submitted:
        # Basic client-side check before hitting the API — the backend
        # still validates everything via Pydantic regardless.
        required = [enroll, roll_no, name, contact_no, father_name, mother_name, course, city]
        if not all(field.strip() for field in required):
            st.warning("Please fill in all required (*) fields.")
        elif not contact_no.strip().isdigit():
            st.warning("Contact No. must contain digits only.")
        else:
            payload = {
                "enroll": enroll.strip(),
                "roll_no": roll_no.strip(),
                "name": name.strip(),
                "age": int(age),
                "gender": gender,
                "contact_no": int(contact_no.strip()),
                "father_name": father_name.strip(),
                "mother_name": mother_name.strip(),
                "course": course.strip(),
                "city": city.strip(),
            }
            ok, data = api_call("POST", "/add", json=payload)
            if ok:
                st.success(data.get("message", "Student added."))
            else:
                st.error(data)

# ---------------------------------------------------------------------------
# PAGE: UPDATE STUDENT  ->  PUT /edit/{student_enroll}
# ---------------------------------------------------------------------------
elif page == "Update Student":
    st.subheader("Update a Student")

    enroll = st.text_input("Enrollment No. of student to update*", placeholder="LNCFBTC00001")

    # Leaving a field blank means "don't change it" — matches StudentUpdate,
    # where every field is Optional and defaults to None (excluded via
    # exclude_unset on the backend).
    st.caption("Leave a field empty to keep its current value unchanged.")

    with st.form("update_student_form"):
        col1, col2 = st.columns(2)
        with col1:
            roll_no = st.text_input("Roll No.")
            name = st.text_input("Student's Name")
            age = st.text_input("Age", placeholder="leave blank to skip")
            gender = st.selectbox("Gender", ["(no change)", "Male", "Female", "Others"])
        with col2:
            contact_no = st.text_input("Contact No.", placeholder="leave blank to skip")
            father_name = st.text_input("Father's Name")
            mother_name = st.text_input("Mother's Name")
            course = st.text_input("Course")
            city = st.text_input("City")

        submitted = st.form_submit_button("Update Student")

    if submitted:
        if not enroll.strip():
            st.warning("Please enter the enrollment number of the student to update.")
        else:
            # Only include fields the user actually typed something into.
            # This mirrors `exclude_unset=True` on the backend's StudentUpdate.
            payload = {}
            if roll_no.strip():
                payload["roll_no"] = roll_no.strip()
            if name.strip():
                payload["name"] = name.strip()
            if age.strip():
                if not age.strip().isdigit():
                    st.warning("Age must be a number.")
                else:
                    payload["age"] = int(age.strip())
            if gender != "(no change)":
                payload["gender"] = gender
            if contact_no.strip():
                if not contact_no.strip().isdigit():
                    st.warning("Contact No. must be a number.")
                else:
                    payload["contact_no"] = int(contact_no.strip())
            if father_name.strip():
                payload["father_name"] = father_name.strip()
            if mother_name.strip():
                payload["mother_name"] = mother_name.strip()
            if course.strip():
                payload["course"] = course.strip()
            if city.strip():
                payload["city"] = city.strip()

            if not payload:
                st.warning("You didn't change anything.")
            else:
                ok, data = api_call("PUT", f"/edit/{enroll.strip()}", json=payload)
                if ok:
                    st.success(data.get("message", "Student updated."))
                else:
                    st.error(data)

# ---------------------------------------------------------------------------
# PAGE: DELETE STUDENT  ->  DELETE /delete/{student_enroll}
# ---------------------------------------------------------------------------
elif page == "Delete Student":
    st.subheader("Delete a Student")

    enroll = st.text_input("Enrollment No. of student to delete*", placeholder="LNCFBTC00001")

    # A checkbox as a lightweight "are you sure" guard, since deletes are
    # irreversible and there's no undo on the backend.
    confirm = st.checkbox("I understand this action cannot be undone.")

    if st.button("Delete Student", disabled=not confirm):
        if not enroll.strip():
            st.warning("Please enter an enrollment number.")
        else:
            ok, data = api_call("DELETE", f"/delete/{enroll.strip()}")
            if ok:
                st.success(data.get("message", "Student deleted."))
            else:
                st.error(data)
