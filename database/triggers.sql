-- ============================================================================
-- Module M45: Reference Range Validation Database
-- TRIGGER — trg_validate_result (AFTER INSERT on test_result)
-- Run AFTER schema.sql, seed_data.sql, and procedures.sql
-- ============================================================================
-- DBMS Concepts:
--   • AFTER INSERT Trigger — fires automatically after a row is inserted
--   • Trigger Function — PL/pgSQL function that powers the trigger
--   • Automatic validation — no application code needed for QC checks
--   • Data integrity through triggers — ensures every result is validated
--   • INSERT into qc_alert — auto-generates alerts for abnormal values
--   • UPDATE of validated_against_range — links result to its reference range
-- ============================================================================

-- ── Trigger Function ────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_validate_result()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_range   effective_range_result;
    v_alert_type    VARCHAR(50);
    v_alert_severity VARCHAR(20);
BEGIN
    -- ── Step 1: Call calculate_effective_range to get the applicable range ──
    BEGIN
        v_range := calculate_effective_range(
            NEW.patient_id,
            NEW.test_id,
            NEW.method_id,
            NEW.pregnancy_status
        );
    EXCEPTION
        WHEN OTHERS THEN
            -- If no range found, still insert an alert for manual review
            INSERT INTO qc_alert (result_id, type, time, severity)
            VALUES (NEW.result_id, 'No Reference Range Found', NOW(), 'Abnormal');
            RETURN NEW;
    END;

    -- ── Step 2: Update the test_result with the matched range ──────────────
    UPDATE test_result
    SET validated_against_range = v_range.range_id
    WHERE result_id = NEW.result_id;

    -- ── Step 3: Compare measured_value against effective limits ─────────────
    IF v_range.critical_low IS NOT NULL AND NEW.measured_value <= v_range.critical_low THEN
        -- CRITICAL LOW: value is dangerously below normal
        v_alert_type := 'Critical Low Value';
        v_alert_severity := 'Critical';

    ELSIF v_range.critical_high IS NOT NULL AND NEW.measured_value >= v_range.critical_high THEN
        -- CRITICAL HIGH: value is dangerously above normal
        v_alert_type := 'Critical High Value';
        v_alert_severity := 'Critical';

    ELSIF NEW.measured_value < v_range.effective_lower THEN
        -- ABNORMAL LOW: below normal but not critical
        v_alert_type := 'Below Normal Range';
        v_alert_severity := 'Abnormal';

    ELSIF NEW.measured_value > v_range.effective_upper THEN
        -- ABNORMAL HIGH: above normal but not critical
        v_alert_type := 'Above Normal Range';
        v_alert_severity := 'Abnormal';

    ELSE
        -- NORMAL: value is within effective range
        v_alert_type := 'Within Normal Range';
        v_alert_severity := 'Normal';
    END IF;

    -- ── Step 4: Insert QC Alert ────────────────────────────────────────────
    INSERT INTO qc_alert (result_id, type, time, severity)
    VALUES (NEW.result_id, v_alert_type, NOW(), v_alert_severity);

    RETURN NEW;
END;
$$;

-- ── Create the Trigger ──────────────────────────────────────────────────────
-- AFTER INSERT: fires after the row is committed to test_result
-- FOR EACH ROW: fires once per inserted row
DROP TRIGGER IF EXISTS trg_validate_result ON test_result;

CREATE TRIGGER trg_validate_result
    AFTER INSERT ON test_result
    FOR EACH ROW
    EXECUTE FUNCTION fn_validate_result();

COMMENT ON FUNCTION fn_validate_result IS
    'Trigger function: validates measured_value against effective range, generates QC alerts';

-- ============================================================================
-- SAMPLE TEST DATA (now safe to insert — trigger will fire automatically)
-- ============================================================================

-- Normal: Male (ID 2), Hemoglobin = 15.2 (range 13.5-17.5) → Normal
INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
    VALUES (2, 1, 1, 15.2, FALSE);

-- Abnormal Low: Female (ID 1), Hemoglobin = 11.0 (range 12.0-16.0) → Abnormal
INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
    VALUES (1, 1, 1, 11.0, FALSE);

-- Critical High: Male (ID 2), Glucose = 450 (critical_high = 400) → Critical
INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
    VALUES (2, 2, 2, 450.0, FALSE);

-- Pregnant Female (ID 3), Hemoglobin = 10.5 (adjusted range ~10.2-13.6) → Normal
INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
    VALUES (3, 1, 1, 10.5, TRUE);

-- Abnormal High: Senior Male (ID 4), TSH = 5.5 (range 0.4-4.0) → Abnormal
INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
    VALUES (4, 3, 3, 5.5, FALSE);

-- Normal: Female (ID 7), Creatinine = 0.9 (range 0.6-1.1) → Normal
INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
    VALUES (7, 4, 2, 0.9, FALSE);

-- Critical Low: Child (ID 5), WBC = 1.8 (critical_low = 2.0) → Critical
INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
    VALUES (5, 6, 1, 1.8, FALSE);

-- Normal: Male (ID 6), Cholesterol = 185 (range 125-200) → Normal
INSERT INTO test_result (patient_id, test_id, method_id, measured_value, pregnancy_status)
    VALUES (6, 5, 2, 185.0, FALSE);
