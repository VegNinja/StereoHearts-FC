import json
import html
import re
import streamlit as st
import pandas as pd
import altair as alt

from ea_client import fetch_club_bundle
from storage import SupabaseStore, StoreError

st.set_page_config(page_title="StereoHearts FC | Club Analytics", page_icon="⚽", layout="wide")

# Middlesbrough-inspired red-and-white visual identity.
# This styling does not change the underlying EA data or dashboard logic.
st.markdown("""
<style>
:root { --boro-red: #C8102E; --boro-dark: #9D0B22; --ink: #20242B; --pale: #F2F3F5; }
.block-container {padding-top: 1.8rem; max-width: 1450px;}
/* Subtle red club stripe above the dashboard. */
.block-container::before {content: ""; display: block; height: 6px; border-radius: 5px;
  background: linear-gradient(90deg, #C8102E 0%, #C8102E 70%, #FFFFFF 70%, #FFFFFF 78%, #C8102E 78%);
  margin-bottom: 1.4rem;}
h1, h2, h3 {letter-spacing: -.025em;}
h1 {font-weight: 800 !important;}
[data-testid="stMetric"] {background: #F7F7F8; border: 1px solid #E5E6E8;
  border-top: 3px solid #C8102E; padding: 16px; border-radius: 10px;}
[data-testid="stMetricLabel"] {font-weight: 600;}
[data-testid="stSidebar"] {border-right: 3px solid #C8102E;}
/* Tabs, active selections and primary action buttons. */
.stTabs [data-baseweb="tab-list"] {gap: 6px; border-bottom: 1px solid #E5E6E8;}
.stTabs [data-baseweb="tab"] {border-radius: 8px 8px 0 0; font-weight: 600;}
.stTabs [aria-selected="true"] {color: #C8102E !important;}
.stTabs [data-baseweb="tab-highlight"] {background-color: #C8102E !important;}
.stButton button[kind="primary"] {background: #C8102E; border-color: #C8102E; color: white;}
.stButton button[kind="primary"]:hover {background: #9D0B22; border-color: #9D0B22; color: white;}
/* Tables and expanders get understated borders rather than heavy red fills. */
[data-testid="stDataFrame"] {border: 1px solid #E5E6E8; border-radius: 9px; overflow: hidden;}
[data-testid="stExpander"] {border-radius: 9px;}
/* Club landing-page hero: red-and-white football identity. */
.sh-hero {background:linear-gradient(115deg,#a50924 0%,#c8102e 68%,#e22b46 100%);color:white;
  border-radius:16px;padding:30px 34px;margin:0 0 22px;position:relative;overflow:hidden;
  box-shadow:0 8px 24px rgba(70,10,22,.12);}
.sh-hero::after {content:"";position:absolute;right:5%;top:-50px;width:105px;height:220px;
  transform:rotate(26deg);background:rgba(255,255,255,.12);box-shadow:150px 0 0 rgba(255,255,255,.07);}
.sh-kicker {font-size:.76rem;font-weight:750;letter-spacing:.17em;text-transform:uppercase;opacity:.88;}
.sh-name {font-size:clamp(1.9rem,4.5vw,3.2rem);line-height:1.1;font-weight:850;margin:10px 0 8px;}
.sh-subtitle {font-size:1rem;opacity:.94;}
.sh-hero-footer {margin-top:22px;padding-top:12px;border-top:1px solid rgba(255,255,255,.28);
  font-size:.82rem;letter-spacing:.04em;}
.sh-section {border-left:5px solid #C8102E;padding-left:14px;margin:10px 0 16px;}
/* Respect Streamlit's dark-mode text colours instead of forcing dark text on dark backgrounds. */
@media (prefers-color-scheme: dark) {
  [data-testid="stMetric"] {background: #262830; border-color: #41434B; border-top-color: #C8102E;}
  .stTabs [data-baseweb="tab-list"] {border-bottom-color: #41434B;}
  [data-testid="stDataFrame"] {border-color: #41434B;}
}
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

st.markdown("""
<div class="sh-hero">
  <div class="sh-kicker">StereoHearts FC · Club headquarters</div>
  <div class="sh-name">STEREOHEARTS FC</div>
  <div class="sh-subtitle">The home of our squad, results and player performance</div>
  <div class="sh-hero-footer">FC 27 &nbsp; / &nbsp; PLAYSTATION 5 &nbsp; / &nbsp; CLUB ANALYTICS</div>
</div>
""", unsafe_allow_html=True)

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
                        st.cache_data.clear()  # Invalidate archived-table snapshots after a successful sync.
                        st.session_state["last_sync_count"] = count
                        st.success(f"Saved {count} records for {CLUB_NAME}.")
                    except Exception as exc:
                        st.error(f"Sync failed: {exc}")
    else:
        st.warning("Add an app.admin_password secret before deploying. Sync controls remain disabled until then.")

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

# Read structured matches once for the snapshot, Overview and Analytics tabs.
@st.cache_data(ttl=60, show_spinner=False)
def read_all_rows(table_name, club_id, _store, page_size=1000):
    """Fetch all Supabase pages once per cache window, across Streamlit reruns.

    `_store` is deliberately excluded from Streamlit's cache-key hashing.
    Manual EA sync clears the cache so new results become visible immediately.
    """
    rows = []
    for offset in range(0, 1_000_000_000, page_size):
        response = (
            _store.client.table(table_name).select("*")
            .eq("club_id", int(club_id))
            .range(offset, offset + page_size - 1).execute()
        )
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
    raise RuntimeError("Supabase pagination exceeded safety limit")

try:
    stored_matches = pd.DataFrame(read_all_rows("matches", CLUB_ID, store))
    structured_matches_error = None
except Exception as exc:
    stored_matches = pd.DataFrame()
    structured_matches_error = str(exc)


def opponent_goals(row):
    """Use explicitly named opponent-goal fields only; never infer from results."""
    raw = row.get("raw_data")
    if not isinstance(raw, dict):
        raw = {}
    for source in (raw, row):
        for key in ("goalsAgainst", "goalsConceded", "opponentGoals", "opponentScore", "goals_against"):
            value = source.get(key)
            if value is not None and str(value).strip() != "":
                number = pd.to_numeric(value, errors="coerce")
                if pd.notna(number):
                    return int(number)
    return None


# Shared archived datasets are prepared before any tabs render.
try:
    stored_players = pd.DataFrame(read_all_rows("match_player_stats", CLUB_ID, store))
except Exception as exc:
    st.warning(f"Could not load player statistics: {exc}")
    stored_players = pd.DataFrame()

def _prepared_matches():
    if stored_matches.empty:
        return pd.DataFrame()
    frame = stored_matches.copy()
    frame["match_id"] = frame["match_id"].astype(str)
    frame = frame.drop_duplicates(subset=["match_id"], keep="last")
    frame["played_at"] = pd.to_datetime(frame["played_at"], utc=True, errors="coerce")
    frame["result_label"] = frame["result"].fillna("").astype(str).str.strip().str.lower().map(
        {"win": "W", "w": "W", "draw": "D", "d": "D", "tie": "D", "loss": "L", "lose": "L", "l": "L"}
    )
    frame["goals_for"] = pd.to_numeric(frame["goals"], errors="coerce")
    frame["goals_against"] = frame.apply(opponent_goals, axis=1)
    return frame.sort_values(["played_at", "match_id"], ascending=[True, True], na_position="first")


def _prepared_players():
    if stored_players.empty or "match_id" not in stored_players or "player_id" not in stored_players:
        return pd.DataFrame()
    frame = stored_players.copy()
    frame["match_id"] = frame["match_id"].astype(str)
    frame["player_id"] = frame["player_id"].astype(str)
    frame = frame.drop_duplicates(["match_id", "player_id"], keep="last")
    for field in ("goals", "assists", "rating", "seconds_played", "clean_sheet", "man_of_the_match",
                  "saves", "tackles_made", "tackle_attempts", "passes_made", "pass_attempts", "shots"):
        if field not in frame:
            frame[field] = float("nan")
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
    for field, default in (("player_name", "Unknown player"), ("position", "Unknown")):
        if field not in frame.columns:
            frame[field] = default
        frame[field] = frame[field].fillna(default).astype(str)

    # Match type belongs to the matches table, not necessarily match_player_stats.
    # Enrich each performance by its match_id without duplicating player rows.
    if "match_type" not in frame.columns:
        frame["match_type"] = pd.NA
    if "played_at" not in frame.columns:
        frame["played_at"] = pd.NaT
    if not all_matches.empty and {"match_id", "match_type"}.issubset(all_matches.columns):
        lookup = all_matches.drop_duplicates("match_id", keep="last").set_index("match_id")
        frame["match_type"] = frame["match_type"].fillna(frame["match_id"].map(lookup["match_type"]))
        if "played_at" in lookup.columns:
            frame["played_at"] = pd.to_datetime(frame["played_at"], utc=True, errors="coerce").fillna(
                pd.to_datetime(frame["match_id"].map(lookup["played_at"]), utc=True, errors="coerce")
            )
    frame["match_type"] = frame["match_type"].fillna("Unknown").astype(str)
    frame["played_at"] = pd.to_datetime(frame["played_at"], utc=True, errors="coerce")
    return frame


all_matches = _prepared_matches()
all_performances = _prepared_players()


def event_counter(raw, names):
    """Read named event counters without constructing a DataFrame per event.

    Exact top-level keys take priority; nested dictionary keys are supported.
    Missing or non-numeric values remain NaN, never fabricated zeros.
    """
    if not isinstance(raw, dict):
        return float("nan")
    for key in names:
        if key in raw:
            return pd.to_numeric(raw[key], errors="coerce")
        pending = list(reversed(list(raw.values())))
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                if key in value:
                    return pd.to_numeric(value[key], errors="coerce")
                pending.extend(reversed(list(value.values())))
    return float("nan")


def sum_event_counters(raw, names):
    """Sum an event group only when *every* required counter is present."""
    values = [event_counter(raw, (name,)) for name in names]
    return sum(values) if all(pd.notna(value) for value in values) else float("nan")

profiles = pd.DataFrame()
if not stored_players.empty and "player_id" in stored_players.columns:
    profiles = stored_players.copy()
    profiles["player_id"] = profiles["player_id"].astype(str)
    profiles["match_id"] = profiles["match_id"].astype(str)
    profiles = profiles.drop_duplicates(subset=["match_id", "player_id"], keep="last")
    profiles["player_name"] = profiles["player_name"].fillna("Unknown player").astype(str)
    profiles["position"] = profiles["position"].fillna("Unknown").astype(str)

    # Use the latest available name, but retain player ID as the stable identity.
    if "played_at" in profiles.columns:
        profiles["played_at"] = pd.to_datetime(profiles["played_at"], utc=True, errors="coerce")
    else:
        profiles["played_at"] = pd.NaT
    if not stored_matches.empty and {"match_id", "match_type", "played_at"}.issubset(stored_matches.columns):
        match_lookup = stored_matches[["match_id", "match_type", "played_at"]].copy()
        match_lookup["match_id"] = match_lookup["match_id"].astype(str)
        match_lookup = match_lookup.drop_duplicates("match_id")
        match_lookup = match_lookup.rename(columns={"played_at": "match_played_at"})
        profiles = profiles.merge(match_lookup, on="match_id", how="left")
        profiles["played_at"] = profiles["played_at"].fillna(
            pd.to_datetime(profiles["match_played_at"], utc=True, errors="coerce")
        )
    else:
        profiles["match_type"] = "Unknown"
    profiles["match_type"] = profiles["match_type"].fillna("Unknown").astype(str)
    profiles = profiles.sort_values("played_at", na_position="last")


st.markdown("""
<style>
/* Keep dashboard KPI pairs, filters and performance buttons in rows on phones. */
@media (max-width: 700px) {
  div[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) { flex-wrap: nowrap !important; gap: .45rem !important; }
  div[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div[data-testid="stColumn"] { min-width: 0 !important; width: 50% !important; flex: 1 1 50% !important; }
  div[data-testid="stHorizontalBlock"]:has([class*="st-key-areas_player"]) { flex-wrap: nowrap !important; gap: .35rem !important; }
  div[data-testid="stHorizontalBlock"]:has([class*="st-key-areas_player"]) > div[data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 33% !important; }
  div[data-testid="stHorizontalBlock"]:has([class*="st-key-performance_area_"]) { flex-wrap: nowrap !important; gap: .2rem !important; }
  div[data-testid="stHorizontalBlock"]:has([class*="st-key-performance_area_"]) > div[data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 25% !important; }
  div[class*="st-key-performance_area_"] button { width: 46px !important; height: 46px !important; }
}
/* Four navigation tabs remain readable on a narrow phone. */
@media (max-width: 700px) {
  .block-container { padding: .65rem .65rem 2rem !important; }
  .sh-hero { padding: 18px 16px; margin-bottom: 12px; border-radius: 11px; }
  .sh-name { font-size: 1.8rem; }
  .sh-hero-footer { font-size: .68rem; margin-top: 12px; }
  .stTabs [data-baseweb="tab-list"] { gap: 0 !important; overflow-x: auto; }
  .stTabs [data-baseweb="tab"] { font-size: .75rem !important; padding: .5rem .4rem !important; min-width: 0 !important; flex: 1 1 25%; white-space: nowrap; }
  [data-testid="stMetric"] { padding: 9px !important; }
  [data-testid="stMetricValue"] { font-size: 1.25rem !important; }
  [data-testid="stMetricLabel"] { font-size: .75rem !important; }
  [data-testid="stDataFrame"] { max-width: 100%; }
  h2, h3 { margin-top: .65rem !important; }
}
</style>
""", unsafe_allow_html=True)

# Four main sections; specialised tools are selected within each section.
tab_snapshot, tab_matches, tab_squad, tab_explorer, tab_fun = st.tabs(
    ["Club Overview", "Matches", "Squad", "Data Explorer", "Fun Stats"]
)

with tab_snapshot:
        st.subheader("Club Overview")
        if st.session_state.get("last_sync_count"):
            st.caption(f"Last manual sync processed {st.session_state['last_sync_count']} records.")
        overall_df = records_to_df([overall] if isinstance(overall, dict) else overall)
        def get_value(df, names):
            col = first_existing(df, names)
            if col and not df.empty:
                val = df.iloc[0][col]
                return val if pd.notna(val) else "—"
            return "—"
        snapshot_metrics = [
            ("Played", get_value(overall_df, ["gamesPlayed", "games", "matchesPlayed", "appearances"])),
            ("Wins", get_value(overall_df, ["wins", "gamesWon"])),
            ("Goals scored", get_value(overall_df, ["goals", "goalsFor", "goalsScored"])),
            ("Skill rating", get_value(overall_df, ["skillRating", "rating"])),
        ]
        for idx in range(0, len(snapshot_metrics), 2):
            left, right = st.columns(2, gap="small")
            for col, (label, value) in zip((left, right), snapshot_metrics[idx:idx + 2]):
                col.metric(label, value)

        st.subheader("Recorded results")
        if structured_matches_error:
            st.warning(f"Could not load match results: {structured_matches_error}")
        elif all_matches.empty:
            st.info("No archived match results are available yet.")
        else:
            results = all_matches["result_label"].dropna()
            result_counts = pd.DataFrame({
                "Result": ["Wins", "Draws", "Losses"],
                "Matches": [int(results.eq("W").sum()), int(results.eq("D").sum()), int(results.eq("L").sum())],
            })
            counted = int(result_counts["Matches"].sum())
            if counted:
                result_counts["Percentage"] = (result_counts["Matches"] / counted * 100).round(1)
                result_counts["Label"] = result_counts.apply(
                    lambda r: f"{r['Result']} {r['Percentage']:.1f}%", axis=1
                )
                donut = (alt.Chart(result_counts).mark_arc(innerRadius=75, outerRadius=118)
                    .encode(
                        theta=alt.Theta("Matches:Q", stack=True),
                        color=alt.Color("Result:N", scale=alt.Scale(
                            domain=["Wins", "Draws", "Losses"],
                            range=["#16A34A", "#9CA3AF", "#DC2626"]),
                            legend=alt.Legend(orient="bottom", title=None)),
                        tooltip=["Result:N", "Matches:Q", alt.Tooltip("Percentage:Q", format=".1f")]
                    ).properties(height=290))
                # A centre label remains readable on narrow screens; percentages
                # are placed inside their respective coloured segments.
                centre = alt.Chart(pd.DataFrame({"text": [f"{counted}\nrecorded"]})).mark_text(
                    align="center", baseline="middle", fontSize=17, fontWeight="bold", lineBreak="\n", color="white"
                ).encode(text="text:N")
                result_counts["Pct label"] = result_counts["Percentage"].map(lambda x: f"{x:.0f}%")
                pct_labels = alt.Chart(result_counts[result_counts["Matches"] > 0]).mark_text(
                    radius=97, fontSize=12, fontWeight="bold", color="white"
                ).encode(theta=alt.Theta("Matches:Q", stack=True), text="Pct label:N")
                st.altair_chart(donut + pct_labels + centre, use_container_width=True)
                st.caption("Green: wins · Grey: draws · Red: losses. Percentages appear in each segment.")
                st.caption("Based on archived matches, which may not cover the club's entire history.")
            else:
                st.info("No recognised win, draw or loss results have been archived.")

        st.subheader("Squad appearances & ratings")
        if all_performances.empty:
            st.info("No archived player performances are available yet.")
        else:
            snap = all_performances.sort_values("played_at", na_position="first").groupby("player_id", dropna=False).agg(
                Player=("player_name", "last"), Appearances=("match_id", "nunique"),
                **{"Average rating": ("rating", "mean")}
            ).reset_index(drop=True)
            snap["Average rating"] = snap["Average rating"].round(2)
            snap = snap.sort_values(["Appearances", "Player"], ascending=[False, True])
            st.dataframe(snap, hide_index=True, use_container_width=True, height=min(420, 38 * (len(snap) + 1)))

with tab_matches:
    matches_view = st.selectbox("Matches section", ["Recent Results", "Club Form", "Match Report"], key="matches_view")
    if matches_view == "Recent Results":
        st.subheader("Recent results")
        if structured_matches_error:
            st.warning(f"Could not load recent results: {structured_matches_error}")
        elif all_matches.empty:
            st.info("No archived matches yet.")
        else:
            recent = all_matches.sort_values("played_at", ascending=False).head(10)
            display = pd.DataFrame({
                "DNF": recent["dnf"].map(lambda v: "—" if pd.isna(v) else ("Yes" if str(v).lower() in ("true", "1") else "No")),
                "Result": recent["result"].fillna("—").astype(str).str.title(),
                "Goals for": recent["goals_for"].astype("Int64"),
                "Goals against": recent["goals_against"].astype("Int64"),
            })
            def shade_result(row):
                result = str(row["Result"]).lower()
                if result in ("win", "w"):
                    bg, fg = "#DCFCE7", "#166534"
                elif result in ("draw", "d", "tie"):
                    bg, fg = "#F1F2F4", "#30343B"
                elif result in ("loss", "lose", "l"):
                    bg, fg = "#FEE2E2", "#991B1B"
                else:
                    bg, fg = "transparent", "inherit"
                return [f"background-color: {bg}; color: {fg}" for _ in row]
            st.dataframe(display.style.apply(shade_result, axis=1), use_container_width=True, hide_index=True)
            if display["Goals against"].isna().any():
                st.caption("Opponent goals are blank where EA's archived record doesn't contain them.")

    elif matches_view == "Club Form":
        st.subheader("Club form & performance trends")
        st.caption("Based on archived results only; the rolling chart excludes unrecognised results.")
        if not all_matches.empty:
            types = sorted(all_matches["match_type"].dropna().astype(str).unique().tolist())
            chosen_types = st.multiselect("Match types", types, default=types, key="form_types")
            window = st.selectbox("Recent match window", [5, 10, 20, 50], index=1, key="form_window")
            f = all_matches[all_matches["match_type"].isin(chosen_types)].dropna(subset=["result_label"]).copy()
            if f.empty:
                st.info("No matches with recognised results match these filters.")
            else:
                recent = f.tail(window).copy()
                w = int(recent["result_label"].eq("W").sum())
                d = int(recent["result_label"].eq("D").sum())
                l = int(recent["result_label"].eq("L").sum())
                metrics = [
                    ("Recorded matches", len(recent)), ("W / D / L", f"{w} / {d} / {l}"),
                    ("Win rate", f"{w / len(recent):.1%}"),
                    ("Goals scored", int(recent["goals_for"].sum()) if recent["goals_for"].notna().all() else "Incomplete"),
                    ("Goals conceded", int(recent["goals_against"].sum()) if recent["goals_against"].notna().all() else "Unavailable / incomplete"),
                ]
                streak = 0
                for result in reversed(f["result_label"].tolist()):
                    if result == "L":
                        break
                    streak += 1
                metrics.append(("Current unbeaten streak", streak))
                for start in range(0, len(metrics), 2):
                    cols = st.columns(2)
                    for col, (label, value) in zip(cols, metrics[start:start + 2]):
                        col.metric(label, value)
                f["Win"] = f["result_label"].eq("W").astype(int)
                f["Rolling win rate (%)"] = (f["Win"].rolling(window, min_periods=1).mean() * 100).round(1)
                f["Match number"] = range(1, len(f) + 1)
                st.subheader("Rolling win percentage")
                st.line_chart(f.set_index("Match number")[["Rolling win rate (%)"]], y_label="Win rate (%)")
                st.subheader("Goals scored vs conceded")
                g = recent[["goals_for", "goals_against"]].copy()
                g.index = range(1, len(g) + 1)
                g.index.name = "Recent match (oldest first)"
                st.bar_chart(g.rename(columns={"goals_for": "Goals for", "goals_against": "Goals against"}))
                if recent["goals_against"].isna().any():
                    st.caption("Some opponent scores are unavailable; missing values are not estimated.")
    elif matches_view == "Match Report":
        st.subheader("Match report")
        if all_matches.empty:
            st.info("No archived matches are available.")
        else:
            matches_desc = all_matches.sort_values("played_at", ascending=False, na_position="last")
            ids = matches_desc["match_id"].tolist()
            def match_label(mid):
                r = matches_desc[matches_desc["match_id"] == mid].iloc[0]
                date = r["played_at"].strftime("%d %b %Y %H:%M UTC") if pd.notna(r["played_at"]) else "Date unavailable"
                return f"{date} · {r['match_type']} · {r['result_label'] if pd.notna(r['result_label']) else 'Unknown'}"
            selected_id = st.selectbox("Select a match", ids, format_func=match_label, key="centre_match")
            row = matches_desc[matches_desc["match_id"] == selected_id].iloc[0]
            a, b = st.columns(2)
            c, d = st.columns(2)
            a.metric("Result", row["result_label"] if pd.notna(row["result_label"]) else "Unknown")
            b.metric("Goals for", int(row["goals_for"]) if pd.notna(row["goals_for"]) else "—")
            c.metric("Goals against", int(row["goals_against"]) if pd.notna(row["goals_against"]) else "—")
            d.metric("DNF", "Unknown" if pd.isna(row["dnf"]) else ("Yes" if str(row["dnf"]).lower() in ("true", "1") else "No"))
            st.caption(f"Match type: {row['match_type']} · Opponent ID: {row.get('opponent_id', '—')}")
            st.subheader("Player performances")
            if all_performances.empty:
                st.info("No individual performances have been archived.")
            else:
                perf = all_performances[all_performances["match_id"] == selected_id].copy()
                if perf.empty:
                    st.info("No player performances were archived for this match.")
                else:
                    cols = ["player_name", "position", "rating", "goals", "assists", "seconds_played", "passes_made", "pass_attempts", "tackles_made", "saves", "man_of_the_match"]
                    perf["seconds_played"] = (perf["seconds_played"] / 60).round(1)
                    st.dataframe(perf[cols].rename(columns={"player_name": "Player", "position": "Position", "rating": "Rating", "goals": "Goals", "assists": "Assists", "seconds_played": "Minutes", "passes_made": "Passes", "pass_attempts": "Pass attempts", "tackles_made": "Tackles", "saves": "Saves", "man_of_the_match": "MOTM"}).sort_values("Rating", ascending=False), use_container_width=True, hide_index=True)
            with st.expander("Archived match details"):
                archived = row["raw_data"] if isinstance(row.get("raw_data"), dict) else {}
                st.json({k: v for k, v in archived.items() if k.lower() not in ("matchid", "match_id")})

with tab_squad:
    squad_view = st.selectbox(
        "Squad section", ["Squad Overview", "Performance Areas", "Player Breakdown", "Head to Head", "Awards & Rankings"],
        key="squad_view", help="Choose the squad statistics to display."
    )
    if squad_view == "Squad Overview":
        st.subheader("Squad Overview")
        st.caption("One row per player. Position filters apply to the position played in each archived match.")
        if all_performances.empty:
            st.info("No archived player performances are available.")
        else:
            frame = all_performances.copy()
            positions = sorted(frame["position"].dropna().unique().tolist())
            position = st.selectbox("Position", ["All positions"] + positions, key="squad_position")
            if position != "All positions":
                frame = frame[frame["position"] == position].copy()
            if frame.empty:
                st.info("No player performances at this position.")
            else:
                # These counters are available only when the decoded EA events contain them.
                won_keys = ("possessionWonDefensiveThird", "possessionWonMiddleThird", "possessionWonAttackingThird")
                lost_keys = ("possessionLostDefensiveThird", "possessionLostMiddleThird", "possessionLostAttackingThird")
                def total_pitch_events(raw, keys):
                    values = [event_counter(raw, [key]) for key in keys]
                    return sum(values) if all(pd.notna(v) for v in values) else float("nan")
                if "raw_data" in frame.columns:
                    frame["possession_won"] = frame["raw_data"].apply(lambda raw: total_pitch_events(raw, won_keys))
                    frame["possession_lost"] = frame["raw_data"].apply(lambda raw: total_pitch_events(raw, lost_keys))
                else:
                    frame["possession_won"] = float("nan")
                    frame["possession_lost"] = float("nan")
                frame = frame.sort_values("played_at", na_position="first")
                rows = []
                for pid, group in frame.groupby("player_id", dropna=False):
                    apps = group["match_id"].nunique()
                    goals = group["goals"].sum(min_count=1)
                    assists = group["assists"].sum(min_count=1)
                    shots = group["shots"].sum(min_count=1)
                    position_counts = group["position"].value_counts()
                    most_played = position_counts.index[0] if not position_counts.empty else "—"
                    won = group["possession_won"]
                    lost = group["possession_lost"]
                    rows.append({
                        "_player_id": str(pid),
                        "Player": group["player_name"].iloc[-1],
                        "Appearances": apps,
                        "Most played position": most_played,
                        "Average rating": round(group["rating"].mean(), 2) if group["rating"].notna().any() else None,
                        "Goals": int(goals) if pd.notna(goals) else None,
                        "Conversion rate": round(100 * goals / shots, 1) if pd.notna(goals) and pd.notna(shots) and shots > 0 else None,
                        "Assists": int(assists) if pd.notna(assists) else None,
                        "Goal involvements / game": round((goals + assists) / apps, 2) if apps and pd.notna(goals) and pd.notna(assists) else None,
                        "Possession won / game": round(won.sum() / apps, 2) if apps and won.notna().all() else None,
                        "Possession lost / game": round(lost.sum() / apps, 2) if apps and lost.notna().all() else None,
                    })
                squad_overview = pd.DataFrame(rows).sort_values(["Appearances", "Player"], ascending=[False, True])
                st.caption("Mobile summary — select a player row for more information; expand for all metrics.")
                compact_cols = ["Player", "Appearances", "Most played position", "Goals", "Assists"]
                st.dataframe(squad_overview[compact_cols], use_container_width=True, hide_index=True)
                with st.expander("Full squad statistics", expanded=False):
                    full_squad = squad_overview.copy()
                    # Include every available numeric field in stored performances and
                    # decoded raw event data. Missing values remain missing, not zero.
                    excluded = {"club_id", "match_id", "player_id", "player_name", "position",
                                "played_at", "match_type", "raw_data", "created_at", "updated_at"}
                    available = frame.reset_index(drop=True).copy()
                    if "raw_data" in available.columns:
                        flattened = pd.json_normalize(
                            [v if isinstance(v, dict) else {} for v in available["raw_data"]], sep="."
                        )
                        for field in flattened.columns:
                            if field not in excluded and field not in available.columns:
                                available[field] = flattened[field]
                    extra = {}
                    for field in available.columns:
                        if field in excluded or field in {"possession_won", "possession_lost"}:
                            continue
                        if field.lower().endswith(("id", "timestamp")):
                            continue
                        values = pd.to_numeric(available[field], errors="coerce")
                        if not values.notna().any():
                            continue
                        if values.notna().sum() != available[field].notna().sum():
                            continue  # exclude text or mixed categorical fields
                        extra[field] = values
                    if extra:
                        expanded = pd.DataFrame(extra)
                        expanded["player_id"] = available["player_id"].to_numpy()
                        # Do not count unknown event values as zeros; only aggregate
                        # counters with complete coverage for that player.
                        totals = expanded.groupby("player_id", dropna=False).agg(
                            {field: (lambda x: x.sum() if x.notna().all() else float("nan"))
                             for field in extra}
                        )
                        full_squad["_pid"] = full_squad["_player_id"]
                        for field in totals.columns:
                            name = "Total · " + field.replace(".", " / ")
                            full_squad[name] = full_squad["_pid"].map(totals[field])
                        full_squad = full_squad.drop(columns="_pid")
                    st.caption("Swipe horizontally to see all available numeric counters. Totals require complete recorded values per player; unavailable data is blank.")
                    full_squad = full_squad.drop(columns=["_player_id"], errors="ignore")
                    st.dataframe(full_squad, use_container_width=True, hide_index=True, height=430,
                        column_config={"Conversion rate": st.column_config.NumberColumn("Conversion rate", format="%.1f%%")})
                st.caption("Conversion rate = goals ÷ recorded shots. Possession rates require all three pitch-third event counters for every included appearance; missing values are left blank.")
    elif squad_view == "Performance Areas":
        st.subheader("Performance Areas")
        st.caption("Explore each player's recorded match statistics. Missing event data is never treated as zero.")
        if all_performances.empty or "player_id" not in all_performances.columns:
            st.info("No archived player performances are available yet.")
        else:
            source = all_performances.sort_values("played_at", na_position="first").copy()
            names = source.groupby("player_id")["player_name"].last().to_dict()
            player_ids = sorted(names, key=lambda pid: (str(names[pid]).casefold(), str(pid)))
            filter_player, filter_position, filter_window = st.columns(3, gap="small")
            with filter_player:
                chosen_player = st.selectbox("Player", player_ids,
                    format_func=lambda pid: str(names[pid]), key="areas_player")
            player_data = source[source["player_id"] == chosen_player].copy()
            available_positions = sorted(player_data["position"].dropna().unique().tolist())
            with filter_position:
                selected_position = st.selectbox("Position", ["All positions"] + available_positions,
                    key="areas_position")
            if selected_position != "All positions":
                player_data = player_data[player_data["position"] == selected_position].copy()
            with filter_window:
                match_window = st.selectbox(
                    "Match Window", ["All Time", "Last 10", "Last 5", "Last Game"],
                    key="areas_match_window",
                )
            # Select the most recent performances for this player and position.
            # Tie-break on match ID for a stable order when timestamps coincide.
            if match_window != "All Time":
                window_size = {"Last 10": 10, "Last 5": 5, "Last Game": 1}[match_window]
                player_data = (player_data.sort_values(
                    ["played_at", "match_id"], ascending=[False, False], na_position="last"
                ).head(window_size).copy())
            st.caption(f"Showing {len(player_data)} recorded appearance(s) for this selection.")
            if "performance_area" not in st.session_state:
                st.session_state["performance_area"] = "Possession"
            area_icons = [("Possession", "⚽"), ("Shooting", "🎯"),
                          ("Passing", "↗"), ("Defending", "🛡")]
            st.markdown("""<style>
            div[class*="st-key-performance_area_"] button {
                width: 64px !important; height: 64px !important;
                border-radius: 50% !important; padding: 3px !important;
                border: 2px solid #C8102E !important;
                font-size: 1.5rem !important; margin: 0 auto !important;
            }
            div[class*="st-key-performance_area_"] button[kind="primary"] {
                background: #C8102E !important; color: white !important;
            }
            @media (max-width: 700px) {
                div[class*="st-key-performance_area_"] button {
                    width: 56px !important; height: 56px !important;
                }
            }
            </style>""", unsafe_allow_html=True)
            area_cols = st.columns(4, gap="small")
            for col, (area_name, symbol) in zip(area_cols, area_icons):
                with col:
                    if st.button(symbol, key=f"performance_area_{area_name.lower()}",
                                 type="primary" if st.session_state["performance_area"] == area_name else "secondary",
                                 help=area_name, use_container_width=True):
                        st.session_state["performance_area"] = area_name
                    st.markdown(f"<div style='text-align:center;font-size:.75rem;font-weight:600'>{area_name}</div>",
                                unsafe_allow_html=True)
            area = st.session_state["performance_area"]
            st.markdown(f"#### {area} breakdown")

            # Flatten only this player's actual archived raw event fields.
            # Retain the original field keys for auditing and avoid invented counters.
            raw_values = player_data.get("raw_data", pd.Series([{}] * len(player_data), index=player_data.index))
            raw_flat = pd.json_normalize(
                [v if isinstance(v, dict) else {} for v in raw_values], sep="."
            ).reset_index(drop=True)
            base = player_data.reset_index(drop=True)
            numeric_fields = {}
            for field in ("goals", "assists", "shots", "saves", "passes_made", "pass_attempts",
                          "tackles_made", "tackle_attempts", "clean_sheet", "red_cards",
                          "man_of_the_match", "rating", "seconds_played"):
                if field in base.columns:
                    numeric_fields[field] = pd.to_numeric(base[field], errors="coerce")
            for field in raw_flat.columns:
                # Never include IDs, dates, metadata, percentages already derived by EA,
                # or unlabelled numerical codes as performance totals.
                tail = field.rsplit(".", 1)[-1]
                lower = tail.lower()
                if (lower.endswith(("id", "timestamp")) or lower in
                    {"rating", "goals", "assists", "shots", "saves", "position", "matchtype",
                     "playername", "secondsplayed", "clubid", "playerid", "matchid"}):
                    continue
                vals = pd.to_numeric(raw_flat[field], errors="coerce")
                if vals.notna().any() and (vals.dropna() >= 0).all() and not ("." in field and field.split(".")[0].lower() in ("metadata", "player")):
                    numeric_fields.setdefault(field, vals)

            def area_for(field):
                key = field.rsplit(".", 1)[-1].lower().replace("_", "")
                if any(t in key for t in ("possession", "dispossess", "balllost", "ballwon", "turnover", "recover")):
                    return "Possession"
                if any(t in key for t in ("shot", "goal", "finish", "header", "weakfoot", "volley", "penaltyscored")):
                    return "Shooting"
                if any(t in key for t in ("pass", "assist", "cross", "throughball", "switchplay", "keyball")):
                    return "Passing"
                if any(t in key for t in ("tackle", "intercept", "block", "clearance", "aerial", "duel",
                                         "save", "cleansheet", "clean_sheet", "marking", "defend", "foul", "redcard")):
                    return "Defending"
                return None

            def nice_name(field):
                tail = field.rsplit(".", 1)[-1]
                known = {
                    "passes_made": "Completed passes", "pass_attempts": "Pass attempts",
                    "tackles_made": "Successful tackles", "tackle_attempts": "Tackle attempts",
                    "clean_sheet": "Clean sheets", "red_cards": "Red cards",
                    "possessionWonDefensiveThird": "Possession won — defensive third",
                    "possessionWonMiddleThird": "Possession won — middle third",
                    "possessionWonAttackingThird": "Possession won — attacking third",
                    "possessionLostDefensiveThird": "Possession lost — defensive third",
                    "possessionLostMiddleThird": "Possession lost — middle third",
                    "possessionLostAttackingThird": "Possession lost — attacking third",
                }
                if tail in known:
                    return known[tail]
                spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", tail.replace("_", " "))
                return spaced[:1].upper() + spaced[1:]

            selected_stats = []
            for field, values in numeric_fields.items():
                if area_for(field) != area:
                    continue
                coverage = int(values.notna().sum())
                total_matches = len(values)
                # No partial totals: otherwise a player with old missing event records
                # could be presented as having lower totals than they actually do.
                total = float(values.sum()) if coverage == total_matches and total_matches else None
                selected_stats.append({"Statistic": nice_name(field), "Total": total,
                                       "Per game": round(total / total_matches, 2) if total is not None else None,
                                       "Recorded matches": coverage, "Total matches": total_matches,
                                       "EA field": field})
            stats_table = pd.DataFrame(selected_stats)
            if stats_table.empty:
                st.info(f"No {area.lower()} counters are present in the selected player's archived records.")
            else:
                # Deduplicate names by retaining source keys in the detailed table.
                def stat_total(key):
                    matches = stats_table.loc[stats_table["EA field"] == key, "Total"]
                    return matches.iloc[0] if not matches.empty else None
                area_kpis = {
                    "Possession": [("Defensive recoveries", "possessionWonDefensiveThird"),
                                   ("Midfield recoveries", "possessionWonMiddleThird"),
                                   ("Attacking recoveries", "possessionWonAttackingThird")],
                    "Shooting": [("Goals", "goals"), ("Shots", "shots")],
                    "Passing": [("Completed passes", "passes_made"), ("Assists", "assists")],
                    "Defending": [("Successful tackles", "tackles_made"), ("Saves", "saves")],
                }
                cards = area_kpis[area]
                for start in range(0, len(cards), 2):
                    cols = st.columns(2)
                    for col, (label, key) in zip(cols, cards[start:start + 2]):
                        val = stat_total(key)
                        col.metric(label, f"{val:,.0f}" if val is not None and pd.notna(val) else "—")
                if area == "Shooting":
                    goals, shots = stat_total("goals"), stat_total("shots")
                    if goals is not None and shots is not None and shots > 0:
                        st.metric("Shot conversion", f"{100 * goals / shots:.1f}%")
                elif area == "Passing":
                    completed, attempted = stat_total("passes_made"), stat_total("pass_attempts")
                    if completed is not None and attempted is not None and attempted > 0:
                        st.metric("Pass accuracy", f"{100 * completed / attempted:.1f}%")
                elif area == "Defending":
                    completed, attempted = stat_total("tackles_made"), stat_total("tackle_attempts")
                    if completed is not None and attempted is not None and attempted > 0:
                        st.metric("Tackle success", f"{100 * completed / attempted:.1f}%")

                # Chart only complete-coverage counters; do not confuse missing with zero.
                chart_data = stats_table.dropna(subset=["Total"]).copy()
                chart_data = chart_data[~chart_data["EA field"].isin(["rating", "seconds_played"])]
                if not chart_data.empty:
                    chart_data = chart_data.sort_values("Total", ascending=False).head(8)
                    plot = alt.Chart(chart_data).mark_bar(color="#C8102E").encode(
                        x=alt.X("Total:Q", title="Recorded actions"),
                        y=alt.Y("Statistic:N", sort="-x", title=None),
                        tooltip=["Statistic:N", alt.Tooltip("Total:Q", format=",.0f")],
                    ).properties(height=max(180, len(chart_data) * 34))
                    st.altair_chart(plot, use_container_width=True)
                st.subheader(f"All {area.lower()} statistics")
                st.caption("Every recognised numeric counter in this category from the selected player's stored records. "
                           "Totals and per-game figures are blank when any included match lacks that counter. "
                           "Swipe the table sideways to inspect source fields and data coverage.")
                st.dataframe(stats_table.sort_values("Statistic").reset_index(drop=True),
                             use_container_width=True, hide_index=True, height=460,
                             column_config={
                                 "Total": st.column_config.NumberColumn("Total", format="%.1f"),
                                 "Per game": st.column_config.NumberColumn("Per game", format="%.2f"),
                                 "EA field": st.column_config.TextColumn("Original EA field"),
                             })
    elif squad_view == "Player Breakdown":
            st.subheader("StereoHearts FC — player profiles")
            st.caption("Statistics are based on archived match performances, not necessarily full career totals.")

            if stored_players.empty or "player_id" not in stored_players.columns:
                st.info("No player performances are available yet. Run an EA sync first.")
            else:
                labels = {}
                for pid, group in profiles.groupby("player_id"):
                    name = group["player_name"].iloc[-1]
                    labels[pid] = str(name)
                selected_id = st.selectbox(
                    "Player", sorted(labels, key=lambda pid: labels[pid].casefold()),
                    format_func=lambda pid: labels[pid], key="profile_player"
                )
                player_all = profiles[profiles["player_id"] == selected_id].copy()
                positions = sorted(player_all["position"].unique().tolist())
                selected_positions = st.multiselect(
                    "Position", positions, default=positions, key="profile_positions",
                    help="Only performances at the selected match positions are included."
                )
                selected_types = player_all["match_type"].unique().tolist()
                selected = player_all[
                    player_all["position"].isin(selected_positions)
                    & player_all["match_type"].isin(selected_types)
                ].copy()

                numeric = ["goals", "assists", "rating", "seconds_played", "passes_made",
                           "pass_attempts", "tackles_made", "tackle_attempts", "clean_sheet",
                           "man_of_the_match", "shots", "saves", "red_cards"]
                for field in numeric:
                    if field not in selected.columns:
                        selected[field] = pd.NA
                    selected[field] = pd.to_numeric(selected[field], errors="coerce")
                    if field not in player_all.columns:
                        player_all[field] = pd.NA
                    player_all[field] = pd.to_numeric(player_all[field], errors="coerce")

                def percentage(frame, made, attempts):
                    completed = frame[made].sum()
                    total = frame[attempts].sum()
                    return f"{100 * completed / total:.1f}%" if total > 0 else "—"

                if selected.empty:
                    st.info("No performances match these filters. Choose at least one position.")
                else:
                    appearances = selected["match_id"].nunique()
                    avg_rating = selected["rating"].mean()
                    metrics = [
                        ("Appearances", f"{appearances}"),
                        ("Goals", f"{int(selected['goals'].sum())}"),
                        ("Assists", f"{int(selected['assists'].sum())}"),
                        ("Average rating", f"{avg_rating:.2f}" if pd.notna(avg_rating) else "—"),
                        ("Minutes", f"{selected['seconds_played'].sum() / 60:.1f}"),
                        ("Player of match", f"{int(selected['man_of_the_match'].sum())}"),
                        ("Clean sheets", f"{int(selected['clean_sheet'].sum())}"),
                        ("Pass accuracy", percentage(selected, "passes_made", "pass_attempts")),
                        ("Tackle success", percentage(selected, "tackles_made", "tackle_attempts")),
                    ]
                    for start in range(0, len(metrics), 3):
                        columns = st.columns(3)
                        for column, (label, value) in zip(columns, metrics[start:start + 3]):
                            column.metric(label, value)

                    st.subheader("Match rating trend")
                    rating_history = selected.sort_values("played_at").copy()
                    rating_history = rating_history.dropna(subset=["rating"])
                    if rating_history.empty:
                        st.info("No match ratings are available for this selection.")
                    else:
                        rating_history["Match"] = range(1, len(rating_history) + 1)
                        trend = alt.Chart(rating_history).encode(
                            x=alt.X("Match:Q", axis=alt.Axis(tickMinStep=1)),
                            y=alt.Y("rating:Q", title="Match rating", scale=alt.Scale(zero=False)),
                            tooltip=[alt.Tooltip("Match:Q"), alt.Tooltip("rating:Q", format=".2f")],
                        )
                        st.altair_chart(
                            (trend.mark_line(color="#C8102E") + trend.mark_circle(size=85, color="#C8102E"))
                            .properties(height=260), use_container_width=True
                        )

                    st.subheader("Performance by position")
                    # Position comparison uses all match types but does not restrict to the
                    # selected position(s), so comparisons remain meaningful.
                    comparison_source = player_all[player_all["match_type"].isin(selected_types)]
                    summary = comparison_source.groupby("position", dropna=False).agg(
                        Appearances=("match_id", "nunique"),
                        Goals=("goals", "sum"),
                        Assists=("assists", "sum"),
                        Rating=("rating", "mean"),
                        Minutes=("seconds_played", "sum"),
                        Passes=("passes_made", "sum"),
                        Attempts=("pass_attempts", "sum"),
                    ).reset_index().rename(columns={"position": "Position"})
                    summary["Minutes"] = (summary["Minutes"] / 60).round(1)
                    summary["Rating"] = summary["Rating"].round(2)
                    summary["Pass %"] = (100 * summary["Passes"] / summary["Attempts"].replace(0, float("nan"))).round(1)
                    st.dataframe(summary[["Position", "Appearances", "Goals", "Assists", "Rating", "Minutes", "Pass %"]],
                                 use_container_width=True, hide_index=True)
                    st.caption("Position comparison includes all positions for the selected match types.")

                    st.subheader("Match-by-match performances")
                    columns = ["position", "rating", "goals", "assists",
                               "seconds_played", "passes_made", "pass_attempts", "tackles_made",
                               "tackle_attempts", "saves"]
                    history = selected.sort_values("played_at", ascending=False)[columns].copy()
                    history["seconds_played"] = (history["seconds_played"] / 60).round(1)
                    history.columns = ["Position", "Rating", "Goals", "Assists",
                                       "Minutes", "Passes", "Pass attempts", "Tackles", "Tackle attempts", "Saves"]
                    st.dataframe(history, use_container_width=True, hide_index=True)


        # Head-to-head player comparisons use the same archived, structured performances.
    elif squad_view == "Head to Head":
            st.subheader("Head-to-head player comparison")
            st.caption("Compare two squad members across all archived match types, with an optional shared position filter.")
            if profiles.empty or profiles["player_id"].nunique() < 2:
                st.info("At least two players with archived match performances are needed for comparisons.")
            else:
                latest_names = (profiles.sort_values("played_at", na_position="first")
                                .groupby("player_id")["player_name"].last().to_dict())
                player_ids = sorted(latest_names, key=lambda pid: (str(latest_names[pid]).casefold(), pid))
                left, right = st.columns(2)
                with left:
                    player_a = st.selectbox("Player A", player_ids, index=0,
                                            format_func=lambda pid: f"{latest_names[pid]} (ID {pid})", key="compare_a")
                with right:
                    player_b = st.selectbox("Player B", player_ids, index=1,
                                            format_func=lambda pid: f"{latest_names[pid]} (ID {pid})", key="compare_b")
                if player_a == player_b:
                    st.warning("Select two different players to compare.")
                else:
                    both = profiles[profiles["player_id"].isin([player_a, player_b])].copy()
                    positions = sorted(both["position"].unique().tolist())
                    selected_positions_cmp = st.multiselect("Position", positions, default=positions,
                        key="compare_positions", help="Only performances at the selected positions count for either player.")
                    both = both[both["position"].isin(selected_positions_cmp)].copy()
                    fields = ["goals", "assists", "rating", "seconds_played", "passes_made", "pass_attempts",
                              "tackles_made", "tackle_attempts", "clean_sheet", "man_of_the_match", "shots", "saves"]
                    for field in fields:
                        if field not in both.columns:
                            both[field] = pd.NA
                        both[field] = pd.to_numeric(both[field], errors="coerce")
                    def compare_summary(pid):
                        frame = both[both["player_id"] == pid]
                        apps = frame["match_id"].nunique()
                        total_passes = frame["pass_attempts"].sum()
                        total_tackles = frame["tackle_attempts"].sum()
                        return {
                            "Appearances": apps,
                            "Goals": int(frame["goals"].sum()),
                            "Assists": int(frame["assists"].sum()),
                            "Goals / game": round(frame["goals"].sum() / apps, 2) if apps else None,
                            "Assists / game": round(frame["assists"].sum() / apps, 2) if apps else None,
                            "Average rating": round(frame["rating"].mean(), 2) if frame["rating"].notna().any() else None,
                            "Minutes": round(frame["seconds_played"].sum() / 60, 1),
                            "Pass accuracy %": round(100 * frame["passes_made"].sum() / total_passes, 1) if total_passes > 0 else None,
                            "Tackle success %": round(100 * frame["tackles_made"].sum() / total_tackles, 1) if total_tackles > 0 else None,
                            "Clean sheets": int(frame["clean_sheet"].sum()),
                            "Player of match": int(frame["man_of_the_match"].sum()),
                            "Shots": int(frame["shots"].sum()),
                            "Saves": int(frame["saves"].sum()),
                        }
                    summary_a, summary_b = compare_summary(player_a), compare_summary(player_b)
                    comparison = pd.DataFrame({
                        "Metric": list(summary_a.keys()),
                        str(latest_names[player_a]): list(summary_a.values()),
                        str(latest_names[player_b]): list(summary_b.values()),
                    })
                    def highlight_comparison(row):
                        a_val = pd.to_numeric(row.iloc[1], errors="coerce")
                        b_val = pd.to_numeric(row.iloc[2], errors="coerce")
                        styles = ["", "", ""]
                        if pd.notna(a_val) and pd.notna(b_val) and a_val != b_val:
                            # More is better for every displayed comparison metric.
                            winner = 1 if a_val > b_val else 2
                            loser = 2 if winner == 1 else 1
                            styles[winner] = "background-color: #DCFCE7; color: #166534"
                            styles[loser] = "background-color: #FEE2E2; color: #991B1B"
                        return styles
                    st.dataframe(comparison.style.apply(highlight_comparison, axis=1),
                                 hide_index=True, use_container_width=True)
                    st.caption("Green is the higher value, red is the lower value; ties and unavailable values remain neutral. Goals and assists per game use recorded appearances. Pass and tackle rates use summed successful actions divided by summed attempts. Blank values mean no usable data.")
                    st.subheader("Match ratings over time")
                    chart = both.dropna(subset=["rating", "played_at"]).sort_values("played_at").copy()
                    if chart.empty:
                        st.info("No dated match ratings available for this selection.")
                    else:
                        chart["Player"] = chart["player_id"].map({player_a: str(latest_names[player_a]), player_b: str(latest_names[player_b])})
                        chart["Appearance"] = chart.groupby("player_id").cumcount() + 1
                        st.line_chart(chart.pivot_table(index="Appearance", columns="Player", values="rating", aggfunc="mean"),
                                      y_label="Match rating")
                        st.caption("Appearance numbers are sequential for each player, not necessarily the same fixtures.")


        # Additional analytics use the same archived match and performance rows as the original tabs.
    else:
        st.subheader("Squad awards & leaderboards")
        st.caption("Awards use archived individual performances. Appearance minimum applies to every award.")
        if all_performances.empty:
            st.info("No player performances are available.")
        else:
            types = sorted(all_performances["match_type"].dropna().astype(str).unique().tolist())
            chosen = st.multiselect("Match types", types, default=types, key="awards_types")
            minimum = st.number_input("Minimum appearances", min_value=1, max_value=1000, value=3, step=1, key="awards_min")
            frame = all_performances[all_performances["match_type"].isin(chosen)].copy()
            if frame.empty:
                st.info("No performances match these match types.")
            else:
                frame = frame.sort_values("played_at", na_position="first")
                ranks = frame.groupby("player_id").agg(
                    Player=("player_name", "last"), Appearances=("match_id", "nunique"), Goals=("goals", "sum"),
                    Assists=("assists", "sum"), Rating=("rating", "mean"), Clean_sheets=("clean_sheet", "sum"),
                    MOTM=("man_of_the_match", "sum"), Tackles=("tackles_made", "sum"), Saves=("saves", "sum"),
                    Minutes=("seconds_played", "sum")
                ).reset_index()
                ranks = ranks[ranks["Appearances"] >= minimum].copy()
                if ranks.empty:
                    st.info("No players meet the minimum appearance requirement.")
                else:
                    awards = [("Golden Boot", "Goals"), ("Playmaker", "Assists"), ("Highest average rating", "Rating"),
                              ("Clean-sheet leader", "Clean_sheets"), ("Most tackles", "Tackles"),
                              ("Most saves", "Saves"), ("Most appearances", "Appearances"), ("Player of the match awards", "MOTM")]
                    for start in range(0, len(awards), 2):
                        columns = st.columns(2)
                        for col, (label, metric) in zip(columns, awards[start:start + 2]):
                            eligible = ranks.dropna(subset=[metric]).sort_values([metric, "Appearances", "Player"], ascending=[False, False, True])
                            if not eligible.empty:
                                best = eligible.iloc[0]
                                col.metric(label, str(best["Player"]), help=f"{metric}: {best[metric]:.2f}" if metric == "Rating" else f"{metric}: {best[metric]:g}")
                    ranks["Rating"] = ranks["Rating"].round(2)
                    ranks["Minutes"] = (ranks["Minutes"] / 60).round(1)
                    ranks = ranks.rename(columns={"Clean_sheets": "Clean sheets", "MOTM": "MOTM awards"})
                    metric = st.selectbox("Leaderboard ranking", ["Goals", "Assists", "Rating", "Clean sheets", "Tackles", "Saves", "Appearances", "MOTM awards"], key="awards_rank")
                    st.dataframe(ranks.sort_values([metric, "Appearances"], ascending=False).drop(columns=["player_id"]), use_container_width=True, hide_index=True)
                    st.caption("Defensive awards show recorded totals, not a judgement of defensive quality. Equal scores are broken by appearances.")
        with st.expander("Additional archived leaderboards", expanded=False):
                st.subheader("StereoHearts FC — match analytics")
                st.caption("Figures cover only matches saved in Supabase, not necessarily the club's full FC 27 history.")

                if stored_matches.empty:
                    st.info("No structured matches yet. Run Sync latest EA data in the sidebar.")
                else:
                    stored_matches["played_at"] = pd.to_datetime(stored_matches["played_at"], utc=True, errors="coerce")
                    match_types = sorted(stored_matches["match_type"].dropna().astype(str).unique().tolist())
                    selected_types = st.multiselect("Match types", match_types, default=match_types, key="analytics_types")
                    filtered_matches = stored_matches[stored_matches["match_type"].isin(selected_types)].copy()
                    filtered_matches = filtered_matches.sort_values("played_at", ascending=False)
                    match_ids = set(filtered_matches["match_id"].astype(str))

                    if not stored_players.empty:
                        filtered_players = stored_players[stored_players["match_id"].astype(str).isin(match_ids)].copy()
                    else:
                        filtered_players = pd.DataFrame()

                    # Position applies to individual match performances, not club-level results.
                    if not filtered_players.empty:
                        filtered_players["position"] = filtered_players["position"].fillna("Unknown").astype(str)
                        positions = sorted(filtered_players["position"].unique().tolist())
                        selected_positions = st.multiselect(
                            "Player positions", positions, default=positions,
                            key="analytics_positions",
                            help="Filters the player leaderboard by position played in each match. Team results are unaffected.",
                        )
                        filtered_players = filtered_players[
                            filtered_players["position"].isin(selected_positions)
                        ].copy()

                    results = filtered_matches["result"].fillna("").astype(str).str.lower()
                    wins = int(results.eq("win").sum())
                    draws = int(results.eq("draw").sum())
                    losses = int(results.eq("loss").sum())
                    total = len(filtered_matches)
                    goals = pd.to_numeric(filtered_matches["goals"], errors="coerce").fillna(0).sum()
                    a, b = st.columns(2)
                    c, d = st.columns(2)
                    a.metric("Archived matches", total)
                    b.metric("W / D / L", f"{wins} / {draws} / {losses}")
                    c.metric("Win rate", f"{wins / total:.1%}" if total else "—")
                    d.metric("Goals per match", f"{goals / total:.2f}" if total else "—")

                    st.subheader("Recent form")
                    form = filtered_matches.head(10)[["played_at", "match_type", "result", "goals", "opponent_id"]].copy()
                    form.columns = ["Date", "Type", "Result", "Goals", "Opponent ID"]
                    st.dataframe(form, use_container_width=True, hide_index=True)

                    st.subheader("Player leaderboard")
                    if filtered_players.empty:
                        st.info("No individual performances have been archived for the selected matches.")
                    else:
                        numeric_fields = ["goals", "assists", "seconds_played", "passes_made", "pass_attempts", "tackles_made", "tackle_attempts", "clean_sheet", "man_of_the_match", "rating", "saves", "shots"]
                        for field in numeric_fields:
                            if field not in filtered_players:
                                filtered_players[field] = 0
                            filtered_players[field] = pd.to_numeric(filtered_players[field], errors="coerce")

                        # Deduplicate at the match/player level before aggregating.
                        filtered_players = filtered_players.drop_duplicates(subset=["match_id", "player_id"])
                        player_summary = filtered_players.groupby("player_id", dropna=False).agg(
                            Player=("player_name", "last"),
                            Appearances=("match_id", "nunique"),
                            Goals=("goals", "sum"),
                            Assists=("assists", "sum"),
                            Minutes=("seconds_played", "sum"),
                            Rating=("rating", "mean"),
                            MOTM=("man_of_the_match", "sum"),
                            Clean_sheets=("clean_sheet", "sum"),
                            Passes_made=("passes_made", "sum"),
                            Pass_attempts=("pass_attempts", "sum"),
                            Tackles_made=("tackles_made", "sum"),
                            Tackle_attempts=("tackle_attempts", "sum"),
                        ).reset_index()
                        player_summary["Minutes"] = (player_summary["Minutes"] / 60).round(1)
                        player_summary["Rating"] = player_summary["Rating"].round(2)
                        player_summary["Pass %"] = (100 * player_summary["Passes_made"] / player_summary["Pass_attempts"].replace(0, float("nan"))).round(1)
                        player_summary["Tackle %"] = (100 * player_summary["Tackles_made"] / player_summary["Tackle_attempts"].replace(0, float("nan"))).round(1)
                        player_summary = player_summary.rename(columns={"MOTM": "Player of match", "Clean_sheets": "Clean sheets"})
                        display_columns = ["Player", "Appearances", "Goals", "Assists", "Rating", "Minutes", "Player of match", "Clean sheets", "Pass %", "Tackle %"]
                        sort_metric = st.selectbox("Rank players by", ["Goals", "Assists", "Appearances", "Rating", "Player of match", "Pass %", "Tackle %"], key="analytics_sort")
                        leaderboard = player_summary.sort_values([sort_metric, "Appearances"], ascending=False, na_position="last")
                        st.dataframe(leaderboard[display_columns], use_container_width=True, hide_index=True)
                        st.caption("Pass and tackle percentages use total successful actions divided by total attempts. Missing attempts display as blank. Average rating is per recorded appearance.")

with tab_explorer:
    explorer_view = st.selectbox(
        "Explore statistics", ["Statistics Explorer", "Advanced Analytics", "Deep Stats", "Raw Data"],
        key="explorer_view", help="Technical and advanced statistics live here."
    )
    if explorer_view == "Statistics Explorer":
            st.subheader("Complete match statistics explorer")
            st.caption("Available fields from stored EA player records. Opponents are kept separate from StereoHearts FC totals. Missing values are not treated as zero.")
            side = st.radio("Players", ["StereoHearts FC", "Opponents"], horizontal=True, key="explorer_side")
            if side == "StereoHearts FC":
                explorer = all_performances.copy()
            else:
                try:
                    explorer = pd.DataFrame(read_all_rows("opponent_player_stats", CLUB_ID, store))
                except Exception as exc:
                    explorer = pd.DataFrame()
                    st.warning(f"Opponent table could not be loaded: {exc}")
            if explorer.empty or "raw_data" not in explorer.columns:
                st.info("No stored player records for this selection. Run the new EA sync first.")
            else:
                raw_rows = [v if isinstance(v, dict) else {} for v in explorer["raw_data"]]
                flattened = pd.json_normalize(raw_rows, sep=".")
                # Use the original row index to avoid mismatched joins.
                flattened.index = explorer.index
                all_keys = sorted(k for k in flattened.columns if k.rsplit(".", 1)[-1].lower() not in ("matchid", "match_id"))
                st.metric("Available stored fields", len(all_keys))
                search = st.text_input("Search statistic names", key="explorer_search")
                candidates = [k for k in all_keys if search.lower() in k.lower()]
                chosen = st.multiselect("Statistics to display", candidates, default=candidates[:min(8, len(candidates))], key="explorer_fields")
                players = sorted(explorer.get("player_name", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
                positions = sorted(explorer.get("position", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
                c1, c2 = st.columns(2)
                selected_players = c1.multiselect("Players", players, default=players, key="explorer_players")
                selected_positions = c2.multiselect("Positions", positions, default=positions, key="explorer_positions")
                filtered = explorer.loc[
                    explorer["player_name"].astype(str).isin(selected_players)
                    & explorer["position"].astype(str).isin(selected_positions)
                ]
                base_cols = [k for k in ("player_name", "position") if k in filtered.columns]
                view = filtered[base_cols].join(flattened[chosen], how="left")
                st.dataframe(view, use_container_width=True, hide_index=True)
                st.download_button("Download selected statistics (CSV)", view.to_csv(index=False).encode("utf-8"),
                                   file_name="stereohearts_statistics.csv", mime="text/csv")
                with st.expander("Every available field name"):
                    st.write(all_keys)
            with st.expander("Archived full EA responses"):
                st.caption("Full-column and raw-match snapshots are also archived in club_records. These can be inspected in Supabase or the Raw data tab.")

        # Decoded EA match-event counters are archived inside match_player_stats.raw_data.
        # No schema migration is required; unknown/missing event fields remain blank.
    elif explorer_view == "Advanced Analytics":
        st.subheader("Advanced player analytics")
        st.caption("Per-90 figures require recorded playing time. Only archived performances are included.")
        if all_performances.empty:
            st.info("No archived player performances are available.")
        else:
            types = sorted(all_performances["match_type"].dropna().astype(str).unique().tolist())
            positions = sorted(all_performances["position"].unique().tolist())
            a, b = st.columns(2)
            chosen_types = a.multiselect("Match types", types, default=types, key="advanced_types")
            chosen_positions = b.multiselect("Positions", positions, default=positions, key="advanced_positions")
            minimum = st.number_input("Minimum appearances", min_value=1, max_value=1000, value=3, key="advanced_min")
            frame = all_performances[all_performances["match_type"].isin(chosen_types) & all_performances["position"].isin(chosen_positions)].copy()
            if frame.empty:
                st.info("No performances match these filters.")
            else:
                frame = frame.sort_values("played_at", na_position="first")
                summary = frame.groupby("player_id").agg(
                    Player=("player_name", "last"), Appearances=("match_id", "nunique"), Goals=("goals", "sum"),
                    Assists=("assists", "sum"), Minutes=("seconds_played", "sum"), Rating=("rating", "mean"),
                    Rating_SD=("rating", "std"), Passes=("passes_made", "sum"), Pass_attempts=("pass_attempts", "sum"),
                    Tackles=("tackles_made", "sum"), Tackle_attempts=("tackle_attempts", "sum"),
                    Saves=("saves", "sum")
                ).reset_index()
                summary = summary[summary["Appearances"] >= minimum].copy()
                if summary.empty:
                    st.info("No players meet the minimum appearance requirement.")
                else:
                    summary["Minutes"] = summary["Minutes"] / 60
                    # Only compute per-90 when every appearance has a usable positive duration.
                    valid_time = frame.assign(ok=frame["seconds_played"].notna() & frame["seconds_played"].gt(0)).groupby("player_id")["ok"].all()
                    summary["Complete time"] = summary["player_id"].map(valid_time).fillna(False)
                    for field in ["Goals", "Assists", "Tackles", "Saves"]:
                        summary[f"{field} / 90"] = (summary[field] * 90 / summary["Minutes"].replace(0, float("nan"))).where(summary["Complete time"]).round(2)
                    summary["Goal contributions / 90"] = ((summary["Goals"] + summary["Assists"]) * 90 / summary["Minutes"].replace(0, float("nan"))).where(summary["Complete time"]).round(2)
                    summary["Pass accuracy %"] = (100 * summary["Passes"] / summary["Pass_attempts"].replace(0, float("nan"))).round(1)
                    summary["Tackle success %"] = (100 * summary["Tackles"] / summary["Tackle_attempts"].replace(0, float("nan"))).round(1)
                    summary["Rating consistency (SD)"] = summary["Rating_SD"].round(2)
                    summary["Average rating"] = summary["Rating"].round(2)
                    ranking = st.selectbox("Rank by", ["Goal contributions / 90", "Goals / 90", "Assists / 90", "Average rating", "Pass accuracy %", "Tackle success %", "Rating consistency (SD)"], key="advanced_rank")
                    ascending = ranking == "Rating consistency (SD)"
                    show = ["Player", "Appearances", "Minutes", "Goals / 90", "Assists / 90", "Goal contributions / 90", "Average rating", "Rating consistency (SD)", "Pass accuracy %", "Tackle success %", "Tackles / 90", "Saves / 90"]
                    st.dataframe(summary.sort_values(ranking, ascending=ascending, na_position="last")[show].round(2), use_container_width=True, hide_index=True)
                    st.caption("Lower rating standard deviation means more consistent ratings. A blank per-90 value means missing or invalid playing-time data.")
                    st.subheader("Performance by position")
                    by_position = frame.groupby("position").agg(Appearances=("match_id", "count"), Goals=("goals", "sum"), Assists=("assists", "sum"), Average_rating=("rating", "mean")).reset_index()
                    st.dataframe(by_position.rename(columns={"position": "Position", "Average_rating": "Average rating"}).round(2), use_container_width=True, hide_index=True)
    elif explorer_view == "Deep Stats":
        st.subheader("Deep match-event statistics")
        st.caption("Community-decoded EA event counters, collected from the latest sync onward. "
                   "These are not xG and may be absent from older archived matches.")
        event_labels = {
            "passesCompletedForward": "Forward passes completed",
            "passesCompleted": "Passes completed (event)",
            "possessionWonDefensiveThird": "Possession won: defensive third",
            "possessionWonMiddleThird": "Possession won: middle third",
            "possessionWonAttackingThird": "Possession won: attacking third",
            "outOfPosition": "Times out of position",
        }
        if all_performances.empty or "raw_data" not in all_performances.columns:
            st.info("No archived player event data is available yet.")
        else:
            event_rows = all_performances.copy()
            for key in event_labels:
                event_rows[key] = event_rows["raw_data"].apply(
                    lambda obj: obj.get(key) if isinstance(obj, dict) else None
                )
                event_rows[key] = pd.to_numeric(event_rows[key], errors="coerce")
            present = [key for key in event_labels if event_rows[key].notna().any()]
            if not present:
                st.info("No decoded match events are stored yet. Deploy ea_client.py, run a new EA sync, then refresh this page.")
            else:
                col1, col2 = st.columns(2)
                types = sorted(event_rows["match_type"].dropna().astype(str).unique().tolist())
                positions = sorted(event_rows["position"].dropna().astype(str).unique().tolist())
                selected_types = col1.multiselect("Match types", types, default=types, key="event_match_types")
                selected_positions = col2.multiselect("Positions", positions, default=positions, key="event_positions")
                filtered = event_rows[
                    event_rows["match_type"].isin(selected_types) & event_rows["position"].isin(selected_positions)
                ].copy()
                if filtered.empty:
                    st.info("No performances match these filters.")
                else:
                    available = [k for k in present if filtered[k].notna().any()]
                    if not available:
                        st.info("No event counters are available for this selection.")
                    else:
                        metric = st.selectbox("Rank players by", available,
                            format_func=lambda k: event_labels[k], key="event_metric")
                        # Preserve missing values as missing rather than silently interpreting them as zero.
                        grouped = filtered.groupby("player_id", dropna=False)
                        summary = grouped.agg(Player=("player_name", "last"),
                                               Appearances=("match_id", "nunique")).reset_index()
                        for key in available:
                            values = grouped[key].sum(min_count=1).reset_index(name=key)
                            summary = summary.merge(values, on="player_id", how="left")
                        summary = summary.sort_values(metric, ascending=False, na_position="last")
                        shown = summary[["Player", "Appearances"] + available].rename(columns=event_labels)
                        st.dataframe(shown, use_container_width=True, hide_index=True)
                        st.subheader("Player event history")
                        players = (filtered[["player_id", "player_name"]]
                                   .drop_duplicates("player_id").sort_values("player_name"))
                        choices = players["player_id"].astype(str).tolist()
                        labels = dict(zip(players["player_id"].astype(str), players["player_name"].astype(str)))
                        selected = st.selectbox("Player", choices, format_func=lambda k: labels.get(k, k), key="event_player")
                        detail = filtered[filtered["player_id"].astype(str) == selected].copy()
                        columns = ["played_at", "match_type", "position", "rating"] + available
                        st.dataframe(detail[columns].rename(columns=event_labels).sort_values("played_at", ascending=False),
                                     use_container_width=True, hide_index=True)
                        st.caption("Only event types confirmed in the API documentation are shown here. "
                                   "Totals reflect archived appearances, not all-time EA career statistics.")
    else:
            st.subheader("Stored source records")
            st.caption("This view exposes the underlying EA response records for troubleshooting and future analytics.")
            for key in ["club_details", "overall_stats", "member_stats", "matches", "match_players"]:
                with st.expander(key.replace("_", " ").title()):
                    st.json(data.get(key, [] if key.endswith("s") else {}))


        # Structured analytics are loaded independently of the raw EA snapshot archive.


# Fun Stats: genuine awards are computed only from complete relevant archived values.
# Fixed awards are intentionally jokes and never presented as computed results.
with tab_fun:
    st.subheader("Fun Stats")
    st.caption("Eight data-driven awards and four deliberately fixed club in-jokes. Missing EA counters never count as zero.")
    genuine = []
    def add_award(name, winner=None, detail="Insufficient reliable archived data", score=None):
        genuine.append((name, winner or "Not available", detail, score))

    perf = all_performances.copy()
    if not perf.empty and not all_matches.empty:
        perf = perf.merge(all_matches[["match_id", "result_label"]].drop_duplicates("match_id"), on="match_id", how="left", suffixes=("", "_club"))
    def winner_from(series, highest=True):
        series = series.dropna().sort_values(ascending=not highest)
        if series.empty:
            return None, None
        pid = series.index[0]
        subset = perf[perf["player_id"] == pid]
        name = str(subset.sort_values("played_at")["player_name"].iloc[-1]) if not subset.empty else str(pid)
        return name, float(series.iloc[0])

    if not perf.empty:
        # Share of team goal involvements in each appearance, not club-wide career totals.
        if {"goals", "assists", "match_id"}.issubset(perf.columns):
            valid = perf.dropna(subset=["goals", "assists"]).copy()
            complete_ids = valid.groupby("match_id").size()
            total_ids = perf.groupby("match_id").size()
            valid = valid[valid["match_id"].isin(complete_ids[complete_ids == total_ids].index)]
            if not valid.empty:
                valid["contribution"] = valid["goals"] + valid["assists"]
                totals = valid.groupby("match_id")["contribution"].transform("sum")
                valid = valid[totals > 0].copy()
                if not valid.empty:
                    valid["share"] = valid["contribution"] / valid.groupby("match_id")["contribution"].transform("sum")
                    groups = valid.groupby("player_id")["share"]
                    scores = groups.mean()[groups.size() >= 5]
                    name, score = winner_from(scores)
                    add_award("Main Character Syndrome", name, "Average share of recorded team goal involvements (minimum five qualifying games)", f"{score:.1%}" if score is not None else None)
                else: add_award("Main Character Syndrome")
            else: add_award("Main Character Syndrome")
        else: add_award("Main Character Syndrome")
        if {"shots", "goals"}.issubset(perf.columns):
            valid = perf.dropna(subset=["shots", "goals"])
            grouped = valid.groupby("player_id")[["shots", "goals"]].sum()
            eligible = grouped[grouped["shots"] >= 15]
            scores = eligible["goals"] / eligible["shots"] if not eligible.empty else pd.Series(dtype=float)
            name, score = winner_from(scores, highest=False)
            add_award("Stormtrooper Award", name, "Lowest goals-per-shot conversion; minimum 15 recorded shots", f"{score:.1%}" if score is not None else None)
        else: add_award("Stormtrooper Award")
        valid = perf.dropna(subset=["rating", "played_at"]).sort_values(["played_at", "match_id"])
        changes = {}
        for pid, group in valid.groupby("player_id"):
            if len(group) >= 10:
                changes[pid] = group["rating"].iloc[-5:].mean() - group["rating"].iloc[-10:-5].mean()
        name, score = winner_from(pd.Series(changes, dtype=float))
        add_award("Purple Patch", name, "Largest improvement in average rating: last five versus previous five games", f"+{score:.2f}" if score is not None else None)
        raw = perf.get("raw_data", pd.Series([{}] * len(perf), index=perf.index))
        loss_keys = ("possessionLostDefensiveThird", "possessionLostMiddleThird", "possessionLostAttackingThird")
        lost = raw.apply(lambda value: sum_event_counters(value, loss_keys))
        losses = perf[["player_id"]].copy(); losses["lost"] = lost
        groups = losses.dropna().groupby("player_id")["lost"]
        scores = groups.mean()[groups.size() >= 5] if not losses.dropna().empty else pd.Series(dtype=float)
        name, score = winner_from(scores)
        add_award("The Black Hole", name, "Most recorded possession losses per appearance; minimum five complete appearances", f"{score:.2f}/game" if score is not None else None)
        # Do not invent weights for an agreed weighted score without a verified formula.
        add_award("The Liability", detail="Requires agreed Chaos Score weights and reliable foul, penalty and red-card counters")
        if "result_label" in perf.columns:
            match_results = perf.dropna(subset=["result_label"]).copy()
            appearances = match_results.groupby("player_id")["match_id"].nunique()
            win_rate = match_results.assign(win=match_results["result_label"].eq("W").astype(float)).groupby("player_id")["win"].mean()
            name, score = winner_from(win_rate[appearances >= 5], highest=False)
            add_award("The Curse", name, "Lowest club win percentage when appearing; minimum five games", f"{score:.1%}" if score is not None else None)
            from itertools import combinations
            pair_results = {}
            for match_id, group in match_results.groupby("match_id"):
                for a, b in combinations(sorted(group["player_id"].unique()), 2):
                    pair_results.setdefault((a, b), []).append(group["result_label"].iloc[0] == "W")
            eligible_pairs = [(pair, sum(wins)/len(wins), len(wins)) for pair, wins in pair_results.items() if len(wins) >= 10]
            if eligible_pairs:
                pair, score, games = sorted(eligible_pairs, key=lambda r: (-r[1], -r[2], r[0]))[0]
                def pname(pid):
                    return str(perf[perf["player_id"] == pid].sort_values("played_at")["player_name"].iloc[-1])
                add_award("Dynamic Duo", f"{pname(pair[0])} & {pname(pair[1])}", f"Best shared win percentage across {games} matches; minimum ten together", f"{score:.1%}")
            else: add_award("Dynamic Duo")
        else:
            add_award("The Curse"); add_award("Dynamic Duo")
    else:
        for label in ("Main Character Syndrome", "Stormtrooper Award", "Purple Patch", "The Black Hole", "The Liability", "The Curse", "Dynamic Duo"):
            add_award(label)
    # First-time goal is not safely inferable from the standard goals counter.
    add_award("Tap-in Merchant", detail="Requires a verified first-time-goal indicator and at least ten total goals")
    ordered = {name: (name, winner, detail, score) for name, winner, detail, score in genuine}
    order = ["Main Character Syndrome", "Stormtrooper Award", "Purple Patch", "The Black Hole", "The Liability", "Tap-in Merchant", "Dynamic Duo", "The Curse"]
    awards = [ordered[name] for name in order]
    awards += [
        ("The Tactical Genius", "VegNinja", "Highest tactical influence score, combining positional discipline, game management and decisive on-field instructions.", None),
        ("False Nine-to-Five", "DYLDESTRUCT", "Highest off-the-ball avoidance index, calculated from time spent away from attacking involvement during key phases.", None),
        ("Ratings Farmer", "Seannn2", "Most efficient match-rating accumulation, rewarding safe possession, low-risk actions and consistent statistical padding.", None),
        ("The Architect", "VegNinja", "Highest weighted creative contribution, combining assists, secondary assists and key passes into a Playmaking Influence Score.", None),
    ]
    # Use a real CSS grid rather than st.columns: Streamlit stacks columns
    # vertically on narrow mobile screens.
    def award_card(item, index):
        name, winner, detail, score = item
        esc = lambda value: html.escape(str(value), quote=True)
        result = f'<div class="sh-award-score">Result: {esc(score)}</div>' if score is not None else ""
        return (
            f'<article class="sh-award-card">'
            f'<div class="sh-award-title">{esc(name)}</div>'
            f'<div class="sh-award-winner">{esc(winner)}</div>'
            f'{result}'
            f'<div class="sh-award-detail">{esc(detail)}</div>'
            f'</article>'
        )

    st.markdown("""
    <style>
    .sh-awards-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        align-items: stretch;
        margin-top: 16px;
    }
    .sh-award-card {
        min-width: 0;
        border: 1px solid rgba(150,150,150,.35);
        border-top: 3px solid #C8102E;
        border-radius: 12px;
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: rgba(120,120,120,.045);
        overflow-wrap: anywhere;
    }
    .sh-award-title { font-size: 1.04rem; font-weight: 750; line-height: 1.3; }
    .sh-award-winner { font-size: 1.55rem; font-weight: 750; line-height: 1.15; margin-top: 10px; }
    .sh-award-score { font-size: .88rem; font-weight: 650; color: #d8344d; }
    .sh-award-detail { font-size: .88rem; line-height: 1.5; opacity: .82; margin-top: auto; }
    @media (max-width: 800px) {
        .sh-awards-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
        .sh-award-card { padding: 12px; gap: 9px; }
        .sh-award-title { font-size: .9rem; }
        .sh-award-winner { font-size: 1.12rem; margin-top: 5px; }
        .sh-award-detail { font-size: .77rem; }
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(
        '<div class="sh-awards-grid">' +
        "".join(award_card(item, index) for index, item in enumerate(awards)) +
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption("Four club in-joke awards have predetermined winners; their descriptions are fictional, not measured statistics.")
