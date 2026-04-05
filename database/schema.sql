-- ============================================================================
-- Module M45: Reference Range Validation Database
-- DDL Schema — PostgreSQL (Neon)
-- ============================================================================
-- DBMS Concepts Used:
--   • PRIMARY KEY constraints for entity integrity
--   • FOREIGN KEY constraints for referential integrity
--   • CHECK constraints for domain integrity
--   • NOT NULL constraints for mandatory attributes
--   • SERIAL / GENERATED ALWAYS for auto-increment IDs
--   • ENUM-like CHECK for restricted value sets
-- ============================================================================

-- 1. PATIENT — stores patient demographics
-- Cardinality: PATIENT (1) → TEST_RESULT (N)
CREATE TABLE patient (
    patient_id   SERIAL PRIMARY KEY,
    dob          DATE        NOT NULL,
    sex          VARCHAR(10) NOT NULL CHECK (sex IN ('Male', 'Female', 'Other')),
    ethnicity    VARCHAR(50)
);

COMMENT ON TABLE patient IS 'Core patient demographics — age derived from dob at query time';

-- 2. METHOD — lab analysis method / instrument used
-- Cardinality: METHOD (1) → REFERENCE_RANGE (N)
CREATE TABLE method (
    method_id    SERIAL PRIMARY KEY,
    instrument   VARCHAR(100) NOT NULL,
    reagent      VARCHAR(100),
    technique    VARCHAR(100) NOT NULL
);

COMMENT ON TABLE method IS 'Analytical method defines instrument + reagent + technique combination';

-- 3. LAB_TEST — catalogue of laboratory tests
-- Cardinality: LAB_TEST (1) → TEST_RESULT (N), LAB_TEST (1) → REFERENCE_RANGE (N)
CREATE TABLE lab_test (
    test_id      SERIAL PRIMARY KEY,
    test_name    VARCHAR(150) NOT NULL UNIQUE
);

COMMENT ON TABLE lab_test IS 'Master list of lab tests (e.g. Hemoglobin, Glucose, TSH)';

-- 4. CONDITION — medical conditions that alter reference ranges
-- Cardinality: CONDITION (1) → RANGE_ADJUSTMENT (N)
CREATE TABLE condition (
    condition_id   SERIAL PRIMARY KEY,
    condition_name VARCHAR(100) NOT NULL UNIQUE
);

COMMENT ON TABLE condition IS 'Conditions like Pregnancy, Diabetes that require range adjustments';

-- 5. REFERENCE_RANGE — normal value ranges per test, method, demographics
-- Cardinality: REFERENCE_RANGE (1) → TEST_RESULT (N), REFERENCE_RANGE (1) → RANGE_ADJUSTMENT (N)
-- FKs: test_id → lab_test, method_id → method
CREATE TABLE reference_range (
    range_id      SERIAL PRIMARY KEY,
    test_id       INTEGER      NOT NULL REFERENCES lab_test(test_id) ON DELETE CASCADE,
    method_id     INTEGER      NOT NULL REFERENCES method(method_id) ON DELETE CASCADE,
    sex           VARCHAR(10)  NOT NULL CHECK (sex IN ('Male', 'Female', 'Both')),
    min_age       INTEGER      NOT NULL CHECK (min_age >= 0),
    max_age       INTEGER      NOT NULL CHECK (max_age >= 0),
    lower_limit   NUMERIC(10,4) NOT NULL,
    upper_limit   NUMERIC(10,4) NOT NULL,
    critical_low  NUMERIC(10,4),
    critical_high NUMERIC(10,4),
    ethnicity     VARCHAR(50),           -- from ER diagram: optional ethnicity filter
    date          DATE DEFAULT CURRENT_DATE,  -- from ER diagram: effective date of this range

    -- Domain constraints
    CHECK (min_age <= max_age),
    CHECK (lower_limit <= upper_limit),
    CHECK (critical_low IS NULL OR critical_low <= lower_limit),
    CHECK (critical_high IS NULL OR critical_high >= upper_limit)
);

COMMENT ON TABLE reference_range IS 'Age/sex/ethnicity-stratified normal ranges with critical limits';

-- 6. RANGE_ADJUSTMENT — condition-based modifications to reference ranges
-- FKs: range_id → reference_range, condition_id → condition
CREATE TABLE range_adjustment (
    adj_id           SERIAL PRIMARY KEY,         -- practical PK added
    range_id         INTEGER NOT NULL REFERENCES reference_range(range_id) ON DELETE CASCADE,
    condition_id     INTEGER NOT NULL REFERENCES condition(condition_id) ON DELETE CASCADE,
    adjustment_type  VARCHAR(20) NOT NULL CHECK (adjustment_type IN ('Multiplier', 'Absolute')),
    adjustment_value NUMERIC(10,4) NOT NULL,

    -- Prevent duplicate adjustments for same range+condition
    UNIQUE (range_id, condition_id)
);

COMMENT ON TABLE range_adjustment IS 'Multiplier or Absolute adjustments applied when patient has a condition';
COMMENT ON COLUMN range_adjustment.adjustment_type IS 'Multiplier: multiply limits by value. Absolute: add value to limits.';

-- 7. TEST_RESULT — actual lab measurements for patients
-- FKs: patient_id → patient, test_id → lab_test, validated_against_range → reference_range
-- Cardinality: TEST_RESULT (1) → QC_ALERT (N)
CREATE TABLE test_result (
    result_id              SERIAL PRIMARY KEY,
    patient_id             INTEGER   NOT NULL REFERENCES patient(patient_id) ON DELETE CASCADE,
    test_id                INTEGER   NOT NULL REFERENCES lab_test(test_id) ON DELETE CASCADE,
    method_id              INTEGER   NOT NULL REFERENCES method(method_id) ON DELETE CASCADE,
    measured_value         NUMERIC(10,4) NOT NULL,
    time                   TIMESTAMP NOT NULL DEFAULT NOW(),
    pregnancy_status       BOOLEAN   NOT NULL DEFAULT FALSE,
    validated_against_range INTEGER  REFERENCES reference_range(range_id)
);

COMMENT ON TABLE test_result IS 'Recorded lab measurements — trigger auto-validates on insert';

-- 8. QC_ALERT — quality control alerts generated by the validation trigger
-- FK: result_id → test_result
CREATE TABLE qc_alert (
    alert_id   SERIAL PRIMARY KEY,
    result_id  INTEGER     NOT NULL REFERENCES test_result(result_id) ON DELETE CASCADE,
    type       VARCHAR(50) NOT NULL,       -- e.g. 'Out of Range', 'Critical Value'
    time       TIMESTAMP   NOT NULL DEFAULT NOW(),
    severity   VARCHAR(20) NOT NULL CHECK (severity IN ('Normal', 'Abnormal', 'Critical'))
);

COMMENT ON TABLE qc_alert IS 'Alerts auto-generated by trg_validate_result trigger';

-- ============================================================================
-- INDEXES for performance on common queries
-- ============================================================================
CREATE INDEX idx_ref_range_lookup ON reference_range(test_id, method_id, sex);
CREATE INDEX idx_test_result_patient ON test_result(patient_id);
CREATE INDEX idx_test_result_test ON test_result(test_id);
CREATE INDEX idx_qc_alert_result ON qc_alert(result_id);
CREATE INDEX idx_qc_alert_severity ON qc_alert(severity);

-- Added by Tushar: Performance index for patient age calculation
CREATE INDEX idx_patient_dob ON patient(dob);