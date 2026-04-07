from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import math
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend to connect from different port

# Team configuration
TEAMS = ["Team 1", "Team 2", "Team 3"]

# -----------------------------
# Data Models & In-Memory State
# -----------------------------

@dataclass
class SurveyAnswer:
    text: str
    points: int
    revealed: bool = False


def _blank_state() -> Dict[str, Any]:
    return {
        "question": None,                 # str | None
        "phase": "idle",                # "idle" | "survey" | "ready" | "in_progress" | "ended"
        "answers": [],                    # List[SurveyAnswer]
        "current_team": "Team 1",       # Which team will receive points on reveal
        "strikes": {team: 0 for team in TEAMS},
        "scores": {team: 0 for team in TEAMS},
        "round_number": 0,
    }

STATE = _blank_state()

# -----------------------------
# Frontend Routes
# -----------------------------

@app.route('/')
def serve_frontend():
    """Default route - redirect to host panel"""
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'host.html')
    return send_file(frontend_path)

@app.route('/host')
def serve_host():
    """Host control panel - for the game master"""
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'host.html')
    return send_file(frontend_path)

@app.route('/player')
def serve_player():
    """Player display screen - for projecting/sharing with players"""
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'player.html')
    return send_file(frontend_path)

# -----------------------------
# Helpers
# -----------------------------

def serialize_state() -> Dict[str, Any]:
    return {
        **{k: v for k, v in STATE.items() if k != "answers"},
        "answers": [asdict(a) for a in STATE["answers"]],
    }

def normalize_points(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    total = sum(int(i.get("points", 0)) for i in items)
    if total == 100:
        return items
    if not items:
        return items
    diff = 100 - total
    # Bump the highest-point item by the diff to force total=100
    max_idx = max(range(len(items)), key=lambda i: items[i]["points"])
    items[max_idx]["points"] += diff
    return items

# -----------------------------
# API Endpoints
# -----------------------------

@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify(serialize_state())


@app.route("/api/start_round", methods=["POST"])
def start_round():
    data = request.get_json(force=True)
    question = data.get("question")
    if not question:
        return jsonify({"error": "question required"}), 400
    STATE["question"] = question
    STATE["answers"] = []
    STATE["strikes"] = {team: 0 for team in TEAMS}
    STATE["phase"] = "survey"  # audience submitting answers now via Discord
    STATE["round_number"] += 1
    return jsonify(serialize_state())


@app.route("/api/survey_results", methods=["POST"])
def survey_results():
    # Called by the Discord bot after it closes survey and aggregates answers
    data = request.get_json(force=True)
    incoming = data.get("answers", [])
    # Expect a list of { text: str, points: int }
    answers: List[SurveyAnswer] = []
    for item in incoming:
        text = str(item.get("text", "")).strip()
        try:
            pts = int(item.get("points", 0))
        except Exception:
            pts = 0
        if text:
            answers.append(SurveyAnswer(text=text, points=pts, revealed=False))
    # Sort by points desc; normalize to sum to 100
    answers = sorted(answers, key=lambda a: a.points, reverse=True)
    normalized = normalize_points([{"text": a.text, "points": a.points} for a in answers])
    STATE["answers"] = [SurveyAnswer(**x) for x in normalized]
    STATE["phase"] = "ready"  # ready to play
    return jsonify(serialize_state())


@app.route("/api/begin_play", methods=["POST"])
def begin_play():
    print(f"Begin play called. Current phase: {STATE['phase']}")  # Debug line
    if STATE["phase"] != "ready":
        return jsonify({"error": "survey results not ready", "current_phase": STATE["phase"]}), 400
    STATE["phase"] = "in_progress"
    print(f"Phase changed to: {STATE['phase']}")  # Debug line
    return jsonify(serialize_state())


@app.route("/api/set_team", methods=["POST"])
def set_team():
    data = request.get_json(force=True)
    team = data.get("team")
    if team not in TEAMS:
        return jsonify({"error": f"team must be one of: {', '.join(TEAMS)}"}), 400
    STATE["current_team"] = team
    return jsonify(serialize_state())


@app.route("/api/reveal", methods=["POST"])
def reveal():
    data = request.get_json(force=True)
    idx = data.get("index")
    team = data.get("team", STATE["current_team"])  # optional override
    try:
        idx = int(idx)
    except Exception:
        return jsonify({"error": "index must be an integer"}), 400
    if team not in STATE["scores"]:
        return jsonify({"error": "unknown team"}), 400
    if not (0 <= idx < len(STATE["answers"])):
        return jsonify({"error": "index out of range"}), 400
    ans = STATE["answers"][idx]
    if ans.revealed:
        return jsonify({"error": "already revealed"}), 400
    ans.revealed = True
    STATE["scores"][team] += int(ans.points)
    return jsonify(serialize_state())


@app.route("/api/strike", methods=["POST"])
def strike():
    data = request.get_json(force=True)
    team = data.get("team", STATE["current_team"])  # default to current team
    if team not in STATE["strikes"]:
        return jsonify({"error": "unknown team"}), 400
    STATE["strikes"][team] = min(3, STATE["strikes"][team] + 1)
    return jsonify(serialize_state())


@app.route("/api/clear_strikes", methods=["POST"])
def clear_strikes():
    STATE["strikes"] = {team: 0 for team in TEAMS}
    return jsonify(serialize_state())


@app.route("/api/end_round", methods=["POST"])
def end_round():
    STATE["phase"] = "ended"
    return jsonify(serialize_state())


@app.route("/api/reset_game", methods=["POST"])
def reset_game():
    global STATE
    STATE = _blank_state()
    return jsonify(serialize_state())


if __name__ == "__main__":
    # Run on port 5000 for backend
    app.run(host="0.0.0.0", port=5000, debug=True)