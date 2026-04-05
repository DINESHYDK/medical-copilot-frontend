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
from datetime import timedelta
import math

# Import DB helper
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from frontend.db_connection import run_query, run_insert


def _build_csv_download(df: pd.DataFrame) -> bytes:
    """Convert a dataframe into UTF-8 CSV bytes for Streamlit download button."""
    return df.to_csv(index=False).encode("utf-8")


def _filter_alerts_by_date(display_df: pd.DataFrame) -> pd.DataFrame:
    """Apply date filtering on the Time column when available and parseable."""
    if "Time" not in display_df.columns or display_df.empty:
        return display_df

    parsed_time = pd.to_datetime(display_df["Time"], errors="coerce")
    valid_time_mask = parsed_time.notna()
    if not valid_time_mask.any():
        return display_df

    min_dt = parsed_time[valid_time_mask].min().date()
    max_dt = parsed_time[valid_time_mask].max().date()

    preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
    with preset_col1:
        if st.button("Today", use_container_width=True, key="alerts_preset_today"):
            st.session_state["alerts_date_start"] = max_dt
            st.session_state["alerts_date_end"] = max_dt
            st.rerun()
    with preset_col2:
        if st.button("Last 7 Days", use_container_width=True, key="alerts_preset_7d"):
            st.session_state["alerts_date_start"] = max(min_dt, max_dt - timedelta(days=6))
            st.session_state["alerts_date_end"] = max_dt
            st.rerun()
    with preset_col3:
        if st.button("Last 30 Days", use_container_width=True, key="alerts_preset_30d"):
            st.session_state["alerts_date_start"] = max(min_dt, max_dt - timedelta(days=29))
            st.session_state["alerts_date_end"] = max_dt
            st.rerun()
    with preset_col4:
        if st.button("All Time", use_container_width=True, key="alerts_preset_all"):
            st.session_state["alerts_date_start"] = min_dt
            st.session_state["alerts_date_end"] = max_dt
            st.rerun()

    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date = st.date_input(
            "From date",
            value=min_dt,
            min_value=min_dt,
            max_value=max_dt,
            key="alerts_date_start"
        )
    with date_col2:
        end_date = st.date_input(
            "To date",
            value=max_dt,
            min_value=min_dt,
            max_value=max_dt,
            key="alerts_date_end"
        )

    if start_date > end_date:
        st.warning("From date cannot be after To date.", icon=":material/warning:")
        return display_df.iloc[0:0]

    normalized_time = parsed_time.dt.tz_localize(None) if parsed_time.dt.tz is not None else parsed_time
    date_mask = normalized_time.between(
        pd.Timestamp(start_date),
        pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1),
        inclusive="both"
    )
    return display_df[date_mask.fillna(False)]


def _paginate_alerts(display_df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Return paginated alert rows and paging metadata."""
    if display_df.empty:
        return display_df, 1, 1

    pager_col1, pager_col2, pager_col3 = st.columns([2, 2, 3])
    with pager_col1:
        rows_per_page = st.selectbox(
            "Rows per page",
            options=[10, 25, 50, 100],
            index=1,
            key="alerts_rows_per_page"
        )

    total_pages = max(1, math.ceil(len(display_df) / rows_per_page))
    default_page = st.session_state.get("alerts_page", 1)
    if not isinstance(default_page, int):
        default_page = 1
    if default_page > total_pages:
        default_page = total_pages

    with pager_col2:
        current_page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=default_page,
            step=1,
            key="alerts_page"
        )

    start_idx = (current_page - 1) * rows_per_page
    end_idx = start_idx + rows_per_page
    page_df = display_df.iloc[start_idx:end_idx]

    with pager_col3:
        st.caption(
            f"Page {current_page} of {total_pages}  •  Showing rows {start_idx + 1}-{min(end_idx, len(display_df))}"
        )

    return page_df, current_page, total_pages


def _render_alert_trend_chart(display_df: pd.DataFrame) -> None:
    """Render daily alert trend from currently filtered rows when timestamps exist."""
    if "Time" not in display_df.columns or display_df.empty:
        return

    parsed_time = pd.to_datetime(display_df["Time"], errors="coerce")
    valid_time = parsed_time.dropna()
    if valid_time.empty:
        return

    if valid_time.dt.tz is not None:
        valid_time = valid_time.dt.tz_localize(None)

    trend_df = (
        valid_time.dt.date.value_counts()
        .sort_index()
        .rename_axis("Date")
        .to_frame(name="Alerts")
    )
    st.markdown("##### :material/monitoring: Daily Alert Trend")
    st.line_chart(trend_df, color="#0A66C2")


def _filter_reference_ranges(df_ranges: pd.DataFrame) -> pd.DataFrame:
    """Filter reference ranges by sex, ethnicity, and age overlap."""
    if df_ranges.empty:
        return df_ranges

    st.markdown("##### :material/tune: Range Filters")

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    available_sex = sorted(df_ranges["Sex"].dropna().astype(str).unique().tolist()) if "Sex" in df_ranges.columns else []
    available_ethnicity = sorted(
        df_ranges["Ethnicity"].dropna().astype(str).unique().tolist()
    ) if "Ethnicity" in df_ranges.columns else []

    with filter_col1:
        selected_sex = st.multiselect(
            "Sex",
            options=available_sex,
            default=available_sex,
            key="ranges_filter_sex"
        )

    with filter_col2:
        selected_ethnicity = st.multiselect(
            "Ethnicity",
            options=available_ethnicity,
            default=available_ethnicity,
            key="ranges_filter_ethnicity"
        )

    min_age = int(df_ranges["Min Age"].min()) if "Min Age" in df_ranges.columns else 0
    max_age = int(df_ranges["Max Age"].max()) if "Max Age" in df_ranges.columns else 120

    with filter_col3:
        selected_age = st.slider(
            "Age Window",
            min_value=min_age,
            max_value=max_age,
            value=(min_age, max_age),
            key="ranges_filter_age_window"
        )

    filtered_df = df_ranges.copy()

    if available_sex and selected_sex:
        filtered_df = filtered_df[filtered_df["Sex"].astype(str).isin(selected_sex)]
    elif available_sex and not selected_sex:
        filtered_df = filtered_df.iloc[0:0]

    if available_ethnicity and selected_ethnicity:
        filtered_df = filtered_df[filtered_df["Ethnicity"].astype(str).isin(selected_ethnicity)]
    elif available_ethnicity and not selected_ethnicity:
        filtered_df = filtered_df.iloc[0:0]

    if "Min Age" in filtered_df.columns and "Max Age" in filtered_df.columns:
        age_low, age_high = selected_age
        filtered_df = filtered_df[
            (filtered_df["Max Age"] >= age_low) &
            (filtered_df["Min Age"] <= age_high)
        ]

    return filtered_df


def _build_range_method_summary(df_ranges: pd.DataFrame) -> pd.DataFrame:
    """Create grouped summary stats by instrument and technique."""
    if df_ranges.empty or "Instrument" not in df_ranges.columns or "Technique" not in df_ranges.columns:
        return pd.DataFrame()

    working_df = df_ranges.copy()
    if "Lower Limit" in working_df.columns and "Upper Limit" in working_df.columns:
        working_df["Range Width"] = working_df["Upper Limit"] - working_df["Lower Limit"]
    else:
        working_df["Range Width"] = pd.NA

    summary_df = (
        working_df.groupby(["Instrument", "Technique"], dropna=False)
        .agg(
            ranges=("Range ID", "count"),
            avg_range_width=("Range Width", "mean"),
            min_lower=("Lower Limit", "min"),
            max_upper=("Upper Limit", "max")
        )
        .reset_index()
    )
    summary_df = summary_df.rename(columns={
        "ranges": "Range Rows",
        "avg_range_width": "Avg Width",
        "min_lower": "Min Lower",
        "max_upper": "Max Upper"
    })
    return summary_df


def _detect_range_overlaps(df_ranges: pd.DataFrame) -> pd.DataFrame:
    """Detect age-window overlaps within the same sex/instrument/technique grouping."""
    required_cols = {"Range ID", "Sex", "Instrument", "Technique", "Min Age", "Max Age"}
    if df_ranges.empty or not required_cols.issubset(df_ranges.columns):
        return pd.DataFrame()

    overlaps = []
    group_cols = ["Sex", "Instrument", "Technique"]
    grouped = df_ranges.sort_values(["Sex", "Instrument", "Technique", "Min Age", "Max Age"]).groupby(group_cols, dropna=False)

    for group_keys, group_df in grouped:
        previous_row = None
        for _, row in group_df.iterrows():
            if previous_row is not None and row["Min Age"] <= previous_row["Max Age"]:
                overlaps.append({
                    "Sex": group_keys[0],
                    "Instrument": group_keys[1],
                    "Technique": group_keys[2],
                    "Range A": int(previous_row["Range ID"]),
                    "Range B": int(row["Range ID"]),
                    "Age Overlap": f"{int(row['Min Age'])}-{int(previous_row['Max Age'])}"
                })
            if previous_row is None or row["Max Age"] > previous_row["Max Age"]:
                previous_row = row

    return pd.DataFrame(overlaps)


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

        controls_col1, controls_col2 = st.columns([4, 1])
        with controls_col1:
            severity_filter = st.radio(
                "Filter by severity:",
                ["All", "Critical", "Abnormal", "Normal"],
                horizontal=True,
                key="alerts_severity_filter"
            )
        with controls_col2:
            st.markdown("")
            st.markdown("")
            if st.button(
                ":material/restart_alt: Reset Filters",
                use_container_width=True,
                help="Reset severity, search text, and date window"
            ):
                st.session_state["alerts_severity_filter"] = "All"
                st.session_state["alerts_search_query"] = ""
                st.session_state["alerts_page"] = 1
                if "alerts_date_start" in st.session_state:
                    del st.session_state["alerts_date_start"]
                if "alerts_date_end" in st.session_state:
                    del st.session_state["alerts_date_end"]
                st.toast("Alert filters reset", icon=":material/restart_alt:")
                st.rerun()

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
                help="Type to filter the table below",
                key="alerts_search_query"
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

            st.markdown("##### :material/date_range: Time Window")
            display_df = _filter_alerts_by_date(display_df)

            if display_df.empty:
                st.info(
                    "No alerts found for the current filters.",
                    icon=":material/search_off:"
                )
            else:
                download_col, count_col = st.columns([2, 3])
                with download_col:
                    csv_bytes = _build_csv_download(display_df)
                    st.download_button(
                        ":material/download: Export Filtered Alerts (CSV)",
                        data=csv_bytes,
                        file_name="qc_alerts_filtered.csv",
                        mime="text/csv",
                        use_container_width=True,
                        help="Exports exactly what is currently shown in the table"
                    )
                with count_col:
                    st.caption(f"Showing {len(display_df)} alert record(s) after filters")

                _render_alert_trend_chart(display_df)

                paged_df, _, _ = _paginate_alerts(display_df)

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
                    paged_df,
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

            filtered_ranges = _filter_reference_ranges(df_ranges)

            summary_col1, summary_col2, summary_col3 = st.columns(3)
            with summary_col1:
                st.metric("Visible Ranges", len(filtered_ranges))
            with summary_col2:
                if "Instrument" in filtered_ranges.columns:
                    st.metric("Instruments", int(filtered_ranges["Instrument"].nunique()))
                else:
                    st.metric("Instruments", 0)
            with summary_col3:
                if "Technique" in filtered_ranges.columns:
                    st.metric("Techniques", int(filtered_ranges["Technique"].nunique()))
                else:
                    st.metric("Techniques", 0)

            if filtered_ranges.empty:
                st.info("No reference ranges match the selected filters.", icon=":material/search_off:")
                return

            st.download_button(
                ":material/download: Export Filtered Ranges (CSV)",
                data=_build_csv_download(filtered_ranges),
                file_name="reference_ranges_filtered.csv",
                mime="text/csv",
                use_container_width=True,
                help="Exports currently visible range rows"
            )

            with st.expander("Method Summary", expanded=False):
                method_summary = _build_range_method_summary(filtered_ranges)
                if method_summary.empty:
                    st.caption("No method summary available for current filters.")
                else:
                    st.dataframe(method_summary, use_container_width=True, hide_index=True)

            overlap_df = _detect_range_overlaps(filtered_ranges)
            if overlap_df.empty:
                st.success("No overlapping age windows detected in the visible ranges.", icon=":material/verified:")
            else:
                st.warning(
                    f"Detected {len(overlap_df)} overlapping age-window pair(s). Review these ranges for ambiguity.",
                    icon=":material/warning:"
                )
                st.dataframe(overlap_df, use_container_width=True, hide_index=True)

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
                filtered_ranges,
                use_container_width=True,
                hide_index=True,
                column_config=range_col_config
            )

            # Condition-based adjustments
            range_ids = [int(rid) for rid in filtered_ranges["Range ID"].tolist()] if "Range ID" in filtered_ranges.columns else []
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
