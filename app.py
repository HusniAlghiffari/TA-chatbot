from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, session, render_template, flash
from flask_cors import CORS
from dotenv import load_dotenv
import bcrypt
import os
from datetime import datetime, timedelta
import sqlite3
import json
import random
from fuzzywuzzy import fuzz

# Import Zhipu AI
from zai import ZhipuAiClient

# ---------------- Setup Flask App ---------------- #
app = Flask(__name__, static_folder="static", static_url_path='')
CORS(app)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY", "default_secret")
app.permanent_session_lifetime = timedelta(hours=2)

# ---------------- Credentials & API ---------------- #
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_HASHED_PASSWORD = os.getenv("ADMIN_HASHED_PASSWORD", "").encode("utf-8")

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
client = ZhipuAiClient(api_key=ZHIPU_API_KEY)


# ---------------- Load Dataset JSON (Bendera) ---------------- #
dataset_bendera_data = {}
try:
    with open("dataset_bendera.json", "r", encoding="utf-8") as f:
        dataset_bendera_data = json.load(f)
except Exception as e:
    print("⚠️ Gagal load dataset_bendera.json:", e)

# ---------------- Database Setup ---------------- #
def get_db():
    return sqlite3.connect('questions.db')

def create_table_if_not_exists():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS question_count (
            date TEXT PRIMARY KEY,
            count INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_question():
    conn = get_db()
    cursor = conn.cursor()
    today = datetime.today().strftime('%Y-%m-%d')
    cursor.execute("SELECT count FROM question_count WHERE date = ?", (today,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE question_count SET count = count + 1 WHERE date = ?", (today,))
    else:
        cursor.execute("INSERT INTO question_count (date, count) VALUES (?, ?)", (today, 1))
    conn.commit()
    conn.close()

def get_today_question_count():
    conn = get_db()
    cursor = conn.cursor()
    today = datetime.today().strftime('%Y-%m-%d')
    cursor.execute("SELECT count FROM question_count WHERE date = ?", (today,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

# ---------------- Helpers ---------------- #
def verify_password(input_password, stored_hash):
    return bcrypt.checkpw(input_password.encode('utf-8'), stored_hash)


def get_jawaban(dosen, nip):
    template = random.choice(jawaban_variasi)
    return template.format(dosen=dosen, nip=nip)

jawaban_variasi = [
    "NIP dari {dosen} itu adalah {nip}",
    "NIP {nip} itu punya {dosen}",
    "{dosen} punya NIP: {nip}"
]


# ---------------- Dataset Handlers ---------------- #
def handle_dataset_bendera(message: str):
    msg = message.lower()
    best_match = None
    best_score = 0
    
    for item in dataset_bendera_data.get("data_dosen", []):
        nama_dosen = item.get("nama_dosen", "").lower()
        nip = item.get("nip", "")
        
        # Hitung kesamaan menggunakan fuzzy matching
        score = fuzz.partial_ratio(msg, nama_dosen)
        
        # Jika skor cukup tinggi dan lebih baik dari sebelumnya
        if score > 70 and score > best_score:
            best_score = score
            best_match = (item.get("nama_dosen", ""), nip)
        
        # Cek NIP
        if nip.lower() in msg:
            return get_jawaban(item.get("nama_dosen", ""), nip)
    
    if best_match:
        return get_jawaban(best_match[0], best_match[1])
    
    return None


def handle_zhipu_ai(user_message: str):
    try:
        response = client.chat.completions.create(
            model="glm-4.5",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Lo sekarang jadi chatbot akademik Universitas Diponegoro (UNDIP). "
                        "Jawaban lo wajib pake bahasa santai, gaul, ala anak muda jaman sekarang 🤙, "
                        "tapi tetep sopan, singkat, jelas, dan gak keluar konteks akademik."
                    ),
                },
                {"role": "user", "content": user_message}
            ],
            thinking={"type": "enabled"},
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Error Zhipu:", e)
        return "⚠️ Maaf bro, ada error pas kita ngehubungin Server🙏"

def get_undip_response(user_message: str):
    reply = handle_dataset_bendera(user_message)
    if reply:
        return reply
    return handle_zhipu_ai(user_message)

# ---------------- Routes ---------------- #
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_message = data.get("message", "")
    save_question()
    reply = get_undip_response(user_message)
    return jsonify({"reply": reply})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and verify_password(password, ADMIN_HASHED_PASSWORD):
            session["logged_in"] = True
            return redirect(url_for("admin"))
        else:
            flash("Login gagal! Username atau password salah.", "error")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/admin")
def admin():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    create_table_if_not_exists()
    today_question_count = get_today_question_count()
    return render_template("admin_panel.html", question_count=today_question_count)

# ---------------- Main ---------------- #
if __name__ == "__main__":
    app.run(debug=True)
