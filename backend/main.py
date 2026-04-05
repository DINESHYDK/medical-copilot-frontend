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

# ── GET / — Deep Health Check ───────────────────────────────────────────────
@app.get("/")
def root():
    """
    Enhanced health check endpoint that actively pings the database.
    Demonstrates: Validating live database connectivity.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS db_is_alive")
            db_status = cur.fetchone()
            
        return {
            "status": "ok", 
            "database_connected": bool(db_status),
            "module": "M45 - Reference Range Validation"
        }
    except Exception as e:
        return {"status": "error", "database_connected": False, "detail": str(e)}
    finally:
        if 'conn' in locals() and conn:
            conn.close()


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

# ── GET /api/patients/{patient_id}/results — Patient History ────────────────
@app.get("/api/patients/{patient_id}/results")
def get_patient_results(patient_id: int):
    """
    Fetch all historical lab results for a specific patient.
    Demonstrates: Multi-table JOINs and ordering by time for historical tracking.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tr.result_id, tr.measured_value, tr.timestamp, 
                       lt.test_name, m.instrument, qa.severity
                FROM test_result tr
                JOIN lab_test lt ON tr.test_id = lt.test_id
                JOIN method m ON tr.method_id = m.method_id
                LEFT JOIN qc_alert qa ON tr.result_id = qa.result_id
                WHERE tr.patient_id = %s
                ORDER BY tr.timestamp DESC
            """, (patient_id,))
            results = cur.fetchall()
            
        if not results:
            raise HTTPException(status_code=404, detail="No results found for this patient.")
            
        return {"patient_id": patient_id, "history": results}
    finally:
        conn.close()

# ── GET /api/stats/dashboard — System-wide aggregates ───────────────────────
@app.get("/api/stats/dashboard")
def get_dashboard_stats():
    """
    Fetch high-level aggregate statistics for a frontend dashboard.
    Demonstrates: Using SQL aggregate functions (COUNT) to reduce payload size.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get total tests performed
            cur.execute("SELECT COUNT(*) as total_tests FROM test_result")
            total_tests = cur.fetchone()["total_tests"]
            
            # Get total critical alerts
            cur.execute("SELECT COUNT(*) as total_critical FROM qc_alert WHERE severity = 'Critical'")
            total_critical = cur.fetchone()["total_critical"]
            
            # Get total patients
            cur.execute("SELECT COUNT(*) as total_patients FROM patient")
            total_patients = cur.fetchone()["total_patients"]

        return {
            "total_patients": total_patients,
            "total_tests_run": total_tests,
            "critical_alerts_count": total_critical
        }
    finally:
        conn.close()

