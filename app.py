import os
import psycopg2
import requests
from flask import Flask, render_template_string, request, redirect, url_for
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

app = Flask(__name__)

# --- Database setup ---
DATABASE_URL = os.getenv("DATABASE_URL")  # you’ll paste Render Postgres URL in .env

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Players
    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    )
    """)
    # Predictions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id SERIAL PRIMARY KEY,
        player_id INTEGER REFERENCES players(id),
        match_id INTEGER,
        prediction TEXT,
        week INTEGER,
        UNIQUE(player_id, match_id)
    )
    """)
    # Results
    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        match_id INTEGER PRIMARY KEY,
        winner TEXT,
        week INTEGER
    )
    """)
    conn.commit()
    cur.close()
    conn.close()

# Stores predictions: {week: {player: {match_id: choice}}}
predictions = {}

# ---------------- API FUNCTIONS ----------------
def get_matches(week):
    url = f"https://api.football-data.org/v4/competitions/PL/matches?season=2025&matchday={week}"
    headers = {"X-Auth-Token": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("matches", [])
    else:
        print("API error:", response.text)
        return []

def get_outcome(match):
    if match["status"] == "FINISHED":
        home_score = match["score"]["fullTime"]["home"]
        away_score = match["score"]["fullTime"]["away"]
        if home_score > away_score:
            return "HOME"
        elif away_score > home_score:
            return "AWAY"
        else:
            return "TIE"
    return None

# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        week = int(request.form["week"])
        return redirect(url_for("week_view", week=week))
    return render_template_string("""
    <html>
    <head>
        <title>Football Predictions 2025/26</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f4f4f9; margin: 0; padding: 20px; }
            h1, h2 { text-align: center; }
            select, button { padding: 8px 12px; margin: 5px; font-size: 16px; }
            .container { max-width: 600px; margin: auto; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Football Predictions 2025/26</h1>
            <form method="post">
                <label>Select Gameweek:</label>
                <select name="week">
                    {% for w in range(1,39) %}
                        <option value="{{ w }}">Gameweek {{ w }}</option>
                    {% endfor %}
                </select><br><br>
                <button type="submit">Go</button>
            </form>
        </div>
    </body>
    </html>
    """)

@app.route("/week/<int:week>", methods=["GET", "POST"])
def week_view(week):
    matches = get_matches(week)

    if request.method == "POST":
        player = request.form["player"]
        predictions.setdefault(str(week), {}).setdefault(player, {})
        for key, choice in request.form.items():
            if key.startswith("match_"):
                match_id = key.split("_")[1]
                predictions[str(week)][player][match_id] = choice
        return redirect(url_for("week_view", week=week))

    # -------- Calculate week scores ----------
    week_scores = {}
    for p, preds in predictions.get(str(week), {}).items():
        points = 0
        for match in matches:
            match_id = str(match["id"])
            outcome = get_outcome(match)
            if outcome and preds.get(match_id) == outcome:
                points += 1
        week_scores[p] = points

    # -------- Calculate accumulated scores ----------
    accumulated_scores = {}
    for w, week_data in predictions.items():
        w_matches = get_matches(int(w))
        for p, preds in week_data.items():
            accumulated_scores.setdefault(p, 0)
            for match in w_matches:
                match_id = str(match["id"])
                outcome = get_outcome(match)
                if outcome and preds.get(match_id) == outcome:
                    accumulated_scores[p] += 1

    return render_template_string("""
    <html>
    <head>
        <title>Gameweek {{ week }}</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f9f9f9; margin: 0; padding: 20px; }
            h1, h2 { text-align: center; }
            table { width: 90%; margin: 20px auto; border-collapse: collapse; background: #fff; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
            th { background: #007BFF; color: white; }
            tr:nth-child(even) { background: #f2f2f2; }
            select, button { padding: 8px 12px; font-size: 16px; margin: 5px; }
            .container { max-width: 900px; margin: auto; }
            form { text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
        <h1>Gameweek {{ week }}</h1>
        <form method="post">
            <label>Select Player:</label>
            <select name="player">
                {% for p in ["Biniam A","Biniam G","Biniam E","Abel","Siem","Kubrom"] %}
                    <option value="{{ p }}">{{ p }}</option>
                {% endfor %}
            </select>
            <table>
                <tr><th>Match</th><th>Prediction</th></tr>
                {% for m in matches %}
                <tr>
                    <td>{{ m['homeTeam']['name'] }} vs {{ m['awayTeam']['name'] }}</td>
                    <td>
                        <select name="match_{{ m['id'] }}">
                            <option value="HOME">Home Win ({{ m['homeTeam']['name'] }})</option>
                            <option value="AWAY">Away Win ({{ m['awayTeam']['name'] }})</option>
                            <option value="TIE">Tie</option>
                        </select>
                    </td>
                </tr>
                {% endfor %}
            </table>
            <button type="submit">Submit All Predictions</button>
        </form>

        {% if week_scores %}
        <h2>Week {{ week }} Results</h2>
        <table>
            <tr><th>Player</th><th>Points</th></tr>
            {% for p, pts in week_scores.items() %}
                <tr><td>{{ p }}</td><td>{{ pts }}</td></tr>
            {% endfor %}
        </table>
        {% endif %}

        {% if accumulated_scores %}
        <h2>Accumulated Points</h2>
        <table>
            <tr><th>Player</th><th>Total Points</th></tr>
            {% for p, pts in accumulated_scores.items() %}
                <tr><td>{{ p }}</td><td>{{ pts }}</td></tr>
            {% endfor %}
        </table>
        {% endif %}
        </div>
    </body>
    </html>
    """, week=week, matches=matches, week_scores=week_scores, accumulated_scores=accumulated_scores)

if __name__ == "__main__":
    app.run(debug=True)
