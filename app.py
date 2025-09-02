import os
from flask import Flask, render_template, request, redirect, url_for
import psycopg2
from dotenv import load_dotenv
import requests

load_dotenv()
app = Flask(__name__)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Players
players = ["Biniam A", "Biniam G", "Biniam E", "Abel", "Siem", "Kubrom"]

# Gameweeks
gameweeks = list(range(1, 39))

# API Key
API_KEY = os.getenv("FOOTBALL_API_KEY")
HEADERS = {"X-Auth-Token": API_KEY}

# ----------------------------
# Utility functions
# ----------------------------
def fetch_fixtures(gameweek):
    url = f"https://api.football-data.org/v4/competitions/PL/matches?season=2025&matchday={gameweek}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return []
    data = r.json()
    matches = []
    for m in data["matches"]:
        matches.append({
            "id": m["id"],
            "home": m["homeTeam"]["name"],
            "away": m["awayTeam"]["name"]
        })
    return matches

def fetch_results(gameweek):
    url = f"https://api.football-data.org/v4/competitions/PL/matches?season=2025&matchday={gameweek}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return {}
    data = r.json()
    results = {}
    for m in data["matches"]:
        if m["score"]["winner"] == "HOME_TEAM":
            winner = m["homeTeam"]["name"]
        elif m["score"]["winner"] == "AWAY_TEAM":
            winner = m["awayTeam"]["name"]
        else:
            winner = "Tie"
        results[str(m["id"])] = winner
    return results

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def index():
    return render_template("index.html", players=players, gameweeks=gameweeks)

@app.route("/gameweek", methods=["POST"])
def gameweek():
    player_id = request.form["player_id"]
    gameweek = int(request.form["gameweek"])
    matches = fetch_fixtures(gameweek)
    return render_template("gameweek.html", player_id=player_id, gameweek=gameweek, matches=matches)

@app.route("/submit_prediction", methods=["POST"])
def submit_prediction():
    player_id = request.form["player_id"]
    gameweek = int(request.form["gameweek"])
    predictions = {}
    for key, val in request.form.items():
        if key.startswith("match_"):
            predictions[key.replace("match_", "")] = val

    # Insert/update predictions in DB
    for match_id, pred in predictions.items():
        cur.execute("""
            INSERT INTO predictions (player_id, gameweek, match_id, prediction)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (player_id, gameweek, match_id) DO UPDATE
            SET prediction = EXCLUDED.prediction
        """, (player_id, gameweek, match_id, pred))
    conn.commit()

    # Redirect to confirmation page
    return redirect(url_for("confirmation", player_id=player_id, gameweek=gameweek))

@app.route("/confirmation/<player_id>/<int:gameweek>")
def confirmation(player_id, gameweek):
    return render_template("confirmation.html", player_id=player_id, gameweek=gameweek)

@app.route("/results/<int:gameweek>")
def results(gameweek):
    results_dict = fetch_results(gameweek)

    # Fetch predictions from DB
    cur.execute("SELECT player_id, match_id, prediction FROM predictions WHERE gameweek=%s", (gameweek,))
    rows = cur.fetchall()
    gameweek_points = {p:0 for p in players}
    for row in rows:
        player, match_id, pred = row
        correct = 1 if results_dict.get(str(match_id)) == pred else 0
        gameweek_points[player] += correct

    # Accumulated points
    cur.execute("SELECT player_id, SUM(points) FROM points GROUP BY player_id")
    accumulated_points = dict(cur.fetchall())

    return render_template("results.html", gameweek=gameweek, gameweek_points=gameweek_points, accumulated_points=accumulated_points)

if __name__ == "__main__":
    app.run(debug=True)
