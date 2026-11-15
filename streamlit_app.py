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
st.caption("FC 27 Â· PlayStation 5 Â· Unofficial community API")

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

tab_overview, tab_squad, tab_matches, tab_analytics, tab_players, tab_archive = st.tabs(
    ["Overview", "Squad", "Matches", "Analytics", "Players", "Raw data"]
)

with tab_overview:
    st.subheader("Recent form")
    if not match_df.empty:
        result_col = first_existing(match_df, ["result"])
        if result_col:
            form = match_df[result_col].astype(str).str.upper().head(10).tolist()
            st.write("  Â·  ".join(form) if form else "No match results recorded.")
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


# Structured analytics are loaded independently of the raw EA snapshot archive.
with tab_analytics:
    st.subheader("StereoHearts FC â€” match analytics")
    st.caption("Figures cover only matches saved in Supabase, not necessarily the club's full FC 27 history.")

    def read_all_rows(table_name, club_id, page_size=1000):
        rows = []
        offset = 0
        while True:
            response = (
                store.client.table(table_name)
                .select("*")
                .eq("club_id", int(club_id))
                .range(offset, offset + page_size - 1)
                .execute()
            )
            batch = response.data or []
            rows.extend(batch)
            if len(batch) < page_size:
                return rows
            offset += page_size

    try:
        stored_matches = pd.DataFrame(read_all_rows("matches", CLUB_ID))
        stored_players = pd.DataFrame(read_all_rows("match_player_stats", CLUB_ID))
    except Exception as exc:
        st.error(f"Could not load structured analytics: {exc}")
        stored_matches = pd.DataFrame()
        stored_players = pd.DataFrame()

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
        a, b, c, d = st.columns(4)
        a.metric("Archived matches", total)
        b.metric("W / D / L", f"{wins} / {draws} / {losses}")
        c.metric("Win rate", f"{wins / total:.1%}" if total else "â€”")
        d.metric("Goals per match", f"{goals / total:.2f}" if total else "â€”")

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


# Player profiles use the same structured Supabase tables as the Analytics tab.
with tab_players:
    st.subheader("StereoHearts FC â€” player profiles")
    st.caption("Statistics are based on archived match performances, not necessarily full career totals.")

    if stored_players.empty or "player_id" not in stored_players.columns:
        st.info("No player performances are available yet. Run an EA sync first.")
    else:
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

        labels = {}
        for pid, group in profiles.groupby("player_id"):
            name = group["player_name"].iloc[-1]
            labels[pid] = f"{name} (ID {pid})"
        selected_id = st.selectbox(
            "Player", sorted(labels, key=lambda pid: labels[pid].casefold()),
            format_func=lambda pid: labels[pid], key="profile_player"
        )
        player_all = profiles[profiles["player_id"] == selected_id].copy()
        positions = sorted(player_all["position"].unique().tolist())
        types = sorted(player_all["match_type"].unique().tolist())
        p_col, t_col = st.columns(2)
        with p_col:
            selected_positions = st.multiselect(
                "Position", positions, default=positions, key="profile_positions",
                help="Only performances at the selected match positions are included."
            )
        with t_col:
            selected_types = st.multiselect(
                "Match type", types, default=types, key="profile_match_types"
            )
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
            return f"{100 * completed / total:.1f}%" if total > 0 else "â€”"

        if selected.empty:
            st.info("No performances match these filters. Choose at least one position and match type.")
        else:
            appearances = selected["match_id"].nunique()
            avg_rating = selected["rating"].mean()
            metrics = [
                ("Appearances", f"{appearances}"),
                ("Goals", f"{int(selected['goals'].sum())}"),
                ("Assists", f"{int(selected['assists'].sum())}"),
                ("Average rating", f"{avg_rating:.2f}" if pd.notna(avg_rating) else "â€”"),
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
                st.line_chart(rating_history.set_index("Match")["rating"], y_label="Match rating")

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
            columns = ["played_at", "match_type", "position", "rating", "goals", "assists",
                       "seconds_played", "passes_made", "pass_attempts", "tackles_made",
                       "tackle_attempts", "saves", "match_id"]
            history = selected.sort_values("played_at", ascending=False)[columns].copy()
            history["seconds_played"] = (history["seconds_played"] / 60).round(1)
            history.columns = ["Date", "Match type", "Position", "Rating", "Goals", "Assists",
                               "Minutes", "Passes", "Pass attempts", "Tackles", "Tackle attempts", "Saves", "Match ID"]
            st.dataframe(history, use_container_width=True, hide_index=True)
