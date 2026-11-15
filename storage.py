"""Supabase persistence. Uses one JSONB row per unique captured record."""
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

    def save_bundle(self, club_id: str, club_name: str, bundle: dict) -> int:
        saved = 0
        for record_type, value in bundle.items():
            rows = value if isinstance(value, list) else [value]
            for record in rows:
                if record is None:
                    continue
                payload = self._json_safe(record)
                # Snapshot hash avoids assumptions about undocumented EA record IDs.
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
        return saved

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
                    # De-duplicate payloads; newest copy wins.
                    if payload not in result[kind]:
                        result[kind].append(payload)
            return result
        except Exception as exc:
            raise StoreError(str(exc)) from exc
