"""
digital_twin.py — Adithiya's Digital Twin
A simple Flask server that:
1. Answers questions as Adithiya using his resume data + OpenAI
2. Lets the owner create share tokens that give guests limited access
"""

import os
import uuid
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__, static_folder=".")
CORS(app)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ── Resume data, split into named sections (called "scopes") ──────────────────
# Each scope is a chunk of text about Adithiya.
# When someone asks a question, we find the relevant chunks and send them to
# OpenAI so it can answer as Adithiya, grounded in real facts.

KNOWLEDGE = {
    "education": """
        I'm studying Computer Engineering at Georgia Tech (BS, expected May 2028),
        with concentrations in Chip Design and Systems & Architecture, and a minor
        in AI/ML Applications. My GPA is 4.00/4.00. Courses include Data Structures
        & Algorithms, Digital Design, OOP, Multivariable Calculus, Linear Algebra.
        Before Georgia Tech I attended Thomas Jefferson High School for Science and
        Technology (TJHSS&T) in Alexandria, VA, graduating June 2025 with a 3.99 GPA.
        Notable courses: Artificial Intelligence, Robotics, AP Computer Science A,
        Mobile App Development.
    """,

    "experience": """
        In summer 2024 I interned at the National Geospatial-Intelligence Agency (NGA)
        in Springfield, VA. I researched technical components for geospatial intelligence
        and satellite data pipelines, and was part of the second inaugural NGA high
        school intern cohort contributing to the Department of Defense.

        From 2022 to 2024 I co-founded Connected Crosswalk Assistance — a smart walking
        cane for the visually impaired combining LiDAR and AI vision with 95% obstacle
        detection accuracy. I published research on SSRN (160+ downloads, 1400+ views),
        demonstrated to VDOT and NASA, and secured a 2023 provisional patent.

        In summer 2023 I was a Machine Learning Research Assistant at George Mason
        University. I built a suicide risk prediction model in Python/PyTorch achieving
        87% accuracy on 6,500+ patient records, and increased high-risk patient
        sensitivity by 12%+ while improving caching efficiency by ~36%.
    """,

    "projects": """
        64-Bit Calculator (Georgia Tech, 2025): Built in SystemVerilog, combining
        modular 32-bit adders with FSM-based controller logic. Validated across 500+
        ModelSim simulation cycles with 100% output correctness.

        Underwater ROV (2023-2025): Developed Python testing utilities and embedded
        control software in C/Arduino. Improved calibration workflows by 11% and
        reduced field debugging time by 15%.

        Forest Fire Tracking Model (2024, Java/DeepLearning4J): Built a CNN achieving
        92.4% wildfire detection accuracy across 10,000+ satellite images, with
        logarithmic normalization improving generalization by 25%.
    """,

    "skills": """
        Programming: Python, Java, JavaScript, C, C++, TypeScript, SQL, R, Kotlin, HTML/CSS.
        ML/AI: PyTorch, TensorFlow, LangChain, LlamaIndex, Scikit-learn, Numpy, Pandas.
        Frontend: React.
        Hardware: PCB Design (Altium, Eagle), Arduino, Raspberry Pi, Verilog,
        SystemVerilog, VLSI Design, Analog & Digital Circuit Design, LTSpice.
        CAD: Autodesk Fusion, AutoCAD, SolidWorks, CATIA, Blender.
    """,

    "interests": """
        Outside of engineering I enjoy Spikeball, GeoGuessr, Chess, Pickleball,
        rooting for the Washington Commanders, license plate collecting, and calligraphy.
    """
}

ALL_SCOPES = list(KNOWLEDGE.keys())

# ── Share tokens ──────────────────────────────────────────────────────────────
# Stored in memory (resets when the server restarts — fine for an MVP).
# Each token is a dict: { id, label, scopes, use_count }

tokens = {}  # token_id -> token dict


def get_relevant_chunks(question, allowed_scopes):
    """
    Find the most relevant knowledge chunks for a question.
    We score each chunk by counting how many words from the question
    appear in the chunk — simple but effective for resume-sized data.
    """
    question_words = set(question.lower().split())

    scored = []
    for scope in allowed_scopes:
        chunk = KNOWLEDGE[scope]
        chunk_words = set(chunk.lower().split())
        # Score = number of question words that appear in this chunk
        score = len(question_words & chunk_words)
        scored.append((score, scope, chunk))

    # Sort by score, highest first, take top 3
    scored.sort(reverse=True)
    top_chunks = scored[:3]

    # Build a context string to inject into the prompt
    context = ""
    for score, scope, chunk in top_chunks:
        context += f"[{scope.upper()}]\n{chunk.strip()}\n\n"

    return context


def ask_twin(question, history, allowed_scopes):
    """
    Send a question to OpenAI with:
    - A system prompt telling it to be Adithiya
    - The relevant resume chunks as context
    - The conversation history for multi-turn chat
    """
    context = get_relevant_chunks(question, allowed_scopes)

    system_prompt = f"""You are a digital twin of Adithiya Balaguru, a Computer Engineering
student at Georgia Tech. Respond in first person as Adithiya — natural, direct, and honest.
Base your answers only on the context below. If a question is outside the context,
say you'd rather not share that here. Keep answers concise (2-4 sentences).

Context about Adithiya:
{context}"""

    # Build the messages list: system + history + new question
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=300
    )

    return response.choices[0].message.content


# ── API routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/shared/<token_id>")
def shared(token_id):
    return send_from_directory(".", "index.html")


# Owner chat — full access to all scopes
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    question = data.get("message", "")
    history = data.get("history", [])
    reply = ask_twin(question, history, ALL_SCOPES)
    return jsonify({"reply": reply})


# Guest chat — only access to the scopes allowed by the token
@app.route("/api/shared/<token_id>/chat", methods=["POST"])
def shared_chat(token_id):
    if token_id not in tokens:
        return jsonify({"error": "This share link is invalid or has been revoked."}), 400

    token = tokens[token_id]
    token["use_count"] += 1

    data = request.json
    question = data.get("message", "")
    history = data.get("history", [])
    reply = ask_twin(question, history, token["scopes"])
    return jsonify({"reply": reply})


# List all share tokens
@app.route("/api/tokens", methods=["GET"])
def list_tokens():
    return jsonify(list(tokens.values()))


# Create a new share token
@app.route("/api/tokens", methods=["POST"])
def create_token():
    data = request.json
    token_id = str(uuid.uuid4())
    token = {
        "id": token_id,
        "label": data.get("label", "Untitled"),
        "scopes": data.get("scopes", ALL_SCOPES),
        "use_count": 0
    }
    tokens[token_id] = token
    return jsonify(token)


# Delete (revoke) a share token
@app.route("/api/tokens/<token_id>", methods=["DELETE"])
def delete_token(token_id):
    if token_id in tokens:
        del tokens[token_id]
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404


# List available scopes
@app.route("/api/scopes", methods=["GET"])
def get_scopes():
    return jsonify(ALL_SCOPES)


if __name__ == "__main__":
    print("Starting Adithiya's Digital Twin...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
