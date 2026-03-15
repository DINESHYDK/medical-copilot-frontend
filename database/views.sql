-- ============================================================================
-- Module M45: Reference Range Validation Database
-- VIEW — vw_critical_patient_alerts
-- Run AFTER all previous SQL files
-- ============================================================================
-- DBMS Concepts:
--   • CREATE VIEW — virtual table derived from a base query
--   • Multi-table JOIN — combines data from 5 tables
--   • Computed columns — age calculated in the view
--   • Aliased columns — user-friendly names for dashboard display
--   • ORDER BY — sorted by severity priority then time
-- ============================================================================

CREATE OR REPLACE VIEW vw_critical_patient_alerts AS
SELECT
    -- Patient info
    p.patient_id,
    p.sex                                              AS patient_sex,
    p.ethnicity                                        AS patient_ethnicity,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, p.dob))::INT   AS patient_age,

    -- Test info
    lt.test_id,
    lt.test_name,

    -- Result info
    tr.result_id,
    tr.measured_value,
    tr.time                                            AS result_time,
    tr.pregnancy_status,

    -- Reference range info
    rr.range_id,
    rr.lower_limit                                     AS ref_lower,
    rr.upper_limit                                     AS ref_upper,
    rr.critical_low                                    AS ref_critical_low,
    rr.critical_high                                   AS ref_critical_high,

    -- Method info
    m.instrument,
    m.technique,

    -- Alert info
    qa.alert_id,
    qa.type                                            AS alert_type,
    qa.severity                                        AS alert_severity,
    qa.time                                            AS alert_time

FROM qc_alert qa
    JOIN test_result tr      ON tr.result_id  = qa.result_id
    JOIN patient p           ON p.patient_id  = tr.patient_id
    JOIN lab_test lt         ON lt.test_id    = tr.test_id
    LEFT JOIN reference_range rr ON rr.range_id = tr.validated_against_range
    LEFT JOIN method m       ON m.method_id   = tr.method_id

ORDER BY
    -- Critical first, then Abnormal, then Normal
    CASE qa.severity
        WHEN 'Critical' THEN 1
        WHEN 'Abnormal' THEN 2
        WHEN 'Normal'   THEN 3
        ELSE 4
    END,
    qa.time DESC;

COMMENT ON VIEW vw_critical_patient_alerts IS
    'Dashboard-ready view: joins Patient, Lab Test, Test Result, Reference Range, Method, and QC Alert for display';
