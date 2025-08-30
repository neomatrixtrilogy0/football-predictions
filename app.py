import os
import datetime as dt
import requests
from flask import Flask, render_template_string, request, redirect, url_for
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

app = Flask(__name__)

predictions = {}
results = {}

# ----------- API FUNCTIONS ----------------
def get_matches(week):
    url = f"https://api.football-data.org/v4/competitions/PL/matches?season=2025&matchday={week}"
    headers = {"X-Auth-Token": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("matches", [])
    else:
        print("API error:", response.text)
        return []

def parse_kickoff(kickoff_str):
    return dt.datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))

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

# ----------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        week = int(request.form["week"])
        player = request.form["player"]
        predictions.setdefault(week, {}).setdefault(player, {})

        # Save all predictions for selected week
        for key, choice in request.form.items():
            if key.startswith("match_"):
                match_id = int(key.split("_")[1])
                predictions[week][player][match_id] = choice
        return redirect(url_for("week_view", week=week))

    return render_template_string("""
    <html>
    <head>
        <title>Football Predictions 2025/26</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f4f4f9; margin: 0; padding: 20px; }
            h1, h2, h3 { text-align: center; }
            select, button { padding: 8px 12px; margin: 5px; font-size: 16px; }
            table { width: 60%; margin: 10px auto; border-collapse: collapse; background: #fff; }
            th, td { padding: 8px; text-align: center; border: 1px solid #ccc; }
            th { background: #007BFF; color: white; }
            tr:nth-child(even) { background: #f2f2f2; }
            form { text-align: center; margin-bottom: 30px; }
            .match-select { margin-bottom: 15px; }
            .container { max-width: 900px; margin: auto; }
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
            </select>
            <br>
            <label>Select Player:</label>
            <select name="player">
                {% for p in ["Biniam A","Biniam G","Biniam E","Abel","Siem","Kubrom"] %}
                    <option value="{{ p }}">{{ p }}</option>
                {% endfor %}
            </select>
            <br><br>
            <button type="submit">Continue</button>
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
        predictions.setdefault(week, {}).setdefault(player, {})
        for key, choice in request.form.items():
            if key.startswith("match_"):
                match_id = int(key.split("_")[1])
                predictions[week][player][match_id] = choice
        return redirect(url_for("week_view", week=week))

    return render_template_string("""
    <html>
    <head>
        <title>Gameweek {{ week }}</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f9f9f9; margin: 0; padding: 20px; }
            h1, h2, h3 { text-align: center; }
            .container { max-width: 900px; margin: auto; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; background: #fff; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
            th { background: #007BFF; color: white; }
            tr:nth-child(even) { background: #f2f2f2; }
            form { text-align: center; margin-bottom: 20px; }
            select, button { padding: 8px 12px; font-size: 16px; margin: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
        <h1>Gameweek {{ week }}</h1>
        <form method="post">
            <label>Select Player:</label>
            <select name="player">
                {% for p in ["Player1","Player2","Player3","Player4","Player5","Player6"] %}
                    <option value="{{ p }}">{{ p }}</option>
                {% endfor %}
            </select>
            <table>
                <tr>
                    <th>Match</th>
                    <th>Prediction</th>
                </tr>
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
        </div>
    </body>
    </html>
    """, week=week, matches=matches)

if __name__ == "__main__":
    app.run(debug=True)
