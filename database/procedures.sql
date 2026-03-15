-- ============================================================================
-- Module M45: Reference Range Validation Database
-- STORED FUNCTION — calculate_effective_range
-- Run AFTER schema.sql and seed_data.sql
-- ============================================================================
-- DBMS Concepts:
--   • PL/pgSQL Stored Function (procedural SQL in PostgreSQL)
--   • Parameterised queries with type-safe input
--   • Conditional logic (IF / ELSIF) inside database
--   • Computed column (age from dob)
--   • JOIN across multiple tables inside a function
--   • Returns a composite type (multiple OUT parameters)
-- ============================================================================

-- Custom composite type for the function return value
DROP TYPE IF EXISTS effective_range_result CASCADE;
CREATE TYPE effective_range_result AS (
    range_id         INTEGER,
    base_lower       NUMERIC(10,4),
    base_upper       NUMERIC(10,4),
    effective_lower  NUMERIC(10,4),
    effective_upper  NUMERIC(10,4),
    critical_low     NUMERIC(10,4),
    critical_high    NUMERIC(10,4)
);

-- ============================================================================
-- FUNCTION: calculate_effective_range
-- Purpose:  Given a patient, test, and method, find the matching reference
--           range and apply any condition-based adjustments.
--
-- Steps:
--   1. Compute patient age from dob
--   2. Get patient sex
--   3. Find the base REFERENCE_RANGE matching test + method + sex + age
--   4. Check if patient has relevant conditions (e.g., pregnancy via flag)
--   5. For each matching RANGE_ADJUSTMENT, apply the math:
--        - Multiplier: new_limit = base_limit × adjustment_value
--        - Absolute:   new_limit = base_limit + adjustment_value
--   6. Return effective lower/upper limits and critical thresholds
-- ============================================================================
CREATE OR REPLACE FUNCTION calculate_effective_range(
    p_patient_id   INTEGER,
    p_test_id      INTEGER,
    p_method_id    INTEGER,
    p_is_pregnant  BOOLEAN DEFAULT FALSE
)
RETURNS effective_range_result
LANGUAGE plpgsql
AS $$
DECLARE
    v_age           INTEGER;
    v_sex           VARCHAR(10);
    v_result        effective_range_result;
    v_adj           RECORD;
BEGIN
    -- ── Step 1 & 2: Get patient age and sex ──────────────────────────────
    SELECT
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, p.dob))::INTEGER,
        p.sex
    INTO v_age, v_sex
    FROM patient p
    WHERE p.patient_id = p_patient_id;

    -- Validate patient exists
    IF v_age IS NULL THEN
        RAISE EXCEPTION 'Patient ID % not found', p_patient_id;
    END IF;

    -- ── Step 3: Find matching reference range ───────────────────────────
    -- Match on test, method, sex (or 'Both'), and age bracket
    SELECT
        rr.range_id,
        rr.lower_limit,
        rr.upper_limit,
        rr.lower_limit,    -- effective starts as base
        rr.upper_limit,    -- effective starts as base
        rr.critical_low,
        rr.critical_high
    INTO v_result
    FROM reference_range rr
    WHERE rr.test_id   = p_test_id
      AND rr.method_id = p_method_id
      AND (rr.sex = v_sex OR rr.sex = 'Both')
      AND v_age BETWEEN rr.min_age AND rr.max_age
    ORDER BY
        -- Prefer sex-specific over 'Both'
        CASE WHEN rr.sex = v_sex THEN 0 ELSE 1 END,
        -- Prefer narrower age ranges
        (rr.max_age - rr.min_age)
    LIMIT 1;

    -- No matching range found
    IF v_result.range_id IS NULL THEN
        RAISE EXCEPTION 'No reference range found for test_id=%, method_id=%, sex=%, age=%',
            p_test_id, p_method_id, v_sex, v_age;
    END IF;

    -- ── Step 4 & 5: Apply condition-based adjustments ───────────────────
    -- If patient is pregnant, apply pregnancy-related adjustments
    IF p_is_pregnant THEN
        FOR v_adj IN
            SELECT ra.adjustment_type, ra.adjustment_value
            FROM range_adjustment ra
            JOIN condition c ON c.condition_id = ra.condition_id
            WHERE ra.range_id = v_result.range_id
              AND c.condition_name = 'Pregnancy'
        LOOP
            IF v_adj.adjustment_type = 'Multiplier' THEN
                -- Multiplier: multiply both limits by the factor
                v_result.effective_lower := v_result.effective_lower * v_adj.adjustment_value;
                v_result.effective_upper := v_result.effective_upper * v_adj.adjustment_value;
            ELSIF v_adj.adjustment_type = 'Absolute' THEN
                -- Absolute: add the value to both limits
                v_result.effective_lower := v_result.effective_lower + v_adj.adjustment_value;
                v_result.effective_upper := v_result.effective_upper + v_adj.adjustment_value;
            END IF;
        END LOOP;
    END IF;

    -- Additional adjustments could be added here for other conditions
    -- (Diabetes, CKD, etc.) based on a patient_condition linking table

    -- ── Step 6: Return the result ───────────────────────────────────────
    RETURN v_result;
END;
$$;

COMMENT ON FUNCTION calculate_effective_range IS
    'Computes effective reference range for a patient+test+method, applying condition adjustments';
