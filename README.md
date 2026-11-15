# FC 27 Pro Clubs Dashboard (PS5)

A starter Streamlit dashboard that reads club/squad/match data through the unofficial community `fc-clubs-api` Python client and stores snapshots in Supabase.

## What is included

- Club search by name
- Club overview and current squad statistics
- Recent league, friendly and playoff match records
- Per-match player performance records for recent league matches
- Supabase JSONB archive with de-duplication by payload hash
- Streamlit website deployment configuration

## Important limitations

- This uses an unofficial, undocumented EA endpoint and a community-maintained Python wrapper. EA can change or block it.
- The wrapper documents EA's recent match history as capped at 10 matches per match type, with no paging. Sync regularly to build your own archive.
- This starter's archive saves each distinct payload once. It is a first persistence layer, not yet a complete event-sourced analytics model.
- EA data availability and field names can vary. The dashboard shows raw records so the integration can be checked against your club before adding advanced metrics.
- The current sync collects per-player match breakdowns for league matches. Friendly/playoff player-level collection can be added after validating the response and call limits.

## 1. Create the Supabase database

1. Create a project at https://supabase.com/.
2. Open **SQL Editor**.
3. Paste and run the contents of `schema.sql`.
4. In **Project Settings > API**, copy the Project URL and the `service_role` key.
5. Keep the service-role key private. It must only be stored as a Streamlit secret.
6. Choose a long random admin password for the `[app] admin_password` setting in your secrets file. Only people with this password can trigger a sync; visitors can view archived statistics.

## 2. Run locally (optional)

Install Python 3.9+.

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your Supabase URL and service-role key.

Run:

```bash
streamlit run streamlit_app.py
```

## 3. Put the project on GitHub

1. Create a new GitHub repository (private is fine).
2. Upload the project files.
3. Confirm `.streamlit/secrets.toml` is NOT uploaded. `.gitignore` excludes it.

## 4. Deploy the website

1. Sign in at https://share.streamlit.io/ using GitHub.
2. Choose **Create app** and select your repository.
3. Set the main file to `streamlit_app.py`.
4. Open **Advanced settings > Secrets** and paste the contents of your local `secrets.toml` (with your real credentials).
5. Deploy. Streamlit gives you a shareable `*.streamlit.app` URL.

## 5. First sync

1. Open your deployed site.
2. Enter the exact club name in the sidebar.
3. Click **Find club** and check that the selected club is correct.
4. Click **Sync latest EA data**.
5. Check Overview, Squad, Matches and Raw data.

## Next development milestones

1. Validate the returned fields using your actual club.
2. Add a scheduled collector (GitHub Actions or a small always-on worker) so the archive updates even when nobody opens the dashboard.
3. Add match-level IDs and normalized match/player tables for reliable historical analytics.
4. Add player profiles, position filters, form charts, player combinations and season comparisons.
5. Add optional access control if the dashboard should be private to club members.

## Security

Never commit Supabase service-role keys, passwords or tokens to GitHub. Streamlit Community Cloud supports secrets in app settings. The starter currently uses the service-role key only in server-side Python. The dashboard is designed as a public, read-only site for visitors; syncing is protected by an admin password stored in Streamlit secrets. Anyone with the site URL can view the club's archived statistics, so do not deploy it publicly if you consider those stats private.
