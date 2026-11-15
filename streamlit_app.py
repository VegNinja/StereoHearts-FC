import json
import streamlit as st
import pandas as pd

from ea_client import fetch_club_bundle
from storage import SupabaseStore, StoreError

st.set_page_config(page_title="FC 27 Club Dashboard", page_icon="âš½", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1450px;}
[data-testid="stMetric"] {background: rgba(120,120,120,.07); padding: 14px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

def get_store():
    try:
        cfg = st.secrets["supabase"]
        return SupabaseStore(cfg["url"], cfg["service_role_key"])
    except Exception:
        return None

def records_to_df(records):
    if not records:
        return pd.DataFrame()
    return pd.json_normalize(records)

def first_existing(df, candidates):
    for name in candidates:
        if name in df.columns:
            return name
    return None

st.title("StereoHearts FC Club Dashboard")
st.caption("FC 27 · PlayStation 5 · Unofficial community API")

# This dashboard is permanently pinned to StereoHearts FC.
CLUB_NAME = "StereoHearts FC"
CLUB_ID = "400349"

st.session_state["club_name"] = CLUB_NAME
st.session_state["club_id"] = CLUB_ID

with st.sidebar:
    st.header("Club")
    st.subheader(CLUB_NAME)
    st.caption(f"EA Club ID: `{CLUB_ID}`")
    st.caption("This dashboard is fixed to StereoHearts FC. The club selector has been removed.")
    st.caption("The website is read-only for visitors. Admin access is required to sync EA data.")

    try:
        expected_password = st.secrets["app"]["admin_password"]
    except Exception:
        expected_password = ""

    if expected_password:
        entered_password = st.text_input("Admin password", type="password")
        if st.button("Unlock sync controls", use_container_width=True):
            st.session_state["admin_unlocked"] = (entered_password == expected_password)
            if not st.session_state["admin_unlocked"]:
                st.error("Incorrect admin password.")

        if st.session_state.get("admin_unlocked"):
            if st.button("Sync latest EA data", type="primary", use_container_width=True):
                store = get_store()
                if store is None:
                    st.error("Supabase is not configured yet. Follow the README setup steps.")
                else:
                    try:
                        with st.spinner(f"Collecting {CLUB_NAME} club, squad and recent match data..."):
                            bundle = fetch_club_bundle(int(CLUB_ID))
                            count = store.save_bundle(
                                CLUB_ID,
                                CLUB_NAME,
                                bundle
                            )
                        st.session_state["last_sync_count"] = count
                        st.success(f"Saved {count} records for {CLUB_NAME}.")
                    except Exception as exc:
                        st.error(f"Sync failed: {exc}")
    else:
        st.warning("Add an app.admin_password secret before deploying. Sync controls remain disabled until then.")

st.divider()
store = get_store()
if store is None:
    st.warning("The club has been selected, but the database is not connected. Configure Supabase using the README before syncing.")
    st.stop()

try:
    data = store.load_bundle(st.session_state["club_id"])
except StoreError as exc:
    st.error(f"Database error: {exc}")
    st.stop()
