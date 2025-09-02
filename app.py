import os
import requests
import psycopg2
from flask import Flask, render_template, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
PLAYERS = ["Biniam A","Biniam G","Biniam E","Abel","Siem","Kubrom"]

HEADERS = {"X-Auth-Token": FOOTBALL_API_KEY}

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# Initialize database table
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            player_id TEXT,
            match_id TEXT,
            gameweek INTEGER,
            prediction TEXT,
            UNIQUE(player_id, match_id)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# Fetch fixtures for a gameweek
def fetch_fixtures(gameweek):
    url = f"https://api.football-data.org/v4/competitions/PL/matches?season=2025&matchday={gameweek}"
    r = requests.get(url, headers=HEADERS)
    data = r.json()
    matches = []
    for m in data.get("matches", []):
        matches.append({
            "id": m["id"],
            "home": m["homeTeam"]["name"],
            "away": m["awayTeam"]["name"]
        })
    return matches

# Fetch results for a gameweek
def fetch_results(gameweek):
    url = f"https://api.football-data.org/v4/competitions/PL/matches?season=2025&matchday={gameweek}"
    r = requests.get(url, headers=HEADERS)
    data = r.json()
    results = {}
    for m in data.get("matches", []):
        if m["status"] == "FINISHED":
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            home_score = m["score"]["fullTime"]["home"]
            away_score = m["score"]["fullTime"]["away"]
            if home_score > away_score:
                results[str(m["id"])] = home
            elif away_score > home_score:
                results[str(m["id"])] = away
            else:
                results[str(m["id"])] = "Tie"
    return results

@app.route("/")
def index():
    return render_template("index.html", players=PLAYERS, gameweeks=range(1,39))

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
    conn = get_db_connection()
    cur = conn.cursor()
    for key, value in request.form.items():
        if key.startswith("match_"):
            match_id = key.split("_")[1]
            cur.execute("""
                INSERT INTO predictions (player_id, match_id, gameweek, prediction)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (player_id, match_id) DO UPDATE SET prediction=EXCLUDED.prediction
            """, (player_id, match_id, gameweek, value))
    conn.commit()
    cur.close()
    conn.close()
    return render_template("confirmation.html", gameweek=gameweek)

@app.route("/results/<int:gameweek>")
def results(gameweek):
    conn = get_db_connection()
    cur = conn.cursor()

    # Collect results for all gameweeks up to selected one
    results_dict_all = {}
    for gw in range(1, gameweek + 1):
        gw_results = fetch_results(gw)
        results_dict_all.update(gw_results)

    # Results for selected gameweek
    results_dict_current = fetch_results(gameweek)

    # Gameweek points
    gameweek_scores = []
    for player in PLAYERS:
        cur.execute("SELECT match_id,prediction FROM predictions WHERE player_id=%s AND gameweek=%s",
                    (player, gameweek))
        preds = cur.fetchall()
        points = sum(1 for m, p in preds if str(m) in results_dict_current and results_dict_current[str(m)] == p)
        gameweek_scores.append({"player": player, "points": points})

    # Accumulated points
    accumulated_scores = []
    for player in PLAYERS:
        cur.execute("SELECT match_id,prediction FROM predictions WHERE player_id=%s", (player,))
        preds = cur.fetchall()
        points = sum(1 for m, p in preds if str(m) in results_dict_all and results_dict_all[str(m)] == p)
        accumulated_scores.append({"player": player, "total": points})

    cur.close()
    conn.close()

    gameweek_points = {row['player']: row['points'] for row in gameweek_scores}
    total_points = {row['player']: row['total'] for row in accumulated_scores}

    return render_template(
        "results.html",
        gameweek=gameweek,
        gameweek_points=gameweek_points,
        total_points=total_points
    )

if __name__ == "__main__":
    app.run(debug=True)
