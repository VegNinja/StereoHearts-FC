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

club = data.get("club_details", {})
overall = data.get("overall_stats", {})
members = data.get("member_stats", [])
matches = data.get("matches", [])
match_players = data.get("match_players", [])

st.subheader(st.session_state.get("club_name", "Your club"))
if st.session_state.get("last_sync_count"):
    st.caption(f"Last sync saved {st.session_state['last_sync_count']} records.")

# Summary cards use known fields where available; raw API payloads remain accessible below.
overall_df = records_to_df([overall] if isinstance(overall, dict) else overall)
member_df = records_to_df(members)
match_df = records_to_df(matches)

def get_value(df, names):
    col = first_existing(df, names)
    if col and not df.empty:
        val = df.iloc[0][col]
        return val if pd.notna(val) else "â€”"
    return "â€”"

m1, m2, m3, m4 = st.columns(4)
m1.metric("Played", get_value(overall_df, ["gamesPlayed", "games", "matchesPlayed", "appearances"]))
m2.metric("Wins", get_value(overall_df, ["wins", "gamesWon"]))
m3.metric("Goals scored", get_value(overall_df, ["goals", "goalsFor", "goalsScored"]))
m4.metric("Skill rating", get_value(overall_df, ["skillRating", "rating"]))

tab_overview, tab_squad, tab_matches, tab_archive = st.tabs(
    ["Overview", "Squad", "Matches", "Raw data"]
)

with tab_overview:
    st.subheader("Recent form")
    if not match_df.empty:
        result_col = first_existing(match_df, ["result"])
        if result_col:
            form = match_df[result_col].astype(str).str.upper().head(10).tolist()
            st.write("  ·  ".join(form) if form else "No match results recorded.")
        st.dataframe(match_df.head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No archived matches yet. Use **Sync latest EA data** in the sidebar.")

with tab_squad:
    st.subheader("Player statistics")
    if member_df.empty:
        st.info("No squad statistics saved yet.")
    else:
        sort_col = first_existing(member_df, ["goals", "assists", "rating", "gamesPlayed"])
        if sort_col:
            member_df = member_df.sort_values(sort_col, ascending=False)
        st.dataframe(member_df, use_container_width=True, hide_index=True)
        player_col = first_existing(member_df, ["name", "playerName", "username"])
        goals_col = first_existing(member_df, ["goals"])
        assists_col = first_existing(member_df, ["assists"])
        if player_col and goals_col:
            chart_cols = [player_col, goals_col] + ([assists_col] if assists_col else [])
            chart = member_df[chart_cols].set_index(player_col)
            st.bar_chart(chart)

with tab_matches:
    st.subheader("Recent matches")
    if match_df.empty:
        st.info("No matches archived yet.")
    else:
        st.dataframe(match_df, use_container_width=True, hide_index=True)
    st.subheader("Player performances in collected matches")
    players_df = records_to_df(match_players)
    if players_df.empty:
        st.info("No per-match player data saved yet.")
    else:
        st.dataframe(players_df, use_container_width=True, hide_index=True)

with tab_archive:
    st.subheader("Stored source records")
    st.caption("This view exposes the underlying EA response records for troubleshooting and future analytics.")
    for key in ["club_details", "overall_stats", "member_stats", "matches", "match_players"]:
        with st.expander(key.replace("_", " ").title()):
            st.json(data.get(key, [] if key.endswith("s") else {}))
