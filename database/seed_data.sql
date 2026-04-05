-- ============================================================================
-- Module M45: Reference Range Validation Database
-- SEED DATA — Realistic sample data for demonstration
-- Run AFTER schema.sql
-- ============================================================================

-- ─── PATIENTS (diverse ages, sex, ethnicity) ────────────────────────────────
INSERT INTO patient (dob, sex, ethnicity) VALUES
    ('1990-05-15', 'Female', 'Asian'),        -- ID 1: ~35 yr female
    ('1985-08-22', 'Male',   'Caucasian'),    -- ID 2: ~40 yr male
    ('2000-11-03', 'Female', 'Hispanic'),     -- ID 3: ~25 yr female (pregnant scenario)
    ('1960-02-14', 'Male',   'African'),      -- ID 4: ~65 yr male (senior)
    ('2018-07-30', 'Female', 'Asian'),        -- ID 5: ~7 yr child
    ('1975-01-20', 'Male',   'Caucasian'),    -- ID 6: ~50 yr male
    ('1995-09-10', 'Female', 'African'),      -- ID 7: ~30 yr female
    ('2010-04-25', 'Male',   'Hispanic');     -- ID 8: ~15 yr teen male

-- ─── METHODS (common lab instruments) ───────────────────────────────────────
INSERT INTO method (instrument, reagent, technique) VALUES
    ('Beckman Coulter DxH 900',   'Coulter Reagent',     'Impedance / Flow Cytometry'),   -- ID 1: Hematology
    ('Roche Cobas c702',          'Roche Glucose HK',    'Spectrophotometry'),             -- ID 2: Chemistry
    ('Siemens Atellica IM',       'Siemens TSH Reagent', 'Chemiluminescence'),             -- ID 3: Immunoassay
    ('Abbott Alinity ci',         'Abbott Reagent Pack',  'CMIA'),                          -- ID 4: Multi-analyte
    ('Sysmex XN-1000',            'Sysmex Reagent',      'Fluorescence Flow Cytometry');   -- ID 5: Hematology

-- ─── LAB TESTS ──────────────────────────────────────────────────────────────
INSERT INTO lab_test (test_name) VALUES
    ('Hemoglobin'),                 -- ID 1
    ('Fasting Blood Glucose'),      -- ID 2
    ('Thyroid Stimulating Hormone'),-- ID 3 (TSH)
    ('Serum Creatinine'),           -- ID 4
    ('Total Cholesterol'),          -- ID 5
    ('White Blood Cell Count'),     -- ID 6 (WBC)
    ('Platelet Count'),             -- ID 7
    ('Serum Potassium'),            -- ID 8
    ('Alanine Transaminase'),       -- ID 9 (ALT)
    ('Blood Urea Nitrogen');        -- ID 10 (BUN)

-- ─── CONDITIONS ─────────────────────────────────────────────────────────────
INSERT INTO condition (condition_name) VALUES
    ('Pregnancy'),          -- ID 1
    ('Diabetes'),           -- ID 2
    ('Chronic Kidney Disease'), -- ID 3
    ('Hyperthyroidism'),    -- ID 4
    ('Anemia');             -- ID 5

-- ─── REFERENCE RANGES (medically accurate values) ──────────────────────────
-- Hemoglobin (g/dL) — Method 1 (Hematology Analyzer)
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (1, 1, 'Male',   18, 65,  13.5,  17.5,  7.0,  20.0, NULL, '2025-01-01'),
    (1, 1, 'Female', 18, 65,  12.0,  16.0,  7.0,  20.0, NULL, '2025-01-01'),
    (1, 1, 'Male',   0,  17,  11.0,  16.0,  7.0,  20.0, NULL, '2025-01-01'),
    (1, 1, 'Female', 0,  17,  11.0,  15.0,  7.0,  20.0, NULL, '2025-01-01'),
    (1, 1, 'Both',   66, 120, 11.5,  16.5,  7.0,  20.0, NULL, '2025-01-01');

-- Fasting Blood Glucose (mg/dL) — Method 2 (Chemistry Analyzer)
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (2, 2, 'Both', 18, 120, 70.0, 100.0, 40.0, 400.0, NULL, '2025-01-01'),
    (2, 2, 'Both', 0,  17,  60.0, 100.0, 40.0, 400.0, NULL, '2025-01-01');

-- TSH (mIU/L) — Method 3 (Immunoassay)
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (3, 3, 'Both', 18, 120, 0.4,  4.0,   0.1,  10.0, NULL, '2025-01-01'),
    (3, 3, 'Both', 0,  17,  0.7,  6.4,   0.1,  15.0, NULL, '2025-01-01');

-- Serum Creatinine (mg/dL) — Method 2
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (4, 2, 'Male',   18, 120, 0.7,  1.3,  0.2, 10.0, NULL, '2025-01-01'),
    (4, 2, 'Female', 18, 120, 0.6,  1.1,  0.2, 10.0, NULL, '2025-01-01');

-- Total Cholesterol (mg/dL) — Method 2
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (5, 2, 'Both', 18, 120, 125.0, 200.0, 100.0, 400.0, NULL, '2025-01-01');

-- WBC (×10³/µL) — Method 1
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (6, 1, 'Both', 18, 120, 4.5,  11.0,  2.0,  30.0, NULL, '2025-01-01'),
    (6, 1, 'Both', 0,  17,  5.0,  13.0,  2.0,  30.0, NULL, '2025-01-01');

-- Platelet Count (×10³/µL) — Method 5
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (7, 5, 'Both', 0, 120, 150.0, 400.0, 50.0, 1000.0, NULL, '2025-01-01');

-- Serum Potassium (mEq/L) — Method 4
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (8, 4, 'Both', 18, 120, 3.5, 5.0, 2.5, 6.5, NULL, '2025-01-01');

-- ALT (U/L) — Method 2
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (9, 2, 'Male',   18, 120, 7.0,  56.0, 0.0, 1000.0, NULL, '2025-01-01'),
    (9, 2, 'Female', 18, 120, 7.0,  45.0, 0.0, 1000.0, NULL, '2025-01-01');

-- BUN (mg/dL) — Method 2
INSERT INTO reference_range (test_id, method_id, sex, min_age, max_age, lower_limit, upper_limit, critical_low, critical_high, ethnicity, date) VALUES
    (10, 2, 'Both', 18, 120, 7.0, 20.0, 2.0, 100.0, NULL, '2025-01-01');

-- ─── RANGE ADJUSTMENTS ─────────────────────────────────────────────────────
-- Pregnancy adjusts Hemoglobin lower (multiplier 0.85 = 15% decrease in limits)
INSERT INTO range_adjustment (range_id, condition_id, adjustment_type, adjustment_value) VALUES
    (2, 1, 'Multiplier', 0.85);  -- Female Hgb range_id=2,  Pregnancy condition_id=1

-- Pregnancy adjusts TSH range (first trimester: lower limits)
INSERT INTO range_adjustment (range_id, condition_id, adjustment_type, adjustment_value) VALUES
    (9, 1, 'Multiplier', 0.75);  -- TSH adult range_id=9, Pregnancy

-- Diabetes shifts Glucose upper limit up by +26 mg/dL
INSERT INTO range_adjustment (range_id, condition_id, adjustment_type, adjustment_value) VALUES
    (6, 2, 'Absolute', 26.0);    -- Glucose adult range_id=6, Diabetes condition_id=2

-- CKD shifts Creatinine upper limit up by +0.5 mg/dL
INSERT INTO range_adjustment (range_id, condition_id, adjustment_type, adjustment_value) VALUES
    (11, 3, 'Absolute', 0.5);    -- Male Creatinine range_id=11, CKD condition_id=3

-- Pregnancy adjusts WBC (higher normal in pregnancy, multiplier 1.15)
INSERT INTO range_adjustment (range_id, condition_id, adjustment_type, adjustment_value) VALUES
    (14, 1, 'Multiplier', 1.15); -- WBC adult range_id=14, Pregnancy

-- ─── SAMPLE TEST RESULTS (inserted AFTER triggers are created) ─────────────
-- NOTE: Do NOT run these until triggers.sql has been executed!
-- They are placed here for reference. Run them via the application or manually.

-- Normal result: Male, Hemoglobin = 15.2
-- INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
--     VALUES (2, 1, 1, 15.2, FALSE);

-- Abnormal result: Female, Hemoglobin = 11.0 (below 12.0 lower limit)
-- INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
--     VALUES (1, 1, 1, 11.0, FALSE);

-- Critical result: Male, Glucose = 450 (above 400 critical high)
-- INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
--     VALUES (2, 2, 2, 450.0, FALSE);

-- Pregnant female, Hemoglobin = 10.5 (normal with pregnancy adjustment)
-- INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
--     VALUES (3, 1, 1, 10.5, TRUE);

-- Added by Tushar: Additional condition for future scaling
INSERT INTO condition (condition_name) VALUES ('Hypertension');