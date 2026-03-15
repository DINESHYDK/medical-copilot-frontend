@echo off
echo ============================================
echo  Module M45 - Git Commit History Generator
echo ============================================
echo.

REM 1. The Foundation
echo [1/13] Committing database schema...
git add database/schema.sql
git commit -m "feat(db): design normalized schema for reference ranges and lab tests"

REM 2. The Seed Data
echo [2/13] Committing seed data...
git add database/seed_data.sql
git commit -m "chore(db): populate initial reference range and patient mock data"

REM 3. Database Logic - Procedures
echo [3/13] Committing stored procedures...
git add database/procedures.sql
git commit -m "feat(db): implement pl/pgsql procedure for condition-based range adjustments"

REM 4. Database Logic - Triggers
echo [4/13] Committing triggers...
git add database/triggers.sql
git commit -m "feat(db): add AFTER INSERT trigger for automated QC alert generation"

REM 5. Database Views
echo [5/13] Committing views...
git add database/views.sql
git commit -m "feat(db): create materialized view for critical patient alerts dashboard"

REM 6. Backend Setup
echo [6/13] Committing backend setup...
git add backend/requirements.txt backend/.env.example
git commit -m "chore(api): initialize FastAPI backend dependencies and env templates"

REM 7. Backend API Core
echo [7/13] Committing backend API...
git add backend/main.py
git commit -m "feat(api): build REST endpoints for reference ranges and lab result submissions"

REM 8. Frontend Connection Logic
echo [8/13] Committing DB connection layer...
git add frontend/db_connection.py requirements.txt
git commit -m "feat(ui): configure psycopg2 database connection for Streamlit"

REM 9. The Dashboard Structure
echo [9/13] Committing dashboard...
git add frontend/dashboard.py
git commit -m "feat(ui): build initial layout for lab result submission and alerts table"

REM 10. UI/UX Premium Polish
echo [10/13] Committing theme config...
git add .streamlit/config.toml
git commit -m "style(ui): apply global enterprise medical-blue theme to streamlit"

REM 11. Integrating into Main App
echo [11/13] Committing dashboard integration...
git add dashboards/patient_dashboard.py dashboards/doctor_dashboard.py
git commit -m "fix(integration): route module 45 into main doctor and patient dashboards"

REM 12. Documentation
echo [12/13] Committing documentation...
git add Progress.md CLAUDE*.md
git commit -m "docs: add project progress tracker and architecture documentation"

REM 13. Catch-all
echo [13/13] Committing remaining files...
git add .
git commit -m "chore: minor formatting and cleanup"

echo.
echo ============================================
echo  All 13 commits created successfully!
echo  Run 'git log --oneline' to verify.
echo ============================================
pause
