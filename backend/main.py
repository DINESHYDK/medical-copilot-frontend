# ============================================================================
# Module M45: Reference Range Validation Database
# Backend API — FastAPI with psycopg2 (direct PostgreSQL connection)
# ============================================================================
# DBMS Concepts Demonstrated:
#   • Direct SQL queries from application layer
#   • Connection pooling via psycopg2
#   • Parameterised queries (SQL injection prevention)
#   • Calling stored functions from application
#   • Reading from views (vw_critical_patient_alerts)
#   • Transaction management (auto-commit for inserts that trigger DB logic)
# ============================================================================

import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables from .env file
load_dotenv()

# ─── App Initialization ─────────────────────────────────────────────────────
app = FastAPI(
    title="M45 Reference Range Validation API",
    description="Backend API for Lab Test Reference Range Validation — DBMS Mini Project",
    version="1.0.0"
)

# CORS — allow Streamlit frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Database Connection ────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")

def get_db_connection():
    """Create a new database connection using the Neon PostgreSQL connection string."""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        conn.autocommit = True  # Important: triggers fire on commit
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


# ─── Pydantic Models (Request/Response schemas) ─────────────────────────────
class LabResultSubmit(BaseModel):
    """Schema for submitting a new lab test result."""
    patient_id: int
    test_id: int
    method_id: int
    measured_value: float
    pregnancy_status: bool = False


class LabResultResponse(BaseModel):
    """Response after submitting a lab result."""
    result_id: int
    message: str
    alert: Optional[dict] = None


# ─── ENDPOINTS ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "module": "M45 - Reference Range Validation"}


# ── GET /api/patients — List all patients (for dropdowns) ───────────────────
@app.get("/api/patients")
def get_patients():
    """Fetch all patients for the frontend dropdown."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT patient_id, dob, sex, ethnicity,
                       EXTRACT(YEAR FROM AGE(CURRENT_DATE, dob))::INT AS age
                FROM patient
                ORDER BY patient_id
            """)
            patients = cur.fetchall()
        return {"patients": patients}
    finally:
        conn.close()


# ── GET /api/tests — List all lab tests (for dropdowns) ─────────────────────
@app.get("/api/tests")
def get_tests():
    """Fetch all lab tests for the frontend dropdown."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT test_id, test_name FROM lab_test ORDER BY test_id")
            tests = cur.fetchall()
        return {"tests": tests}
    finally:
        conn.close()


# ── GET /api/methods — List all methods (for dropdowns) ─────────────────────
@app.get("/api/methods")
def get_methods():
    """Fetch all lab methods for the frontend dropdown."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT method_id, instrument, reagent, technique
                FROM method
                ORDER BY method_id
            """)
            methods = cur.fetchall()
        return {"methods": methods}
    finally:
        conn.close()


# ── GET /api/ranges/{test_id} — Fetch reference ranges for a test ───────────
@app.get("/api/ranges/{test_id}")
def get_reference_ranges(test_id: int):
    """
    Fetch all reference ranges for a given lab test.
    Demonstrates: SQL SELECT with JOIN, parameterised query.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT rr.range_id, rr.sex, rr.min_age, rr.max_age,
                       rr.lower_limit, rr.upper_limit,
                       rr.critical_low, rr.critical_high,
                       rr.ethnicity, rr.date,
                       m.instrument, m.technique,
                       lt.test_name
                FROM reference_range rr
                JOIN method m ON m.method_id = rr.method_id
                JOIN lab_test lt ON lt.test_id = rr.test_id
                WHERE rr.test_id = %s
                ORDER BY rr.sex, rr.min_age
            """, (test_id,))
            ranges = cur.fetchall()

        if not ranges:
            raise HTTPException(status_code=404, detail=f"No reference ranges found for test_id={test_id}")

        return {"test_id": test_id, "ranges": ranges}
    finally:
        conn.close()


# ── POST /api/results — Submit a new lab result ─────────────────────────────
@app.post("/api/results")
def submit_result(data: LabResultSubmit):
    """
    Submit a new lab test result.
    The database trigger (trg_validate_result) automatically:
      1. Calls calculate_effective_range()
      2. Compares value against limits
      3. Inserts a QC alert row
    Demonstrates: INSERT triggering stored procedure via trigger.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Insert the test result — trigger fires automatically
            cur.execute("""
                INSERT INTO test_result
                    (patient_id, test_id, method_id, measured_value, pregnancy_status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING result_id
            """, (
                data.patient_id,
                data.test_id,
                data.method_id,
                data.measured_value,
                data.pregnancy_status
            ))
            result = cur.fetchone()
            result_id = result["result_id"]

            # Fetch the alert that was auto-generated by the trigger
            cur.execute("""
                SELECT alert_id, type, severity, time
                FROM qc_alert
                WHERE result_id = %s
                ORDER BY alert_id DESC
                LIMIT 1
            """, (result_id,))
            alert = cur.fetchone()

        return {
            "result_id": result_id,
            "message": "Lab result submitted and validated successfully",
            "alert": dict(alert) if alert else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


# ── GET /api/alerts — Fetch data from vw_critical_patient_alerts ────────────
@app.get("/api/alerts")
def get_alerts(severity: Optional[str] = None):
    """
    Fetch alerts from the vw_critical_patient_alerts VIEW.
    Optionally filter by severity (Critical, Abnormal, Normal).
    Demonstrates: Reading from a database VIEW.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if severity:
                cur.execute("""
                    SELECT * FROM vw_critical_patient_alerts
                    WHERE alert_severity = %s
                """, (severity,))
            else:
                cur.execute("SELECT * FROM vw_critical_patient_alerts")
            alerts = cur.fetchall()

        return {"total": len(alerts), "alerts": alerts}
    finally:
        conn.close()


# ── GET /api/conditions — List all conditions ───────────────────────────────
@app.get("/api/conditions")
def get_conditions():
    """Fetch all medical conditions."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT condition_id, condition_name FROM condition ORDER BY condition_id")
            conditions = cur.fetchall()
        return {"conditions": conditions}
    finally:
        conn.close()
