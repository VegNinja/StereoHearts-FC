"""One-time, repeatable migration of archived EA records into analytics tables.

Run via GitHub Actions with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
Does not delete or modify club_records.
"""
import os
from storage import SupabaseStore

CLUB_ID = "400349"
PAGE_SIZE = 250


def main():
    url = os.environ["SUPABASE_URL"].strip()
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip()
    store = SupabaseStore(url, key)
    offset = 0
    scanned = 0
    matches = 0
    performances = 0

    while True:
        # Oldest first: newer versions of the same match overwrite older ones.
        response = (
            store.client.table("club_records")
            .select("record_type,payload,captured_at")
            .eq("club_id", CLUB_ID)
            .in_("record_type", ["matches", "match_players"])
            .order("captured_at", desc=False)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            break

        # Process in captured order to preserve latest values when IDs recur.
        # save_analytics deduplicates within each batch using stable IDs.
        bundle = {"matches": [], "match_players": []}
        for row in rows:
            kind = row.get("record_type")
            payload = row.get("payload")
            if kind in bundle and isinstance(payload, dict):
                bundle[kind].append(payload)
        store.save_analytics(CLUB_ID, bundle)
        scanned += len(rows)
        matches += len(bundle["matches"])
        performances += len(bundle["match_players"])
        print(f"Processed {scanned} archived records...", flush=True)
        offset += len(rows)
        if len(rows) < PAGE_SIZE:
            break

    print(
        f"Backfill complete. Scanned {scanned} archive records; "
        f"processed {matches} match records and {performances} player records. "
        "These are not counts of newly inserted unique rows."
    )


if __name__ == "__main__":
    main()
