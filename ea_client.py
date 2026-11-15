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
    details = api.get_club_details(club_id)
    if isinstance(details, list):
        details = details[0] if details else {}
    return {"club_id": int(club_id), "details": details or {}}

def fetch_club_bundle(club_id: int) -> dict:
    """Fetch one current snapshot. EA currently caps match history at 10 per type."""
    details = api.get_club_details(club_id)
    overall = api.get_club_overall_stats(club_id)
    members = _as_list(api.get_member_stats(club_id))
    career = _as_list(api.get_member_career_stats(club_id))
    league_matches = _as_list(api.get_club_matches(club_id, match_type="leagueMatch", count=10))
    friendlies = _as_list(api.get_club_matches(club_id, match_type="friendlyMatch", count=10))
    playoff_matches = _as_list(api.get_club_matches(club_id, match_type="playoffMatch", count=10))
    match_players = _as_list(api.get_match_players(club_id, match_type="leagueMatch", count=10))
    return {
        "club_details": details if isinstance(details, dict) else (details[0] if details else {}),
        "overall_stats": overall if isinstance(overall, dict) else (overall[0] if isinstance(overall, list) and overall else {}),
        "member_stats": members,
        "career_stats": career,
        "matches": league_matches + friendlies + playoff_matches,
        "match_players": match_players,
    }
