# ============================================================================
# Module M45: Reference Range Validation Database
# Frontend — Streamlit Dashboard (db_connection helper)
# ============================================================================

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st


def get_connection():
    """
    Get a PostgreSQL connection using Streamlit secrets or environment variables.

    Priority:
      1. st.secrets["DATABASE_URL"] — for Streamlit Cloud deployment
      2. os.environ["DATABASE_URL"] — for local development with .env
    """
    try:
        # Try Streamlit secrets first (for deployed app)
        db_url = st.secrets.get("DATABASE_URL", None)
        if not db_url:
            # Fall back to environment variable
            db_url = os.getenv("DATABASE_URL", "")

        if not db_url:
            st.error("❌ DATABASE_URL not configured. Please set it in .streamlit/secrets.toml or .env")
            st.stop()

        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        conn.autocommit = True
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        st.stop()


def run_query(query, params=None):
    """Execute a SELECT query and return results as list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()


def run_insert(query, params=None):
    """Execute an INSERT query and return the result (e.g., RETURNING clause)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()
    finally:
        conn.close()
