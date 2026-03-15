# Project Context: Module 45 - Reference Range Validation Database
You are an expert full-stack Python developer and database architect helping me build a university DBMS Mini-Project. 
**Crucial Constraint:** This is a Database Management Systems course project. The logic MUST live in the database. DO NOT use Machine Learning. Validation logic must be handled via SQL Queries, Views, Triggers, and Stored Procedures.

## Tech Stack
* **Database:** PostgreSQL (Neon)
* **Backend API:** Python with FastAPI & `psycopg2` (or SQLAlchemy)
* **Frontend UI:** Python with Streamlit (must integrate seamlessly into an existing Streamlit multi-page app)

## 1. Database Schema Requirements (Based on my ER Diagram)
Write the complete PostgreSQL `schema.sql` file (DDL). Use standard naming conventions. I have an ER diagram with the following entities:
1. `PATIENT`: `patient_id`, `dob`, `sex`, `ethnicity`.
2. `METHOD`: `method_id`, `instrument`, `reagent`, `technique`.
3. `LAB_TEST`: `test_id`, `test_name`.
4. `CONDITION`: `condition_id`, `condition_name` (e.g., Pregnancy, Diabetic).
5. `REFERENCE_RANGE`: `range_id`, `test_id` (FK), `method_id` (FK), `sex`, `min_age`, `max_age`, `lower_limit`, `upper_limit`, `critical_low`, `critical_high`.
6. `RANGE_ADJUSTMENT`: `adj_id`, `range_id` (FK), `condition_id` (FK), `adjustment_type` (Multiplier/Absolute), `adjustment_value`.
7. `TEST_RESULT`: `result_id`, `patient_id` (FK), `test_id` (FK), `measured_value`, `time`, `pregnancy_status`, `validated_against_range` (FK to Reference Range).
8. `QC_ALERT`: `alert_id`, `result_id` (FK), `type`, `time`, `severity`.

## 2. Required Database Logic (Procedural SQL)
Generate the SQL for the following exactly as requested to get full marks:
* **Function/Procedure (`calculate_effective_range`):** Given a patient and a test, find the base `REFERENCE_RANGE`. If the patient has a `CONDITION` (like pregnancy), apply the `RANGE_ADJUSTMENT` math to calculate the true safe limits.
* **Trigger (`trg_validate_result`):** An `AFTER INSERT` trigger on `TEST_RESULT`. It must call the procedure above. If `measured_value` falls outside the effective normal limits, insert a row into `QC_ALERT` with severity (e.g., 'Abnormal' or 'Critical').
* **View (`vw_critical_patient_alerts`):** A view joining Patient, Lab Test, Test Result, and QC Alert to display a dashboard-ready table of critical alerts.

## 3. Backend API Requirements (FastAPI)
Create a `main.py` using FastAPI with endpoints to:
* `GET /api/ranges/{test_id}`: Fetch reference ranges.
* `POST /api/results`: Submit a new lab result (trigger handles the rest).
* `GET /api/alerts`: Fetch data from `vw_critical_patient_alerts`.

## 4. Frontend Requirements (Streamlit)
Write a `dashboard.py` file that can act as a page in a broader Streamlit app. It should have:
* **Form:** To input a new Lab Result (Patient ID, Test, Value, Conditions).
* **Dataframe/Table:** Showing `vw_critical_patient_alerts` with conditional formatting (highlighting critical rows in red).

**Execution Instructions:**
Output the files in this order:
1. `database/schema.sql`
2. `backend/main.py`
3. `frontend/dashboard.py`
Add ample comments explaining the DBMS concepts (Triggers, Views, Constraints) used.