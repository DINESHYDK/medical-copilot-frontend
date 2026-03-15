# ============================================================================
# Module M45: Reference Range Validation Database
# Frontend — 100% Native Streamlit Dashboard (Zero Custom CSS)
# ============================================================================
# Architecture:
#   - All styling via .streamlit/config.toml ONLY (no inline HTML/CSS)
#   - @st.cache_data(ttl=60) on all GET queries
#   - st.metric() for KPI cards, st.column_config for dataframes
#   - st.bar_chart for severity visualization
#   - st.toast() for micro-interactions
#   - st.container(border=True) for card sections
# ============================================================================

import streamlit as st
import pandas as pd

# Import DB helper
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from frontend.db_connection import run_query, run_insert


# ─── CACHED DATA FETCHERS ──────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_patients():
    """Fetch all patients with computed age for the submission form dropdown."""
    return run_query("""
        SELECT patient_id, sex, ethnicity,
               EXTRACT(YEAR FROM AGE(CURRENT_DATE, dob))::INT AS age
        FROM patient ORDER BY patient_id
    """)

@st.cache_data(ttl=60, show_spinner=False)
def fetch_tests():
    """Fetch all lab tests for dropdown selection."""
    return run_query("SELECT test_id, test_name FROM lab_test ORDER BY test_id")

@st.cache_data(ttl=60, show_spinner=False)
def fetch_methods():
    """Fetch all analytical methods (instrument + technique)."""
    return run_query("""
        SELECT method_id, instrument, technique
        FROM method ORDER BY method_id
    """)

@st.cache_data(ttl=60, show_spinner=False)
def fetch_alerts(severity_filter=None):
    """Fetch QC alerts from the database view, optionally filtered by severity."""
    if severity_filter and severity_filter != "All":
        return run_query(
            "SELECT * FROM vw_critical_patient_alerts WHERE alert_severity = %s",
            (severity_filter,)
        )
    return run_query("SELECT * FROM vw_critical_patient_alerts")

@st.cache_data(ttl=60, show_spinner=False)
def fetch_ranges(test_id):
    """Fetch reference ranges for a specific lab test, joined with method details."""
    return run_query("""
        SELECT rr.range_id, rr.sex, rr.min_age, rr.max_age,
               rr.lower_limit, rr.upper_limit,
               rr.critical_low, rr.critical_high,
               rr.ethnicity, rr.date,
               m.instrument, m.technique
        FROM reference_range rr
        JOIN method m ON m.method_id = rr.method_id
        WHERE rr.test_id = %s
        ORDER BY rr.sex, rr.min_age
    """, (test_id,))

@st.cache_data(ttl=60, show_spinner=False)
def fetch_adjustments(range_ids):
    """Fetch condition-based range adjustments for a list of range IDs."""
    return run_query("""
        SELECT ra.adj_id, ra.range_id, c.condition_name,
               ra.adjustment_type, ra.adjustment_value
        FROM range_adjustment ra
        JOIN condition c ON c.condition_id = ra.condition_id
        WHERE ra.range_id = ANY(%s)
        ORDER BY ra.range_id
    """, (range_ids,))


# ─── MAIN DASHBOARD ────────────────────────────────────────────────────────

def reference_range_dashboard():
    """Main dashboard entry point for Module M45 — Reference Range Validation."""

    # ── Header ───────────────────────────────────────────────────────────
    header_col, refresh_col = st.columns([5, 1])
    with header_col:
        st.markdown("### :material/science: Reference Range Validation Database")
        st.caption("Module M45  —  Lab test validation with automated QC alerts")
    with refresh_col:
        st.markdown("")  # spacer
        if st.button(":material/sync: Refresh", use_container_width=True,
                      help="Clear cached data and reload from database"):
            st.cache_data.clear()
            st.toast("Cache cleared — reloading data", icon=":material/sync:")
            st.rerun()

    st.divider()

    # ── Tabs ─────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        ":material/add_circle: Submit Lab Result",
        ":material/monitoring: Critical Alerts",
        ":material/rule: Reference Ranges"
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1: Submit New Lab Result
    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("#### :material/edit_note: Submit a New Lab Test Result")
        st.info(
            "When you submit a result, the database **trigger** automatically validates "
            "the value against the reference range and generates a QC alert.",
            icon=":material/info:"
        )

        with st.spinner(":material/sync: Loading clinical data..."):
            try:
                patients = fetch_patients()
                tests = fetch_tests()
                methods = fetch_methods()
            except Exception as e:
                st.error(f"Could not load form data: {e}", icon=":material/error:")
                return

        if not patients or not tests or not methods:
            st.warning(
                "No master data found. Please ensure the database has been seeded.",
                icon=":material/warning:"
            )
            return

        # ── Form ─────────────────────────────────────────────────────────
        with st.form("lab_result_form", clear_on_submit=True, border=True):
            col_left, col_right = st.columns(2, gap="large")

            with col_left:
                st.markdown("##### :material/person: Patient & Test")
                patient_options = {
                    f"PID-{p['patient_id']}  |  {p['sex']}, Age {p['age']}, {p['ethnicity'] or 'N/A'}": p['patient_id']
                    for p in patients
                }
                selected_patient = st.selectbox(
                    "Patient",
                    list(patient_options.keys()),
                    help="Search by Patient ID, sex, age, or ethnicity"
                )

                test_options = {t['test_name']: t['test_id'] for t in tests}
                selected_test = st.selectbox("Lab Test", list(test_options.keys()))

                pregnancy_status = st.toggle("Patient is pregnant", value=False)

            with col_right:
                st.markdown("##### :material/biotech: Method & Value")
                method_options = {
                    f"{m['instrument']} — {m['technique']}": m['method_id']
                    for m in methods
                }
                selected_method = st.selectbox("Analytical Method", list(method_options.keys()))

                measured_value = st.number_input(
                    "Measured Value",
                    min_value=0.0,
                    step=0.1,
                    format="%.4f"
                )

            st.divider()
            submitted = st.form_submit_button(
                ":material/send: Submit Lab Result",
                use_container_width=True,
                type="primary"
            )

            if submitted:
                if measured_value <= 0.0:
                    st.warning("Please enter a measured value greater than 0.", icon=":material/warning:")
                else:
                    with st.spinner(":material/sync: Running validation trigger..."):
                        try:
                            patient_id = patient_options[selected_patient]
                            test_id = test_options[selected_test]
                            method_id = method_options[selected_method]

                            result = run_insert("""
                                INSERT INTO test_result
                                    (patient_id, test_id, method_id, measured_value, pregnancy_status)
                                VALUES (%s, %s, %s, %s, %s)
                                RETURNING result_id
                            """, (patient_id, test_id, method_id, measured_value, pregnancy_status))

                            result_id = result['result_id']

                            alert = run_query("""
                                SELECT type, severity, time
                                FROM qc_alert
                                WHERE result_id = %s
                                ORDER BY alert_id DESC LIMIT 1
                            """, (result_id,))

                            st.cache_data.clear()

                            # Toast micro-interaction
                            st.toast("Lab result recorded & validated!", icon=":material/check_circle:")

                            # Visual confirmation
                            st.success(
                                f"Result submitted successfully  —  **Result ID: {result_id}**",
                                icon=":material/check_circle:"
                            )

                            if alert:
                                a = alert[0]
                                if a['severity'] == 'Critical':
                                    st.error(
                                        f"**CRITICAL ALERT** — {a['type']}",
                                        icon=":material/emergency:"
                                    )
                                elif a['severity'] == 'Abnormal':
                                    st.warning(
                                        f"**ABNORMAL** — {a['type']}",
                                        icon=":material/warning:"
                                    )
                                else:
                                    st.success(
                                        f"**NORMAL** — {a['type']}",
                                        icon=":material/verified:"
                                    )

                        except Exception as e:
                            st.error(f"Error submitting result: {e}", icon=":material/error:")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2: Critical Alerts Dashboard
    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("#### :material/monitoring: QC Alerts Dashboard")
        st.caption("Data source: `vw_critical_patient_alerts` — a database VIEW joining 5 tables")

        severity_filter = st.radio(
            "Filter by severity:",
            ["All", "Critical", "Abnormal", "Normal"],
            horizontal=True
        )

        with st.spinner(":material/sync: Syncing with clinical database..."):
            try:
                alerts = fetch_alerts(severity_filter)
            except Exception as e:
                st.error(f"Could not load alerts: {e}", icon=":material/error:")
                return

        if not alerts:
            st.info("No alerts found matching the selected filter.", icon=":material/info:")
        else:
            df = pd.DataFrame(alerts)

            # ── KPI Metric Cards (native st.metric) ─────────────────────
            total = len(df)
            critical_count = int((df['alert_severity'] == 'Critical').sum()) if 'alert_severity' in df.columns else 0
            abnormal_count = int((df['alert_severity'] == 'Abnormal').sum()) if 'alert_severity' in df.columns else 0
            normal_count   = int((df['alert_severity'] == 'Normal').sum()) if 'alert_severity' in df.columns else 0

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                with st.container(border=True):
                    st.metric("Total Alerts", total)
            with c2:
                with st.container(border=True):
                    st.metric("Critical", critical_count, help="Dangerously out of range")
            with c3:
                with st.container(border=True):
                    st.metric("Abnormal", abnormal_count, help="Outside normal limits")
            with c4:
                with st.container(border=True):
                    st.metric("Normal", normal_count, help="Within reference range")

            # ── Severity Breakdown Chart (native st.bar_chart) ───────────
            if 'alert_severity' in df.columns:
                severity_counts = df['alert_severity'].value_counts().reset_index()
                severity_counts.columns = ['Severity', 'Count']
                severity_counts = severity_counts.set_index('Severity')
                st.bar_chart(severity_counts, color="#0A66C2")

            st.divider()

            # ── Search Bar ───────────────────────────────────────────────
            search_query = st.text_input(
                ":material/search: Search alerts",
                placeholder="Filter by Patient ID, Test Name, or Alert Type...",
                help="Type to filter the table below"
            )

            # Prepare display DataFrame
            display_cols = [
                'patient_id', 'patient_sex', 'patient_age', 'test_name',
                'measured_value', 'ref_lower', 'ref_upper',
                'ref_critical_low', 'ref_critical_high',
                'alert_type', 'alert_severity', 'result_time'
            ]
            available_cols = [c for c in display_cols if c in df.columns]
            display_df = df[available_cols].copy()

            rename_map = {
                'patient_id': 'Patient ID',
                'patient_sex': 'Sex',
                'patient_age': 'Age',
                'test_name': 'Test',
                'measured_value': 'Value',
                'ref_lower': 'Lower Limit',
                'ref_upper': 'Upper Limit',
                'ref_critical_low': 'Critical Low',
                'ref_critical_high': 'Critical High',
                'alert_type': 'Alert Type',
                'alert_severity': 'Severity',
                'result_time': 'Time'
            }
            display_df = display_df.rename(columns=rename_map)

            # Apply search filter
            if search_query:
                search_lower = search_query.lower()
                mask = display_df.apply(
                    lambda row: row.astype(str).str.lower().str.contains(search_lower).any(),
                    axis=1
                )
                display_df = display_df[mask]

            if display_df.empty:
                st.info(
                    f'No results matching "{search_query}".',
                    icon=":material/search_off:"
                )
            else:
                # ── Professional Dataframe (native column_config) ────────
                column_config = {
                    "Patient ID": st.column_config.NumberColumn("Patient ID", format="%d"),
                    "Age": st.column_config.NumberColumn("Age", format="%d yrs"),
                    "Value": st.column_config.NumberColumn("Value", format="%.2f", help="Measured lab value"),
                    "Lower Limit": st.column_config.NumberColumn("Lower Limit", format="%.2f"),
                    "Upper Limit": st.column_config.NumberColumn("Upper Limit", format="%.2f"),
                    "Critical Low": st.column_config.NumberColumn("Crit. Low", format="%.2f"),
                    "Critical High": st.column_config.NumberColumn("Crit. High", format="%.2f"),
                    "Severity": st.column_config.TextColumn(
                        "Severity",
                        help="Critical = dangerously OOR, Abnormal = outside normal, Normal = within range"
                    ),
                    "Time": st.column_config.DatetimeColumn("Timestamp", format="DD MMM YYYY, HH:mm"),
                }

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config=column_config
                )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3: Reference Ranges Viewer
    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("#### :material/rule: Reference Ranges Browser")
        st.caption("Browse reference ranges by test — shows age, sex, and method-specific normal values")

        with st.spinner(":material/sync: Loading lab tests..."):
            try:
                tests_list = fetch_tests()
            except Exception as e:
                st.error(f"Could not load tests: {e}", icon=":material/error:")
                return

        if not tests_list:
            st.info("No tests found in the database.", icon=":material/info:")
            return

        test_options_viewer = {t['test_name']: t['test_id'] for t in tests_list}
        selected_test_name = st.selectbox(
            "Select a Lab Test:",
            list(test_options_viewer.keys()),
            key="range_viewer"
        )
        selected_tid = test_options_viewer[selected_test_name]

        with st.spinner(f":material/sync: Loading ranges for {selected_test_name}..."):
            try:
                ranges = fetch_ranges(selected_tid)
            except Exception as e:
                st.error(f"Could not load ranges: {e}", icon=":material/error:")
                return

        if not ranges:
            st.info(
                f"No reference ranges defined for **{selected_test_name}**.",
                icon=":material/info:"
            )
        else:
            df_ranges = pd.DataFrame(ranges)
            rename_map_r = {
                'range_id': 'Range ID', 'sex': 'Sex',
                'min_age': 'Min Age', 'max_age': 'Max Age',
                'lower_limit': 'Lower Limit', 'upper_limit': 'Upper Limit',
                'critical_low': 'Critical Low', 'critical_high': 'Critical High',
                'ethnicity': 'Ethnicity', 'date': 'Effective Date',
                'instrument': 'Instrument', 'technique': 'Technique'
            }
            df_ranges = df_ranges.rename(columns=rename_map_r)

            range_col_config = {
                "Range ID": st.column_config.NumberColumn("Range ID", format="%d"),
                "Min Age": st.column_config.NumberColumn("Min Age", format="%d"),
                "Max Age": st.column_config.NumberColumn("Max Age", format="%d"),
                "Lower Limit": st.column_config.NumberColumn("Lower", format="%.2f"),
                "Upper Limit": st.column_config.NumberColumn("Upper", format="%.2f"),
                "Critical Low": st.column_config.NumberColumn("Crit. Low", format="%.2f"),
                "Critical High": st.column_config.NumberColumn("Crit. High", format="%.2f"),
                "Effective Date": st.column_config.DateColumn("Effective", format="DD MMM YYYY"),
            }
            st.dataframe(
                df_ranges,
                use_container_width=True,
                hide_index=True,
                column_config=range_col_config
            )

            # Condition-based adjustments
            range_ids = [r['range_id'] for r in ranges]
            if range_ids:
                with st.spinner(":material/sync: Loading condition adjustments..."):
                    try:
                        adjustments = fetch_adjustments(range_ids)
                    except Exception:
                        adjustments = []

                if adjustments:
                    st.markdown("##### :material/swap_vert: Condition-Based Adjustments")
                    df_adj = pd.DataFrame(adjustments)
                    df_adj = df_adj.rename(columns={
                        'adj_id': 'Adj ID', 'range_id': 'Range ID',
                        'condition_name': 'Condition',
                        'adjustment_type': 'Type', 'adjustment_value': 'Value'
                    })
                    st.dataframe(df_adj, use_container_width=True, hide_index=True)


# ── Standalone entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(
        page_title="M45 Reference Range Validation",
        page_icon=":material/science:",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    reference_range_dashboard()
