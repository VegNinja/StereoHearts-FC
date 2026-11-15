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
            return f"{100 * completed / total:.1f}%" if total > 0 else "—"

        if selected.empty:
            st.info("No performances match these filters. Choose at least one position and match type.")
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
