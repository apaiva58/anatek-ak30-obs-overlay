# FOYS DWF API

Discovered by reverse engineering the NBB Digitaal Wedstrijd Formulier
web app at https://dwf.basketball.nl

Demo match: https://dwf.basketball.nl/matches/487998/progress

---

## Authentication

```
POST https://api.foys.io/foys/api/v1/token
Content-Type: application/x-www-form-urlencoded

grant_type=password
username=...
password=...
organisationId=...
```

Returns a JWT token. Use as Bearer header on all subsequent requests.
Token expires and must be refreshed periodically. On 401 response,
re-authenticate and retry.

JWT is stateless — multiple simultaneous clients using the same
credentials are supported. The DWF tablet operator is unaffected
by additional read-only clients.

API requires authentication. Public access not available.
401 returned without a valid Bearer token (confirmed April 2026).

NEVER commit credentials to the repository. Store in a .env file.

---

## Base URL

```
https://api.foys.io/competition/dmf-api/v1
```

All endpoints below are relative to this base URL.

---

## Endpoints

### All matches for account

```
GET /matches
```

Returns an array of all matches assigned to the authenticated DWF
account — completed, live and upcoming.

Match status values:

  Planned      not yet started
  InProgress   live (not confirmed in demo environment)
  Final        completed

Key fields per match object:

  id                              matchId for subsequent calls
  status
  homeTeamId / awayTeamId
  homeTeamName / awayTeamName
  homeTeamOrganisationName        club name
  homeTeamOrganisationUrl         club logo URL
  homeScore / awayScore           pre-calculated running totals
  period                          current period ID (null when not started)
  matchDisciplinaryStatus         null or reason if match stopped
  homeTeamMatchPlayers / awayTeamMatchPlayers
    teamNumber                    jersey number
    isCaptain
    isSubstitute / isSubstitutePlayed
    matchRole.type                Player or Coach
    totalPoints                   running scorer total
    presentStatus                 Present or NotChecked

Note: homeScore and awayScore in the match object are pre-calculated
but the match object is not polled live by the DWF app. During live
play, score must be calculated from the /goals endpoint.

---

### Goals

```
GET /matches/{matchId}/goals
```

Returns an array of all scoring events for the match.

Key fields:

  teamId          which team scored
  points          0, 1, 2 or 3
  penalty         true = free throw, false = field goal
  periodId        period in which the score occurred
  matchPlayerId   player who scored
  matchLogId      chronological sequence number

Scoring reference:

  points=2, penalty=false   2-point field goal
  points=3, penalty=false   3-point field goal
  points=1, penalty=true    free throw made
  points=0, penalty=true    free throw missed (no score change)

Score calculation:

  home_score = sum(g["points"] for g in goals if g["teamId"] == home_id)
  away_score = sum(g["points"] for g in goals if g["teamId"] == away_id)

---

### Offenses

```
GET /matches/{matchId}/offenses
```

Returns a paginated object:

  {"totalCount": N, "items": [...]}

Extract the items array. Returns all fouls registered in the match.

Key fields:

  matchPlayer.teamId
  matchPlayer.matchRole.type    Player or Coach
  offenseType.code
  offenseType.group
  periodId
  matchPlayerId
  matchLogId

Offense type reference:

  code  group  name                              counts as team foul
  P0    P      Diskwalificerende persoonlijke    yes
  P1    P      Persoonlijke fout 1               yes
  P2    P      Persoonlijke fout 2               yes
  P3    P      Persoonlijke fout 3               yes
  T     TF     Technische fout speler            yes
  TC    TF     Technische fout coach             NO
  TB    TF     Technische fout bank              NO
  U     SF     Onsportief gedrag                 yes
  D     SF     Diskwalificatie                   yes
  F     SF     Vechten                           yes

Team foul count — only fouls where matchRole.type == "Player" count.
Coach (TC) and bench (TB) technicals are excluded.

  team_fouls = [
      f for f in offenses
      if f["matchPlayer"]["teamId"] == team_id
      and f["periodId"] == current_period
      and f["matchPlayer"]["matchRole"]["type"] == "Player"
  ]
  bonus = len(team_fouls) >= 4

---

### Timeouts

```
GET /matches/{matchId}/timeouts
```

Returns a paginated object:

  {"totalCount": N, "items": [...]}

Extract the items array. Returns all timeouts taken in the match.

Key fields:

  isHomeTeam    true or false
  periodId

Note: the API records that a timeout occurred but does not indicate
whether the timeout is currently active. Duration tracking must be
handled client-side.

---

### Logs

```
GET /matches/{matchId}/logs
```

Returns a chronological event log. Each entry has a sparse structure
where most fields are null — only fields relevant to the event type
are populated.

Useful fields:

  details         human-readable description (e.g. "Gewisseld naar 2e kwart")
  periodPosition  new period ID on period change events
  matchLogId      chronological sequence number

Note: the DWF browser app polls this endpoint only occasionally,
not continuously. Not suitable for high-frequency polling.

---

## Period IDs

FOYS uses numeric period IDs consistent across all matches:

  14   1e kwart
  15   2e kwart
  16   3e kwart
  17   4e kwart
  18   1e verlenging
  19   2e verlenging
  20   3e verlenging
  21   4e verlenging
  22   5e verlenging

Team fouls reset between quarters (resetTeamOffenses: true).
Overtime periods do not reset team fouls (resetTeamOffenses: false).

---

## Clock

The game clock is not transmitted via the FOYS API. It runs
client-side in the DWF browser app from a start timestamp.
No WebSocket connection detected.

For live clock data an alternative source is required, such as
the Anatec AK30 serial feed (see docs/protocol.md).

---

## Security

Credentials must never be committed to the repository.

Store in a .env file:

  FOYS_USERNAME=...
  FOYS_PASSWORD=...
  FOYS_ORGANISATION_ID=...

Add .env to .gitignore.

---

## Technical notes

- All API calls go to api.foys.io, not dwf.basketball.nl
- CORS restricted to dwf.basketball.nl origin
- Served via Cloudflare
- Use demo-mode: true header in the demo environment only
- matchId is visible in the DWF URL: /matches/{matchId}/progress
- InProgress status not confirmed in demo — verify with a live match
- Consider contacting FOYS/NBB for a dedicated read-only API token
  for club streaming and broadcast integrations
