# Module M45 — Reference Range Validation Database

A DBMS Mini-Project module for a university course. All validation logic lives in PostgreSQL (no ML). The module validates lab test results against age/sex/method-specific reference ranges, applies condition-based adjustments (e.g., pregnancy), and generates QC alerts for abnormal/critical values.

## User Review Required

> [!IMPORTANT]
> **Neon PostgreSQL Connection**: I'll need you to provide the Neon database connection string (host, database name, user, password) so the backend and frontend can connect. I'll use a `.env` file or `st.secrets` pattern — you can fill in creds after.

> [!IMPORTANT]
> **Seed Data**: I'll create realistic seed data (common lab tests like CBC, BMP, Lipid Panel with medically accurate reference ranges). Let me know if you have specific tests you want included.

---

## Proposed Changes

### Database Layer (`database/`)

#### [NEW] [schema.sql](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/database/schema.sql)
Complete DDL for all 8 tables — **matching your ER diagram exactly**:
- [patient](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-%28Winter%29/DBMS/H45%20Project/medical-copilot-frontend/dashboards/patient_dashboard.py#132-168) — patient_id (PK), dob, sex, ethnicity
- `method` — method_id (PK), instrument, reagent, technique
- `lab_test` — test_id (PK), test_name
- `condition` — condition_id (PK), condition_name
- `reference_range` — range_id (PK), test_id (FK→lab_test), method_id (FK→method), sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, **ethnicity**, **date** *(from your ER diagram)*
- `range_adjustment` — adj_id (PK, *added for practical use*), range_id (FK→reference_range), condition_id (FK→condition), adjustment_type, adjustment_value
- `test_result` — result_id (PK), patient_id (FK→patient), test_id (FK→lab_test), measured_value, time, pregnancy_status, validated_against_range (FK→reference_range)
- `qc_alert` — alert_id (PK), result_id (FK→test_result), type, time, severity

**Relationships (from ER diagram):**
| Relationship | Cardinality |
|---|---|
| PATIENT → TEST_RESULT (HAS) | 1 : N |
| LAB_TEST → TEST_RESULT (YIELDS) | 1 : N |
| LAB_TEST → REFERENCE_RANGE (DEFINES) | 1 : N |
| METHOD → REFERENCE_RANGE (UTILIZED_BY) | 1 : N |
| REFERENCE_RANGE → TEST_RESULT (VALIDATED_AGAINST) | 1 : N |
| REFERENCE_RANGE → RANGE_ADJUSTMENT (HAS_ADJUSTMENT) | 1 : N |
| CONDITION → RANGE_ADJUSTMENT (CAUSED_BY) | 1 : N |
| TEST_RESULT → QC_ALERT (TRIGGERS) | 1 : N |

Includes `CHECK` constraints, `NOT NULL` where appropriate, and proper FK relationships.

#### [NEW] [seed_data.sql](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/database/seed_data.sql)
Realistic sample data: patients of varying ages/sex, common lab tests (Hemoglobin, Glucose, Creatinine, TSH, etc.), reference ranges with medically accurate values, conditions (Pregnancy, Diabetes), and sample test results that trigger both normal and abnormal alerts.

#### [NEW] [procedures.sql](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/database/procedures.sql)
`calculate_effective_range(p_patient_id, p_test_id, p_method_id)` — PostgreSQL function that:
1. Looks up the patient's age (from dob) and sex
2. Finds the matching `reference_range` row
3. Checks if patient has active conditions via `test_result.pregnancy_status` or a patient-condition link
4. Applies `range_adjustment` math (Multiplier or Absolute) to get effective lower/upper limits
5. Returns: range_id, effective_lower, effective_upper, critical_low, critical_high

#### [NEW] [triggers.sql](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/database/triggers.sql)
`trg_validate_result` — AFTER INSERT trigger on `test_result`:
1. Calls `calculate_effective_range` for the inserted row's patient + test
2. Compares `measured_value` against effective limits
3. If outside critical_low/critical_high → inserts `qc_alert` with severity 'Critical'
4. If outside lower/upper but within critical → inserts `qc_alert` with severity 'Abnormal'
5. Updates `validated_against_range` FK on the test_result

#### [NEW] [views.sql](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/database/views.sql)
`vw_critical_patient_alerts` — Joins patient, lab_test, test_result, qc_alert, and reference_range to show a dashboard-ready table with: patient info, test name, measured value, expected range, alert type, severity, timestamp.

---

### Backend API (`backend/`)

#### [NEW] [main.py](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/backend/main.py)
FastAPI application with `psycopg2` direct connections:
- `GET /api/ranges/{test_id}` — Fetch all reference ranges for a given test
- `POST /api/results` — Submit a new lab result (patient_id, test_id, measured_value, method_id, pregnancy_status). The DB trigger handles validation automatically.
- `GET /api/alerts` — Fetch rows from `vw_critical_patient_alerts`
- `GET /api/patients` — List patients for dropdowns
- `GET /api/tests` — List lab tests for dropdowns

Includes CORS middleware and proper error handling.

#### [NEW] [requirements.txt](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/backend/requirements.txt)
Dependencies: `fastapi`, `uvicorn`, `psycopg2-binary`, `python-dotenv`

#### [NEW] [.env.example](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/backend/.env.example)
Template for DB connection creds (you fill in your Neon values).

---

### Frontend Integration (`frontend/`)

#### [NEW] [dashboard.py](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/frontend/dashboard.py)
Streamlit page with 3 sections:
1. **Submit Lab Result Form**: Patient dropdown, Test dropdown, Value input, Method selection, Pregnancy status toggle. Calls the backend API on submit.
2. **Critical Alerts Dashboard**: Table from `vw_critical_patient_alerts` with red highlighting for 'Critical' rows and yellow for 'Abnormal'.
3. **Reference Ranges Viewer**: Select a test → see all reference ranges with age/sex breakdown.

#### [NEW] [db_connection.py](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/frontend/db_connection.py)
Helper for direct psycopg2 connection from Streamlit (reads creds from `st.secrets` or `.env`).

---

### Existing File Modifications

#### [MODIFY] [doctor_dashboard.py](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/dashboards/doctor_dashboard.py)
Update [show_module_detail()](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-%28Winter%29/DBMS/H45%20Project/medical-copilot-frontend/dashboards/patient_dashboard.py#360-452) to detect when the selected module is B3 (Reference Range Validation) and render the real `frontend/dashboard.py` content instead of the generic placeholder.

#### [MODIFY] [patient_dashboard.py](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/dashboards/patient_dashboard.py)
Same as above — detect H3 module and render the real dashboard.

#### [MODIFY] [requirements.txt](file:///c:/Users/dines/Desktop/00_IIT%20ISM%20Academic%20Files/00_2025_Sem_4-(Winter)/DBMS/H45%20Project/medical-copilot-frontend/requirements.txt)
Add `psycopg2-binary`, `python-dotenv`, `requests`, `pandas` (for the Streamlit frontend to call the API and display data).

---

## Verification Plan

### Database Verification
- Run the SQL files in sequence on Neon: `schema.sql` → `seed_data.sql` → `procedures.sql` → `triggers.sql` → `views.sql`
- Insert a test result manually and verify the trigger creates a `qc_alert`
- Query `vw_critical_patient_alerts` to verify the view works

### Manual Verification (User)
1. After I create all files, you run the SQL files on your Neon database
2. Start the FastAPI backend: `cd backend && uvicorn main:app --reload`
3. Test endpoints via browser: `/docs` (Swagger UI)
4. Start the Streamlit app: `streamlit run app.py`
5. Navigate to Category H → Module H3 and verify the real dashboard loads
6. Submit a lab result and check that alerts appear in the table
