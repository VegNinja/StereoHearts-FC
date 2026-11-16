import json
import base64
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


.sh-donut {position:relative;width:min(290px,80vw);aspect-ratio:1;border-radius:50%;margin:12px auto;}
.sh-donut-hole {position:absolute;inset:28%;background:#171717;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;color:white;z-index:1;}
.sh-donut-hole strong{font-size:1.5rem;line-height:1.1;}.sh-donut-hole span{font-size:.9rem;}
.sh-donut-pct {position:absolute;transform:translate(-50%,-50%);font-size:.9rem;font-weight:800;color:white;text-shadow:0 1px 3px #333;z-index:2;}
.sh-donut-legend {display:flex;gap:20px;justify-content:center;flex-wrap:wrap;margin:6px 0 20px;}
.sh-donut-legend span{display:flex;gap:7px;align-items:center;}.sh-donut-legend i{width:12px;height:12px;border-radius:50%;display:inline-block;}

/* Compact club snapshot based on the supplied reference graphic. */
.sh-club-panel {background:linear-gradient(115deg,#a50924 0%,#c8102e 68%,#e22b46 100%);border:1px solid rgba(255,255,255,.22);color:#fff;border-radius:18px;
 padding:20px;max-width:100%;margin:8px 0 24px;box-sizing:border-box;}
.sh-club-identity {display:flex;align-items:center;justify-content:space-between;gap:18px;min-width:0;}
.sh-club-photo {order:2;width:100px;height:100px;object-fit:cover;border-radius:13px;flex-shrink:0;}
.sh-club-heading {min-width:0;flex:1;}
.sh-club-heading h3 {color:#fff;margin:0 0 7px;font-size:1.55rem;}
.sh-club-badges {display:flex;gap:7px;flex-wrap:wrap;}
.sh-club-badges span {background:rgba(90,0,20,.32);color:#fff;border-radius:16px;padding:3px 9px;font-size:.78rem;}
.sh-club-record {display:flex;gap:13px;margin-top:10px;font-size:.9rem;font-weight:750;}
.sh-club-record span:nth-child(1),.sh-green {color:#79f5a6!important;}
.sh-club-record span:nth-child(2),.sh-yellow {color:#ffe082!important;}
.sh-club-record span:nth-child(3),.sh-red {color:#ffd0d7!important;}
.sh-club-heading h3 {font-weight:900!important;letter-spacing:-.045em!important;text-transform:uppercase;}
.sh-club-kpis {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin-top:17px;}
.sh-club-kpi {min-width:0;background:rgba(65,0,18,.34);border-radius:10px;text-align:center;padding:12px 4px;}
.sh-club-kpi strong {display:block;font-size:1.2rem;color:#fff;}
.sh-club-kpi small {display:block;font-size:.64rem;color:rgba(255,255,255,.8);letter-spacing:.04em;}
.sh-form-strip {display:grid;grid-template-columns:repeat(10,minmax(0,1fr));gap:5px;border-top:1px solid rgba(255,255,255,.28);margin-top:15px;padding-top:14px;}
.sh-form-result {border-radius:7px;min-width:0;text-align:center;padding:7px 4px;color:white;font-weight:800;}
.sh-form-W {background:#139d55;} .sh-form-D {background:#c98b19;} .sh-form-L {background:#d92332;}
.sh-form-empty {color:#fff;font-size:.85rem;}
@media(max-width:550px){.sh-club-panel{padding:13px;border-radius:13px;}
 .sh-club-photo{width:74px;height:74px;} .sh-club-identity{gap:11px;}
 .sh-club-heading h3{font-size:1.12rem;} .sh-club-record{gap:8px;font-size:.78rem;}
 .sh-club-kpis{gap:5px;} .sh-club-kpi{padding:9px 2px;}
 .sh-club-kpi strong{font-size:1rem;} .sh-club-kpi small{font-size:.54rem;}
 .sh-form-result{min-width:0;padding:5px 3px;}}
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

# Compact reference-style club identity panel; values are live data.
def _overall_value(keys):
    if not isinstance(overall, dict):
        return None
    for key in keys:
        if key in overall and overall[key] not in (None, ""):
            return overall[key]
    return None

def _number(value):
    result = pd.to_numeric(value, errors="coerce")
    return float(result) if pd.notna(result) else None

def _fmt(value, digits=0, suffix=""):
    return (f"{value:,.{digits}f}{suffix}" if value is not None else "—")

games = _number(_overall_value(("gamesPlayed", "games", "matchesPlayed", "appearances")))
wins = _number(_overall_value(("wins", "gamesWon")))
draws = _number(_overall_value(("draws", "gamesDrawn", "ties")))
losses = _number(_overall_value(("losses", "gamesLost")))
goals = _number(_overall_value(("goals", "goalsFor", "goalsScored")))
against = _number(_overall_value(("goalsAgainst", "goalsConceded")))
skill = _overall_value(("skillRating", "rating"))
division = _overall_value(("bestDivision", "bestDiv", "division"))
win_rate = 100 * wins / games if wins is not None and games and games > 0 else None
goal_diff = goals - against if goals is not None and against is not None else None
goals_per_game = goals / games if goals is not None and games and games > 0 else None
# Recent form uses archived chronological matches, not fabricated history.
form_window = 10  # Always show the latest 10 recorded results in the header.
form = (all_matches.dropna(subset=["result_label"]).tail(form_window)
        if not all_matches.empty else pd.DataFrame())
form_values = form["result_label"].tolist() if not form.empty else []
streak = "—"
if form_values:
    last = form_values[-1]
    streak_count = 0
    for result in reversed(form_values):
        if result != last:
            break
        streak_count += 1
    streak = f"{streak_count}{last}"
import html as _html
safe = lambda value: _html.escape(str(value), quote=True)
def _kpi(label, value, tone=""):
    return f'<div class="sh-club-kpi"><strong class="{tone}">{safe(value)}</strong><small>{safe(label)}</small></div>'
badges = "".join(f'<span class="sh-form-result sh-form-{safe(r)}">{safe(r)}</span>' for r in form_values)
if not badges:
    badges = '<span class="sh-form-empty">No archived results</span>'
header_markup = f'''<div class="sh-club-panel">
  <div class="sh-club-identity">

    <div class="sh-club-heading"><h3>StereoHearts FC</h3>
      <div class="sh-club-badges"><span>Best: {safe('Div '+str(division) if division is not None else '—')}</span>
      <span>SR: {safe(skill if skill is not None else '—')}</span></div>
      <div class="sh-club-record"><span>{safe(_fmt(wins))}W</span><span>{safe(_fmt(draws))}D</span><span>{safe(_fmt(losses))}L</span></div>
    </div>
    <img class="sh-club-photo" src="data:image/jpeg;base64,{'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'}" alt="StereoHearts FC club photo" />
  </div>
  <div class="sh-club-kpis">
    {_kpi('WIN RATE',_fmt(win_rate,1,'%'),'sh-yellow')}
    {_kpi('GOAL DIFF',('+' if goal_diff is not None and goal_diff > 0 else '')+_fmt(goal_diff),'sh-green')}
    {_kpi('GOALS/GM',_fmt(goals_per_game,2))}
    {_kpi('STREAK',streak,'sh-red')}
  </div>
  <div class="sh-form-strip">{badges}</div>
</div>'''
# Streamlit treats indented HTML lines as a Markdown code block.
# Strip indentation from every HTML line before rendering.
header_markup = "\n".join(line.lstrip() for line in header_markup.splitlines())
st.markdown(header_markup, unsafe_allow_html=True)

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
                # HTML/CSS conic donut: each label is positioned at the angular
                # midpoint of its own wedge. Avoid Altair's independent theta
                # stacking for text, which put all labels into the last wedge.
                import math
                counts = result_counts["Matches"].tolist()
                colours = ["#16A34A", "#9CA3AF", "#DC2626"]
                pct = [100 * n / counted for n in counts]
                stops, labels, cursor = [], [], 0.0
                for label, amount, colour in zip(("Wins", "Draws", "Losses"), pct, colours):
                    end = cursor + amount
                    stops.append(f"{colour} {cursor:.6f}% {end:.6f}%")
                    if amount > 0:
                        angle = math.radians((cursor + amount / 2) * 3.6)
                        # CSS conic gradients start at 12 o'clock, clockwise.
                        x = 50 + 38 * math.sin(angle)
                        y = 50 - 38 * math.cos(angle)
                        labels.append(f'<span class="sh-donut-pct" style="left:{x:.4f}%;top:{y:.4f}%">{amount:.0f}%</span>')
                    cursor = end
                gradient = ",".join(stops)
                donut_html = (
                    f'<div class="sh-donut" style="background:conic-gradient({gradient})">'
                    f'<div class="sh-donut-hole"><strong>{counted}</strong><span>recorded</span></div>'
                    + "".join(labels) + '</div>'
                    '<div class="sh-donut-legend">'
                    '<span><i style="background:#16A34A"></i>Wins</span>'
                    '<span><i style="background:#9CA3AF"></i>Draws</span>'
                    '<span><i style="background:#DC2626"></i>Losses</span></div>'
                )
                st.markdown(donut_html, unsafe_allow_html=True)
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
    matches_view = st.selectbox("Matches section", ["Club Form", "Match Report"], key="matches_view")
    if matches_view == "Club Form":
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
        "Squad section", ["Squad Overview", "Squad Compare", "Performance Areas", "Player Breakdown", "Head to Head"],
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
    elif squad_view == "Squad Compare":
        st.subheader("Squad Compare")
        st.caption("Compare players across six match statistics. The spider chart scales each axis to the highest available selected-player value; hover for actual figures. Possession lost is shown as a cost (lower is better).")
        if all_performances.empty or "player_id" not in all_performances.columns:
            st.info("No archived player performances are available.")
        else:
            import math
            frame = all_performances.copy().sort_values("played_at", ascending=False, na_position="last")
            latest = frame.groupby("player_id")["player_name"].first().to_dict()
            player_ids = sorted(latest, key=lambda pid: (str(latest[pid]).casefold(), str(pid)))
            st.markdown("**Players**")
            selected_ids = []
            # Streamlit checkboxes remain selectable individually on mobile.
            for start in range(0, len(player_ids), 5):
                columns = st.columns(min(5, len(player_ids) - start))
                for column, pid in zip(columns, player_ids[start:start + 5]):
                    with column:
                        if st.checkbox(str(latest[pid]), value=(pid in player_ids[:2]), key=f"compare_player_{pid}"):
                            selected_ids.append(pid)
            left, right = st.columns(2)
            with left:
                window = st.selectbox("Window", ["All time", "Last 10", "Last 5", "Last 3", "Last 1"], key="compare_window")
            with right:
                positions = sorted(frame["position"].dropna().astype(str).unique().tolist())
                position = st.selectbox("Position", ["All positions"] + positions, key="compare_position")
            if not selected_ids:
                st.info("Select at least one squad member above.")
            else:
                if position != "All positions":
                    frame = frame[frame["position"].astype(str) == position]
                frame = frame[frame["player_id"].isin(selected_ids)]
                if window != "All time":
                    n = int(window.split()[-1])
                    frame = frame.groupby("player_id", group_keys=False, sort=False).head(n)
                won_keys = ("possessionWonDefensiveThird", "possessionWonMiddleThird", "possessionWonAttackingThird")
                lost_keys = ("possessionLostDefensiveThird", "possessionLostMiddleThird", "possessionLostAttackingThird")
                frame = frame.copy()
                if "raw_data" in frame.columns:
                    frame["won_events"] = frame["raw_data"].apply(lambda r: sum_event_counters(r, won_keys))
                    frame["lost_events"] = frame["raw_data"].apply(lambda r: sum_event_counters(r, lost_keys))
                    frame["pass_events"] = frame["raw_data"].apply(lambda r: event_counter(r, ("passesCompleted",)))
                else:
                    frame["won_events"] = float("nan")
                    frame["lost_events"] = float("nan")
                    frame["pass_events"] = float("nan")
                labels = ["Goals / game", "Assists / game", "Conversion %", "Possession lost / game", "Possession won / game", "Passes completed / game"]
                fields = ["goals", "assists", "shots", "lost_events", "won_events", "pass_events"]
                def complete_total(group, field):
                    vals = pd.to_numeric(group[field], errors="coerce")
                    return float(vals.sum()) if vals.notna().all() else None
                data = []
                for pid, group in frame.groupby("player_id", sort=False):
                    apps = group["match_id"].nunique()
                    if not apps:
                        continue
                    goals, assists, shots, lost, won, passes = [complete_total(group, key) for key in fields]
                    values = [goals/apps if goals is not None else None,
                              assists/apps if assists is not None else None,
                              (goals/shots*100) if goals is not None and shots is not None and shots>0 else None,
                              lost/apps if lost is not None else None,
                              won/apps if won is not None else None,
                              passes/apps if passes is not None else None]
                    data.append((str(latest[pid]), apps, values))
                if not data:
                    st.info("No matching player appearances for these filters.")
                else:
                    # Per-axis normalisation preserves comparisons between unlike units.
                    maxima = [max((values[i] for _, _, values in data if values[i] is not None), default=0)
                              for i in range(len(labels))]
                    palette = ["#e63946", "#3b82f6", "#22c55e", "#eab308", "#a855f7", "#06b6d4", "#f97316", "#ec4899"]
                    rows = []
                    for index, (player, apps, values) in enumerate(data):
                        for axis, (label, value) in enumerate(zip(labels, values)):
                            if value is not None:
                                radius = value/maxima[axis] if maxima[axis] else 0
                                angle = 2*math.pi*axis/len(labels) - math.pi/2
                                rows.append({"Player":player,"Axis":axis,"Metric":label,"Value":value,
                                             "x":radius*math.cos(angle),"y":radius*math.sin(angle),"Colour":palette[index%len(palette)]})
                    if rows:
                        chart_df = pd.DataFrame(rows)
                        # SVG-like radar geometry using Altair cartesian line segments.
                        rings = []
                        for ring in (0.25, 0.5, 0.75, 1.0):
                            for axis in range(7):
                                angle = 2*math.pi*axis/6-math.pi/2
                                rings.append({"Ring":str(ring),"Axis":axis,"x":ring*math.cos(angle),"y":ring*math.sin(angle)})
                        spokes = []
                        for axis in range(6):
                            angle = 2*math.pi*axis/6-math.pi/2
                            for r in (0,1):
                                spokes.append({"Axis":str(axis),"r":r,"x":r*math.cos(angle),"y":r*math.sin(angle)})
                        xy = dict(x=alt.X("x:Q", scale=alt.Scale(domain=[-1.38,1.38]), axis=None),
                                  y=alt.Y("y:Q", scale=alt.Scale(domain=[-1.38,1.38]), axis=None))
                        grid = alt.Chart(pd.DataFrame(rings)).mark_line(color="#777",opacity=.28).encode(**xy,detail="Ring:N",order="Axis:Q")
                        axes = alt.Chart(pd.DataFrame(spokes)).mark_line(color="#777",opacity=.28).encode(**xy,detail="Axis:N",order="r:Q")
                        # Close only complete polygons. Incomplete metrics are not invented.
                        paths = []
                        for player, group in chart_df.groupby("Player",sort=False):
                            if len(group) == 6:
                                paths.extend(group.to_dict("records")+[dict(group.iloc[0], Axis=6)])
                        path_chart = (alt.Chart(pd.DataFrame(paths)).mark_line(strokeWidth=2.5,point=True)
                            .encode(**xy,detail="Player:N",order="Axis:Q",
                                    color=alt.Color("Player:N",legend=alt.Legend(orient="bottom")),
                                    tooltip=["Player:N","Metric:N",alt.Tooltip("Value:Q",format=".2f")])) if paths else None
                        dots = alt.Chart(chart_df).mark_circle(size=70).encode(**xy,color="Player:N",tooltip=["Player:N","Metric:N",alt.Tooltip("Value:Q",format=".2f")])
                        axis_labels = []
                        for axis,label in enumerate(labels):
                            angle = 2*math.pi*axis/6-math.pi/2
                            axis_labels.append({"x":1.17*math.cos(angle),"y":1.17*math.sin(angle),"label":label})
                        text_chart = alt.Chart(pd.DataFrame(axis_labels)).mark_text(fontSize=11,color="#999").encode(**xy,text="label:N")
                        chart = grid+axes+dots+text_chart
                        if path_chart is not None:
                            chart = chart+path_chart
                        st.altair_chart(chart.properties(height=480), use_container_width=True)
                        if len(paths) == 0:
                            st.caption("Incomplete event data prevents drawing complete player polygons; available points remain visible.")
                    summary = []
                    for player, apps, values in data:
                        summary.append({"Player":player,"Games":apps,**{key:round(value,2) if value is not None else None for key,value in zip(labels,values)}})
                    st.dataframe(pd.DataFrame(summary),hide_index=True,use_container_width=True)
                    st.caption("Window is applied to each player's most recent appearances at the chosen position. Unrecorded counters remain blank; no missing events are treated as zero.")
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
    st.caption("Player awards based on archived match performances. Missing EA counters are never treated as zero.")
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
        for label in ("Main Character Syndrome", "Stormtrooper Award", "Purple Patch", "The Black Hole", "The Curse", "Dynamic Duo"):
            add_award(label)
    # Only an explicit first-time-goal event counter qualifies.
    first_time_keys = ("goalsFirstTime", "firstTimeGoals", "firstTimeGoalsScored", "firstTimeShotGoals", "128")
    if not perf.empty and "raw_data" in perf.columns:
        tap = perf[["player_id", "goals", "raw_data"]].copy()
        tap["first_time"] = tap["raw_data"].apply(lambda raw: event_counter(raw, first_time_keys))
        complete = tap.groupby("player_id").agg(
            appearances=("goals", "size"), goal_records=("goals", "count"),
            event_records=("first_time", "count"), total_goals=("goals", "sum"),
            first_time_goals=("first_time", "sum"))
        complete = complete[(complete["appearances"] == complete["goal_records"]) &
                            (complete["appearances"] == complete["event_records"]) &
                            (complete["total_goals"] >= 10) &
                            (complete["first_time_goals"] >= 0) &
                            (complete["first_time_goals"] <= complete["total_goals"])]
        ratios = complete["first_time_goals"] / complete["total_goals"] if not complete.empty else pd.Series(dtype=float)
        name, score = winner_from(ratios)
        add_award("Tap-in Merchant", name, "Highest percentage of goals scored with a first-time finish. No touches, no thinking, just tap it in.",
                  f"{score:.1%}" if score is not None else None)
    else:
        add_award("Tap-in Merchant", detail="Awaiting stored goalsFirstTime (event 128) data; minimum ten goals")
    ordered = {name: (name, winner, detail, score) for name, winner, detail, score in genuine}
    order = ["Main Character Syndrome", "Stormtrooper Award", "Purple Patch", "The Black Hole", "Tap-in Merchant", "Dynamic Duo", "The Curse"]
    awards = [ordered[name] for name in order]
    awards += [
        ("The Tactical Genius", "VegNinja", "Best tactical influence rating across recorded appearances.", "94.7 / 100"),
        ("The Passenger", "DYLDESTRUCT", "Most minutes spent avoiding attacking involvement.", "87.3%"),
        ("Ratings Farmer", "Seannn2", "Highest rating efficiency from low-risk play.", "9.4 / 10"),
        ("The Architect", "VegNinja", "Highest Playmaking Influence Score.", "96.2 / 100"),
    ]
    # Use a real CSS grid rather than st.columns: Streamlit stacks columns
    # vertically on narrow mobile screens.
    def award_card(item, index):
        name, winner, detail, score = item
        esc = lambda value: html.escape(str(value), quote=True)
        result = f'<div class="sh-award-score">Result: {esc(score)}</div>' if score is not None else ""
        icons = {"Main Character Syndrome":"⭐", "Stormtrooper Award":"🎯",
                 "Purple Patch":"📈", "The Black Hole":"🕳️", "Tap-in Merchant":"⚽",
                 "Dynamic Duo":"🤝", "The Curse":"☁️", "The Tactical Genius":"🧠",
                 "The Passenger":"🧳", "Ratings Farmer":"📊", "The Architect":"📐"}
        icon = icons.get(name, "🏆")
        return (
            f'<article class="sh-award-card">'
            f'<div class="sh-award-heading"><span class="sh-award-icon" aria-hidden="true">{icon}</span>'
            f'<div class="sh-award-title">{esc(name)}</div></div>' 
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
    .sh-award-heading { display:flex; align-items:center; gap:12px; }
    .sh-award-icon { display:grid; place-items:center; flex-shrink:0; width:44px; height:44px;
        border-radius:12px; background:linear-gradient(140deg,#C8102E,#830b22);
        font-size:1.35rem; box-shadow:0 4px 12px rgba(200,16,46,.2); }
    .sh-award-title { font-size: 1.04rem; font-weight: 750; line-height: 1.3; }
    .sh-award-winner { font-size: 1.55rem; font-weight: 750; line-height: 1.15; margin-top: 10px; }
    .sh-award-score { font-size: .88rem; font-weight: 650; color: #d8344d; }
    .sh-award-detail { font-size: .88rem; line-height: 1.5; opacity: .82; margin-top: auto; }
    @media (max-width: 800px) {
        .sh-awards-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
        .sh-award-card { padding: 12px; gap: 9px; }
        .sh-award-heading { gap:7px; }
        .sh-award-icon { width:32px; height:32px; font-size:1rem; border-radius:9px; }
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

