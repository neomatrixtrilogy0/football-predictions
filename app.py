import os
import psycopg2
from flask import Flask, render_template, request
from dotenv import load_dotenv

# Load .env file
load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")  # Your Render Postgres DB
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")  # Football-Data API key

# List of players
PLAYERS = ["Biniam A", "Biniam G", "Biniam E", "Abel", "Siem", "Kubrom"]


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# ✅ Home Page (Choose player + gameweek)
@app.route("/")
def index():
    return render_template("index.html", players=PLAYERS, gameweeks=range(1, 39))


# ✅ Show fixtures for selected gameweek
@app.route("/gameweek", methods=["POST"])
def show_gameweek():
    player_id = request.form["player_id"]
    gameweek = int(request.form["gameweek"])

    # Example: Fetch fixtures (replace with Football-Data API calls)
    fixtures = [
        {"id": 1, "home": "Arsenal", "away": "Chelsea"},
        {"id": 2, "home": "Liverpool", "away": "Man City"},
    ]

    return render_template(
        "gameweek.html",
        player_id=player_id,
        gameweek=gameweek,
        fixtures=fixtures,
    )


# ✅ Submit predictions
@app.route("/submit_prediction", methods=["POST"])
def submit_prediction():
    player_id = request.form["player_id"]
    gameweek = int(request.form["gameweek"])

    conn = get_db_connection()
    cur = conn.cursor()

    for key, value in request.form.items():
        if key.startswith("match_"):
            match_id = key.split("_")[1]
            cur.execute(
                """
                INSERT INTO predictions (player_id, match_id, gameweek, prediction)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (player_id, match_id) DO UPDATE SET prediction = EXCLUDED.prediction
                """,
                (player_id, match_id, gameweek, value),
            )

    conn.commit()
    cur.close()
    conn.close()

    return render_template("confirmation.html", gameweek=gameweek)


# ✅ Show results
@app.route("/results/<int:gameweek>")
def results(gameweek):
    conn = get_db_connection()
    cur = conn.cursor()

    # Mock results — replace with API data
    results = {
        1: {"winner": "Arsenal"},
        2: {"winner": "Liverpool"},
    }

    # Gameweek table
    gameweek_scores = []
    for player in PLAYERS:
        cur.execute(
            "SELECT match_id, prediction FROM predictions WHERE player_id=%s AND gameweek=%s",
            (player, gameweek),
        )
        predictions = cur.fetchall()

        points = 0
        for match_id, pred in predictions:
            if str(match_id) in results and results[int(match_id)]["winner"] == pred:
                points += 1

        gameweek_scores.append({"player": player, "points": points})

    # Accumulated points
    accumulated_scores = []
    for player in PLAYERS:
        cur.execute("SELECT match_id, prediction, gameweek FROM predictions WHERE player_id=%s", (player,))
        predictions = cur.fetchall()

        total_points = 0
        for match_id, pred, gw in predictions:
            if str(match_id) in results and results[int(match_id)]["winner"] == pred:
                total_points += 1

        accumulated_scores.append({"player": player, "total": total_points})

    cur.close()
    conn.close()

    return render_template(
        "results.html",
        gameweek=gameweek,
        gameweek_scores=gameweek_scores,
        accumulated_scores=accumulated_scores,
    )


if __name__ == "__main__":
    app.run(debug=True)
