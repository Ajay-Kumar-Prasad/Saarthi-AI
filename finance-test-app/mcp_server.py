from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

conn = sqlite3.connect("finance.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL,
    category TEXT,
    description TEXT
)
""")
conn.commit()


# ---------------- TOOLS ----------------

@app.route("/tools", methods=["GET"])
def list_tools():
    return jsonify([
        {"name": "add_expense", "description": "Add new expense"},
        {"name": "get_total_spending", "description": "Get total spending"},
        {"name": "get_last_expense", "description": "Get last expense"}
    ])


@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.get_json().get("message")

    # 🔥 Get tools from MCP server
    tools = requests.get("http://localhost:8000/tools").json()

    prompt = f"""
    You are a finance assistant.

    Available tools:
    {tools}

    If user logs expense → use add_expense  
    If asking total → use get_total_spending  
    If asking last → use get_last_expense  

    Respond ONLY in JSON:
    {{
        "tool": "tool_name",
        "args": {{}}
    }}

    User: {user_msg}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()
    clean_text = re.sub(r"```json|```", "", text).strip()

    try:
        action = json.loads(clean_text)

        result = requests.post(
            "http://localhost:8000/execute",
            json={
                "tool": action["tool"],
                "args": action.get("args", {})
            }
        ).json()["result"]

        return jsonify({"reply": result})

    except:
        return jsonify({"reply": text})


if __name__ == "__main__":
    app.run(port=8000)