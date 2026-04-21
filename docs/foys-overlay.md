# FOYS DWF API — Overlay Integration

This document describes how the FOYS DWF API is used in the
Almere Pioneers scoreboard overlay stack.

---

## Architecture

```
DWF tablet (scorer's table)
        down - operator input
api.foys.io (NBB server)
        down - REST API polled every 3 seconds
scoreboard/server.py (Flask)
        down - /api/state + /api/players
overlay.html (OBS Browser Source)
```

---

## Authentication

The server authenticates once at startup using OAuth2 password grant.
Credentials are stored in `.env` (never committed to git).

```
POST https://api.foys.io/foys/api/v1/token
grant_type=password
username=...
password=...
organisationId=...
```

Returns a JWT token used as Bearer header on all subsequent calls.
Token is automatically refreshed on 401 response.

See: scoreboard/foys.py - FoysClient.authenticate()

---

## Match Selection

On startup the server fetches all matches for the account:

```
GET /competition/dmf-api/v1/matches
```

Returns an array of matches - past, live and upcoming.
The volunteer selects the correct match via the web UI at /.

Key fields used:
- id                          matchId for subsequent calls
- status                      Planned, InProgress, Final
- homeTeamName / awayTeamName
- homeTeamOrganisationName / awayTeamOrganisationName
- homeTeamId / awayTeamId
- homeScore / awayScore

See: scoreboard/server.py - select_match()

---

## Live Polling (every 3 seconds)

Three endpoints are polled continuously during the game.

### Goals

```
GET /competition/dmf-api/v1/matches/{matchId}/goals
```

Returns array of all scoring events. Score is calculated client-side:

```python
home_score = sum(g["points"] for g in goals if g["teamId"] == home_id)
```

Fields used:
- teamId          which team scored
- points          0, 1, 2 or 3
- penalty         true = free throw
- periodId        which quarter
- matchPlayerId   for player stats

### Offenses

```
GET /competition/dmf-api/v1/matches/{matchId}/offenses
```

Returns {"totalCount": N, "items": [...]} - extract items array.

Used for team foul count per period and player foul count.
Only fouls where matchPlayer.matchRole.type == "Player" count
towards team fouls. Coach and bench technicals (TC, TB) excluded.

Fields used:
- matchPlayer.teamId
- matchPlayer.matchRole.type    Player or Coach
- offenseType.code              P1, P2, P3, T, TC, TB, U, D, F
- periodId
- matchPlayerId                 for player stats

Offense codes reference: see docs/foys-api.md

### Timeouts

```
GET /competition/dmf-api/v1/matches/{matchId}/timeouts
```

Returns {"totalCount": N, "items": [...]} - extract items array.

Fields used:
- isHomeTeam    true or false
- periodId

---

## Status Check (every 9 seconds)

```
GET /competition/dmf-api/v1/matches
```

Full match list re-fetched to detect status change to Final.
Also updates current period from match object if available.

---

## Player Stats Endpoint

```
GET /api/players  (served by Flask, not FOYS)
```

Combines:
- Roster from last /matches call (name, jersey, captain)
- Live stats calculated from goals and offenses:
  - points    sum of goal points per player
  - threes    count of 3-point goals per player
  - fouls     count of player offenses

---

## Period Mapping

FOYS uses numeric period IDs:

  periodId 14   1e kwart
  periodId 15   2e kwart
  periodId 16   3e kwart
  periodId 17   4e kwart
  periodId 18+  Overtime

---

## Overlay Behaviour

overlay.html polls /api/state every 3 seconds.

During game (status != Final):
- Shows bottom scorebar with score, period, clock, fouls
- Flashing timeout popup for 60 seconds on new timeout
- Foul popup for 4 seconds on new player foul
- Bonus indicator in red when team fouls >= 4 in current period

On Final (status == Final):
- Scorebar fades out
- Final stats table fades in automatically
- Shows player points, 3-pointers, fouls sorted by points

---

## Clock

The FOYS API does not transmit the game clock. No WebSocket
connection detected in the DWF browser app. The clock runs
client-side in JavaScript from a start timestamp.

The overlay reads anatec_clock from /api/state which comes
from the Anatec AK30 serial feed when connected.
When Anatec is not connected, clock shows a dash.

---

## Known Limitations

- Period update delayed until first goal or foul in new period
- Scores above 99 not tested
- demo-mode header must be removed for production use
- API requires authentication - returns 401 without token
- FOYS server load on Saturday mornings may cause polling delays

---

## Files

  scoreboard/foys.py       FOYS API client - auth and fetch
  scoreboard/server.py     Flask server - poll loop and routes
  scoreboard/state.py      Shared in-memory match state
  templates/overlay.html   Combined live and final overlay
  templates/select.html    Match selection UI
  .env                     Credentials (not in git)

---

## References

- FOYS DWF demo: https://dwf.basketball.nl/matches/487998/progress
- Raw API documentation: docs/foys-api.md
- NBB Basketball Nederland: https://www.basketball.nl
