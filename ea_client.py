"""Small adapter around the community-maintained FC 27 Pro Clubs API client."""
from fc_clubs_api import FC27API

api = FC27API(timezone="Europe/London")

def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    # DataFrame output is not enabled; handle dict responses defensively.
    if isinstance(value, dict):
        for key in ("items", "members", "matches", "data"):
            if isinstance(value.get(key), list):
                return value[key]
        return [value]
    try:
        return value.to_dict(orient="records")
    except Exception:
        return []

def find_club(name: str) -> dict:
    club_id = api.find_club_id(name)
    details = api.get_club_details(club_id, all_columns=True, output="records")
    if isinstance(details, list):
        details = details[0] if details else {}
    return {"club_id": int(club_id), "details": details or {}}

def fetch_club_bundle(club_id: int) -> dict:
    """Fetch one current snapshot. EA currently caps match history at 10 per type."""
    details = api.get_club_details(club_id, all_columns=True, output="records")
    overall = api.get_club_overall_stats(club_id, all_columns=True, output="records")
    members = _as_list(api.get_member_stats(club_id, all_columns=True, output="records"))
    career = _as_list(api.get_member_career_stats(club_id, all_columns=True, output="records"))
    # Keep the existing curated match and squad records for the current dashboard.
    # Full-column versions are separately archived below.
    full_details = details
    full_overall = overall
    full_members = members
    full_career = career
    details = api.get_club_details(club_id, output="records")
    overall = api.get_club_overall_stats(club_id, output="records")
    members = _as_list(api.get_member_stats(club_id, output="records"))
    career = _as_list(api.get_member_career_stats(club_id, output="records"))
    league_matches = _as_list(api.get_club_matches(club_id, match_type="leagueMatch", count=10))
    friendlies = _as_list(api.get_club_matches(club_id, match_type="friendlyMatch", count=10))
    playoff_matches = _as_list(api.get_club_matches(club_id, match_type="playoffMatch", count=10))
    # Collect player performances for every match category we already archive.
    # Do not swallow API errors: a failed category should fail the sync visibly.
    match_players = []
    opponent_players = []
    raw_matches = []
    full_match_players = []
    for match_type in ("leagueMatch", "friendlyMatch", "playoffMatch"):
        rows = _as_list(api.get_match_players(
            club_id, match_type=match_type, count=10, both_teams=True,
            all_columns=True, include_events=True, output="records"
        ))
        full_match_players.extend(rows)
        for row in rows:
            # Do not let opponent performances overwrite our own player's rows.
            row_club = row.get("clubId")
            if row_club is None:
                raise ValueError("EA player row lacks clubId; refusing unsafe classification")
            if str(row_club) == str(club_id):
                match_players.append(row)
            else:
                opponent_players.append(row)
        # Raw output is unprocessed EA match JSON (includes both teams and event IDs).
        raw_matches.extend(_as_list(api.get_club_matches(
            club_id, match_type=match_type, count=10, output="raw"
        )))
    # Structured player rows must retain the wrapper's curated names used by storage.py.
    # Full-column rows are still archived separately in club_records.
    match_players = []
    opponent_players = []
    for match_type in ("leagueMatch", "friendlyMatch", "playoffMatch"):
        curated = _as_list(api.get_match_players(
            club_id, match_type=match_type, count=10, both_teams=True,
            include_events=True, output="records"
        ))
        for row in curated:
            row_club = row.get("clubId")
            if row_club is None:
                raise ValueError("EA player row lacks clubId; refusing unsafe classification")
            (match_players if str(row_club) == str(club_id) else opponent_players).append(row)
    playoff_achievements = _as_list(api.get_playoff_achievements(club_id, output="records"))
    return {
        "full_club_details": full_details,
        "full_overall_stats": full_overall,
        "full_member_stats": full_members,
        "full_career_stats": full_career,
        "full_match_players": full_match_players,
        "opponent_players": opponent_players,
        "raw_matches": raw_matches,
        "playoff_achievements": playoff_achievements,
        "club_details": details if isinstance(details, dict) else (details[0] if details else {}),
        "overall_stats": overall if isinstance(overall, dict) else (overall[0] if isinstance(overall, list) and overall else {}),
        "member_stats": members,
        "career_stats": career,
        "matches": league_matches + friendlies + playoff_matches,
        "match_players": match_players,
    }
