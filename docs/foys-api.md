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

## Data Priority — Combined Anatec + FOYS Input

When both Anatec serial and FOYS API are active, each data source
has a defined priority for each field.

### Anatec is leading

  Score        Anatec updates instantly when the operator presses
               the button. FOYS score has human latency (DWF operator
               must enter the goal). For a live stream the displayed
               score must match the physical scoreboard in real time.

  Clock        Only available from Anatec. FOYS does not transmit
               the game clock.

  Period       Physical scoreboard is authoritative.

  Timeouts     Physical scoreboard is authoritative.

### FOYS is leading

  Fouls        FOYS captures individual player fouls with names,
               jersey numbers and foul codes. Richer than Anatec
               team foul count.

  Club logos   Available from FOYS match object only.

  Match info   Date, location, court - from FOYS match object.

  Player stats Calculated from FOYS goals and offenses during the
               game. Running in the background, displayed at Final.

### FOYS score role

  The FOYS score is the official NBB record - entered by the
  certified DWF operator. It is used for player stats calculation
  and shown in the final stats table. It is not used for the live
  score display when Anatec is connected.

### Fallback

  When Anatec is not connected, the overlay falls back to FOYS
  score for the live display. This covers FOYS-only deployments.

  In overlay.html:

    const homeScore = s.anatec_connected
        ? s.anatec_home_score
        : s.home_score;

---

## Authentication

The server authenticates once at startup using OAuth2 password grant.
Credentials are stored in .env (never committed to git).

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
- homeTeamOrganisationUrl / awayTeamOrganisationUrl
- homeTeamId / awayTeamId
- homeScore / awayScore
- date / startTime / accommodationName / fieldName

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

Player stats run in the background during the game and are
displayed automatically when status becomes Final.

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
- Score from Anatec when connected, FOYS as fallback
- Clock from Anatec serial feed
- Period from FOYS (updated on first event per quarter)
- Team fouls from FOYS per period
- Club logos from FOYS
- Flashing timeout popup for 60 seconds on new timeout
- Foul popup for 4 seconds on new player foul
- Bonus indicator in red when team fouls >= 4 in current period

On Final (status == Final):
- Scorebar fades out
- Final stats table fades in automatically
- Shows FOYS official score
- Player points, 3-pointers, fouls sorted by points

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
- Scores above 99 not tested (Anatec protocol open question)
- FOYS score latency expected - Anatec score used for live display
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

- FOYS developer portal: https://developers.foys.tech
- FOYS DWF demo: https://dwf.basketball.nl/matches/487998/progress
- Raw API documentation: docs/foys-api.md
- NBB Basketball Nederland: https://www.basketball.nl