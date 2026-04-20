# FOYS DWF API

Discovered by reverse engineering the NBB Digitaal Wedstrijd Formulier
web app at https://dwf.basketball.nl

Demo match: https://dwf.basketball.nl/matches/487998/progress

---

## Authentication

POST https://api.foys.io/foys/api/v1/token
Content-Type: application/x-www-form-urlencoded

grant_type=password
username=...
password=...
organisationId=...

Returns a JWT token. Use as Bearer token on all subsequent requests.
Token expires — must be refreshed periodically.

NEVER commit credentials to the repository. Store in .env file.
Add .env to .gitignore.

---

## Base URL

https://api.foys.io/competition/dmf-api/v1

---

## Endpoints

### All matches for account
GET /matches

Returns an array of all matches assigned to the authenticated DWF
account — completed, live, and upcoming. The Pi uses this to find
the currently live match without needing a hardcoded matchId.

  live = next(m for m in matches if m["status"] == "InProgress")

Match status values:
  "Planned"    — not yet started
  "InProgress" — live (assumed, not yet confirmed in demo)
  "Final"      — completed

Key fields per match object:
  id                        — matchId for subsequent calls
  status
  homeTeamId / awayTeamId
  homeTeamName / awayTeamName
  homeTeamOrganisationUrl / awayTeamOrganisationUrl  (team logo)
  homeScore / awayScore     — pre-calculated running totals
  period                    — current period (null when not started)
  matchDisciplinaryStatus   — null or reason object if match stopped
  homeTeamMatchPlayers / awayTeamMatchPlayers
    teamNumber              — jersey number
    isCaptain
    isSubstitute / isSubstitutePlayed
    matchRole.type          — "Player" or "Coach"
    totalPoints             — running scorer total
    presentStatus           — "Present" | "NotChecked"

### Goals (polled every 3 seconds during live match)
GET /matches/{matchId}/goals

Returns all scoring events. Score must be calculated client-side
by summing points per team — this endpoint is polled live, not
the match object.

Key fields:
  teamId
  points   — 0, 1, 2, or 3
  penalty  — true = free throw, false = field goal
  periodId

Scoring reference:
  points=2, penalty=false  →  2-point field goal
  points=3, penalty=false  →  3-point field goal
  points=1, penalty=true   →  free throw made
  points=0, penalty=true   →  free throw missed (no score change)

Score calculation:
  home_score = sum(g["points"] for g in goals if g["teamId"] == home_id)
  away_score = sum(g["points"] for g in goals if g["teamId"] == away_id)

### Offenses (polled every 3 seconds during live match)
GET /matches/{matchId}/offenses

Returns all fouls. Used to calculate team fouls per period for
bonus situation detection.

Key fields:
  matchPlayer.teamId
  matchPlayer.matchRole.type  — "Player" or "Coach"
  offenseType.code
  offenseType.group
  periodId

Offense type reference:
  code  group  name                            counts as team foul
  P0    P      Diskwalificerende persoonlijke  yes
  P1    P      Persoonlijke fout 1             yes
  P2    P      Persoonlijke fout 2             yes
  P3    P      Persoonlijke fout 3             yes
  T     TF     Technische fout speler          yes
  TC    TF     Technische fout coach           NO
  TB    TF     Technische fout bank            NO
  U     SF     Onsportief gedrag               yes
  D     SF     Diskwalificatie                 yes
  F     SF     Vechten                         yes

Team foul count — only fouls where matchRole.type == "Player" count.
Coach (TC) and bench (TB) technicals are excluded.

  team_fouls = [
      f for f in offenses
      if f["matchPlayer"]["teamId"] == team_id
      and f["periodId"] == current_period
      and f["matchPlayer"]["matchRole"]["type"] == "Player"
  ]
  bonus = len(team_fouls) >= 4

### Timeouts (polled if needed)
GET /matches/{matchId}/timeouts

Key fields:
  isHomeTeam  — true or false
  periodId

---

## Pi polling architecture

On startup:
  GET /matches
    → find live match by status "InProgress"
    → extract team names, IDs, matchId

Every 3 seconds during game:
  GET /matches/{matchId}/goals     → calculate score per team
  GET /matches/{matchId}/offenses  → calculate team fouls per period

---

## Clock

The game clock is not transmitted via the FOYS API. It runs
client-side in the DWF browser app. No WebSocket connection detected.

For the overlay, clock data must come from the Anatec AK30 serial
feed (see protocol.md), or be omitted from the overlay.

---

## Security

Credentials (username, password, organisationId) must never be
committed to the repository.

Store in a .env file:
  FOYS_USERNAME=...
  FOYS_PASSWORD=...
  FOYS_ORGANISATION_ID=...

Add to .gitignore:
  .env

---

## Notes

- All API calls go to api.foys.io, not dwf.basketball.nl
- CORS restricted to dwf.basketball.nl origin
- Served via Cloudflare
- demo-mode: true header used in demo environment
- matchId visible in DWF URL: /matches/{matchId}/progress
- "InProgress" status not confirmed in demo — to verify with live match
- homeScore/awayScore in match object are pre-calculated but the
  match object is not polled live — calculate from /goals instead