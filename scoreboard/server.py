"""
server.py
=========
Flask server — serves match selection UI, overlay data endpoint,
and runs the FOYS background poller.

Usage:
    python scoreboard/server.py
"""

import threading
import time
from flask import Flask, jsonify, render_template
from foys import FoysClient
from state import match_state

app = Flask(__name__, template_folder="../templates")
client = FoysClient()


# ── Helper functions ────────────────────────────────────────────────────────

def calculate_score(goals, team_id):
    return sum(g["points"] for g in goals if g["teamId"] == team_id)


def calculate_fouls(offenses, team_id, period_id):
    return len([
        f for f in offenses
        if f["matchPlayer"]["teamId"] == team_id
        and f["periodId"] == period_id
        and f["matchPlayer"]["matchRole"]["type"] == "Player"
    ])


def current_period(goals, offenses):
    events = (goals or []) + (offenses or [])
    if not events:
        return None
    return max(events, key=lambda e: e.get("matchLogId", 0)).get("periodId")


# ── Background poller ───────────────────────────────────────────────────────

seen_offense_ids = set()


def poll():
    global seen_offense_ids
    while True:
        try:
            if match_state["selected"] and match_state["status"] != "Final":
                match_id = match_state["match_id"]
                home_id  = match_state["home_id"]
                away_id  = match_state["away_id"]

                goals    = client.get_goals(match_id)
                offenses = client.get_offenses(match_id)
                period   = current_period(goals, offenses)

                match_state["home_score"] = calculate_score(goals, home_id)
                match_state["away_score"] = calculate_score(goals, away_id)
                match_state["period"]     = period

                if period:
                    home_fouls = calculate_fouls(offenses, home_id, period)
                    away_fouls = calculate_fouls(offenses, away_id, period)
                    match_state["home_fouls"] = home_fouls
                    match_state["away_fouls"] = away_fouls
                    match_state["home_bonus"] = home_fouls >= 4
                    match_state["away_bonus"] = away_fouls >= 4

                # detect new player fouls for popup
                new_fouls = [
                    f for f in offenses
                    if f["id"] not in seen_offense_ids
                    and f["matchPlayer"]["matchRole"]["type"] == "Player"
                ]
                if new_fouls:
                    f = new_fouls[-1]
                    match_state["last_foul"] = {
                        "player": f["matchPlayer"]["person"]["fullName"],
                        "jersey": f["matchPlayer"]["teamNumber"],
                        "code":   f["offenseType"]["code"],
                        "team":   "home" if f["matchPlayer"]["teamId"] == home_id else "away",
                    }
                seen_offense_ids = {f["id"] for f in offenses}

        except Exception as e:
            print(f"Poll error: {e}")

        time.sleep(3)


# ── Flask routes ────────────────────────────────────────────────────────────

@app.route("/")
def select():
    matches = client.get_matches()
    return render_template("select.html", matches=matches)


@app.route("/select/<int:match_id>")
def select_match(match_id):
    global seen_offense_ids
    matches = client.get_matches()
    match   = next((m for m in matches if m["id"] == match_id), None)

    if not match:
        return "Match not found", 404

    seen_offense_ids = set()
    match_state.update({
        "selected":   True,
        "match_id":   match_id,
        "home_id":    match["homeTeamId"],
        "away_id":    match["awayTeamId"],
        "home_name":  match["homeTeamName"],
        "away_name":  match["awayTeamName"],
        "home_score": match["homeScore"],
        "away_score": match["awayScore"],
        "status":     match["status"],
        "last_foul":  None,
    })
    return render_template("select.html", matches=matches,
                           selected=match_id, message=f"Selected: {match['homeTeamName']} vs {match['awayTeamName']}")


@app.route("/api/state")
def api_state():
    return jsonify(match_state)


@app.route("/overlay")
def overlay():
    return render_template("overlay.html")


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Authenticating with FOYS...")
    client.authenticate()
    print("Starting background poller...")
    t = threading.Thread(target=poll, daemon=True)
    t.start()
    print("Server running at http://localhost:5000")
    app.run(host="0.0.0.0", port=5001, debug=False)