"""Supabase persistence for raw EA records and structured match analytics."""
import hashlib
import json
from datetime import datetime, timezone
from supabase import create_client


class StoreError(RuntimeError):
    pass


class SupabaseStore:
    def __init__(self, url: str, service_role_key: str):
        self.client = create_client(url, service_role_key)

    @staticmethod
    def _json_safe(value):
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))

    @staticmethod
    def _integer(value):
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _number(value):
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _boolean(value):
        if isinstance(value, bool):
            return value
        if value in (1, "1", "true", "True"):
            return True
        if value in (0, "0", "false", "False"):
            return False
        return None

    def save_bundle(self, club_id: str, club_name: str, bundle: dict) -> int:
        """Save raw data, then upsert normalized records. Returns raw records processed."""
        saved = 0
        for record_type, value in bundle.items():
            rows = value if isinstance(value, list) else [value]
            for record in rows:
                if record is None:
                    continue
                payload = self._json_safe(record)
                canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
                digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                row = {
                    "club_id": str(club_id),
                    "club_name": club_name,
                    "record_type": record_type,
                    "record_key": digest,
                    "payload": payload,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                }
                self.client.table("club_records").upsert(
                    row, on_conflict="club_id,record_type,record_key"
                ).execute()
                saved += 1

        self.save_analytics(club_id, bundle)
        self.save_opponents(club_id, bundle.get("opponent_players", []))
        return saved

    def save_analytics(self, club_id: str, bundle: dict):
        """Match IDs and (match ID, player ID) make repeated syncs idempotent."""
        cid = self._integer(club_id)
        if cid is None:
            raise StoreError("Invalid club ID")

        matches = []
        for item in bundle.get("matches", []):
            if not isinstance(item, dict):
                continue
            match_id = self._integer(item.get("matchId"))
            if match_id is None:
                continue
            matches.append({
                "club_id": cid,
                "match_id": match_id,
                "played_at": item.get("timestamp"),
                "match_type": item.get("matchType"),
                "result": item.get("result"),
                "goals": self._integer(item.get("goals")),
                "opponent_id": self._integer(item.get("opponentId")),
                "dnf": self._boolean(item.get("dnf")),
                "raw_data": self._json_safe(item),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        # Deduplicate within the current API response before upserting.
        unique_matches = {(r["club_id"], r["match_id"]): r for r in matches}
        if unique_matches:
            self.client.table("matches").upsert(
                list(unique_matches.values()), on_conflict="club_id,match_id"
            ).execute()

        performances = []
        for item in bundle.get("match_players", []):
            if not isinstance(item, dict):
                continue
            match_id = self._integer(item.get("matchId"))
            player_id = self._integer(item.get("playerId"))
            if match_id is None or player_id is None:
                continue
            performances.append({
                "club_id": cid,
                "match_id": match_id,
                "player_id": player_id,
                "player_name": item.get("name"),
                "position": item.get("position"),
                "rating": self._number(item.get("rating")),
                "goals": self._integer(item.get("goals")),
                "assists": self._integer(item.get("assists")),
                "shots": self._integer(item.get("shots")),
                "saves": self._integer(item.get("saves")),
                "red_cards": self._integer(item.get("redCards")),
                "clean_sheet": self._integer(item.get("cleanSheet")),
                "passes_made": self._integer(item.get("passesMade")),
                "pass_attempts": self._integer(item.get("passAttempts")),
                "tackles_made": self._integer(item.get("tacklesMade")),
                "tackle_attempts": self._integer(item.get("tackleAttempts")),
                "seconds_played": self._integer(item.get("secondsPlayed")),
                "man_of_the_match": self._integer(item.get("manOfTheMatch")),
                "played_at": item.get("timestamp"),
                "raw_data": self._json_safe(item),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        unique_players = {
            (r["club_id"], r["match_id"], r["player_id"]): r
            for r in performances
        }
        if unique_players:
            self.client.table("match_player_stats").upsert(
                list(unique_players.values()),
                on_conflict="club_id,match_id,player_id",
            ).execute()


    def save_opponents(self, club_id: str, records: list):
        """Separate table avoids opponent/player ID collision in club stats."""
        rows = []
        for item in records:
            if not isinstance(item, dict):
                continue
            match_id = self._integer(item.get("matchId"))
            player_id = self._integer(item.get("playerId"))
            opponent_id = self._integer(item.get("clubId"))
            if None in (match_id, player_id, opponent_id):
                raise StoreError("Opponent row missing matchId/playerId/clubId")
            if opponent_id == self._integer(club_id):
                raise StoreError("Own-club player found in opponent records")
            rows.append({
                "club_id": self._integer(club_id),
                "match_id": match_id,
                "opponent_club_id": opponent_id,
                "player_id": player_id,
                "player_name": item.get("name"),
                "position": item.get("position"),
                "raw_data": self._json_safe(item),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
        unique = {(r["club_id"], r["match_id"], r["opponent_club_id"], r["player_id"]): r for r in rows}
        if unique:
            self.client.table("opponent_player_stats").upsert(
                list(unique.values()),
                on_conflict="club_id,match_id,opponent_club_id,player_id",
            ).execute()

    def load_bundle(self, club_id: str) -> dict:
        result = {}
        try:
            response = (
                self.client.table("club_records")
                .select("record_type,payload,captured_at")
                .eq("club_id", str(club_id))
                .order("captured_at", desc=True)
                .limit(5000)
                .execute()
            )
            for row in response.data or []:
                kind = row["record_type"]
                payload = row["payload"]
                if kind in ("club_details", "overall_stats"):
                    result.setdefault(kind, payload)
                else:
                    result.setdefault(kind, [])
                    if payload not in result[kind]:
                        result[kind].append(payload)
            return result
        except Exception as exc:
            raise StoreError(str(exc)) from exc
