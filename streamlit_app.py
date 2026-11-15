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
    st.subheader("StereoHearts FC — match analytics")
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
