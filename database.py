"""
République RP — Entrée principale
Lance le bot Discord ET le serveur web Flask dans le même process.
Compatible Render (free tier) avec keep-alive intégré.
"""
import os, json, threading, time
from flask import Flask, render_template, request, jsonify, abort
from dotenv import load_dotenv
import database as db

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))
WEB_URL = os.environ.get("WEB_URL", "http://localhost:5000")

# ── KEEP-ALIVE (évite le sleep Render en se pinguant lui-même) ───
def keep_alive():
    """Ping automatique toutes les 5 minutes pour rester éveillé sur Render."""
    import urllib.request
    time.sleep(60)  # attendre que le serveur soit prêt
    while True:
        try:
            urllib.request.urlopen(f"{WEB_URL}/ping", timeout=10)
            print("[keep-alive] ping ok")
        except Exception as e:
            print(f"[keep-alive] erreur: {e}")
        time.sleep(270)  # 4min30 < 5min Render timeout

# ── ROUTES ───────────────────────────────────────────────────────

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/")
def index():
    return render_template("index.html", web_url=WEB_URL, token="None", char="null")

@app.route("/creer")
def creer():
    token = request.args.get("token", "")
    if not token:
        return render_template("index.html", web_url=WEB_URL, token="None", char="null")
    session = db.get_session(token)
    if not session:
        return render_template("error.html", message="Lien invalide ou expiré. Relancez /creer dans Discord.")
    char = db.get_character_by_user(session["discord_id"], session["guild_id"])
    return render_template("index.html",
        web_url=WEB_URL, token=token,
        char=json.dumps(char) if char else "null")

@app.route("/api/save", methods=["POST"])
def api_save():
    token = request.json.get("token","")
    if not token:
        return jsonify({"error":"Token manquant"}), 400
    session = db.get_session(token)
    if not session:
        return jsonify({"error":"Session invalide ou expirée"}), 401
    data = request.json.get("character",{})
    if not data.get("name"):
        return jsonify({"error":"Nom obligatoire"}), 400
    cid = db.upsert_character(session["discord_id"], session["guild_id"], data)
    return jsonify({"ok": True, "id": cid})

@app.route("/api/chars/<guild_id>")
def api_chars(guild_id):
    return jsonify(db.list_characters(guild_id))

# ── LANCEMENT ────────────────────────────────────────────────────

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def run_bot():
    import bot as discord_bot
    discord_bot.bot.run(os.environ["DISCORD_TOKEN"])

if __name__ == "__main__":
    # Keep-alive thread
    threading.Thread(target=keep_alive, daemon=True).start()
    # Web server thread
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    # Bot (blocking, main thread)
    run_bot()
