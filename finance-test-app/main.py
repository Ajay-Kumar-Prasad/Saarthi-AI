import os
import json
import threading
import re
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
from db import insert_expense
app = Flask(__name__)

# -------------------- LAZY LOAD HELPERS --------------------

def get_sheet():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=scopes
    )

    client = gspread.authorize(creds)
    return client.open("expenses_sheet").sheet1

def get_model():
    import google.generativeai as genai

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    return genai.GenerativeModel("gemini-2.5-flash")

# -------------------- TOOLS --------------------

from db import insert_expense  # ADD AT TOP

def save_expense(amount, category, description=""):
    try:
        now = datetime.now()

        # ✅ Save to DB FIRST
        try:
            insert_expense(amount, category, description, now)
        except Exception as e:
            print("DB failed but continuing:", e)

        # ✅ Then save to Sheets
        sheet = get_sheet()
        sheet.append_row([str(now), amount, category, description])

        return f"✅ Saved ₹{amount} for {category}"

    except Exception as e:
        return f"ERROR: {str(e)}"

def get_last_expense():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_values()
        if len(rows) <= 1:
            return "No expenses found."
        last = rows[-1]
        return f"🧾 Last: ₹{last[1]} on {last[2]}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def get_spending_summary():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_values()[1:]
        if not rows:
            return "No data."
        summary = {}
        for row in rows:
            category = row[2]
            amount = float(row[1])
            summary[category] = summary.get(category, 0) + amount
        msg = "📊 Summary:\n"
        for k, v in summary.items():
            msg += f"- {k}: ₹{v}\n"
        return msg
    except Exception as e:
        return f"ERROR: {str(e)}"

def get_weekly_spending():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_values()[1:]
        total = sum(float(row[1]) for row in rows)
        msg = f"📅 Total spending: ₹{total}"
        if total > 3000:
            msg += "\n⚠️ High spending!"
        return msg
    except Exception as e:
        return f"ERROR: {str(e)}"

# -------------------- CHAT --------------------

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.get_json().get("message")
    try:
        model = get_model()
        prompt = f"""
You are a finance assistant.

Your job is to convert user messages into TOOL calls ONLY.
Return EXACTLY a JSON object, no extra text.

TOOLS:
1. save_expense → when user mentions spending money
2. get_last_expense → when user asks last expense
3. get_spending_summary → when user asks summary
4. get_weekly_spending → when user asks weekly

RULES:
- ALWAYS return EXACTLY one tool in JSON
- JSON format ONLY, no markdown, no explanation
- Extract amount, category, description

EXAMPLES:

User: spent 500 on food
Response: {{"tool": "save_expense", "args": {{"amount": 500, "category": "food", "description": ""}}}}

User: last expense
Response: {{"tool": "get_last_expense", "args": {{}}}}

User: weekly spending
Response: {{"tool": "get_weekly_spending", "args": {{}}}}

User: {user_msg}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        clean = re.sub(r"```json|```", "", text).strip()
        action = json.loads(clean)
        tool = action.get("tool")
        args = action.get("args", {})

        if tool == "save_expense":
            result = save_expense(args.get("amount", 0),
                                  args.get("category", "other"),
                                  args.get("description", ""))
        elif tool == "get_last_expense":
            result = get_last_expense()
        elif tool == "get_spending_summary":
            result = get_spending_summary()
        elif tool == "get_weekly_spending":
            result = get_weekly_spending()
        else:
            result = "Unknown request"

    except Exception as e:
        result = f"⚠️ Error: {str(e)}"

    return jsonify({"reply": result})

# -------------------- GMAIL SYNC --------------------

@app.route("/sync-gmail", methods=["POST"])
def sync_gmail():
    def run_sync():
        try:
            from gmail_reader import read_messages_and_save
            sheet = get_sheet()
            result = read_messages_and_save(sheet)
            print(result)  # logs to Cloud Run
        except Exception as e:
            print("Sync error:", e)
    threading.Thread(target=run_sync).start()
    return {"message": "✅ Synced Gmail"}

# -------------------- HOME UI --------------------

@app.route("/", methods=["GET"])
def home_ui():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Finance Chat Agent</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 min-h-screen p-4 flex flex-col items-center">
<div class="w-full max-w-xl bg-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[80vh]">
    <div class="bg-blue-600 p-4 font-bold text-lg flex justify-between">
        <span>💰 Finance AI Assistant</span>
        <button id="sync-btn" onclick="syncGmail()" class="bg-white text-black px-3 py-1 rounded text-sm">Sync Gmail
        </button>
    </div>
    <div id="chat-window" class="flex-1 p-4 overflow-y-auto space-y-4 text-slate-300 scroll-smooth">
        <div class="bg-slate-700 p-3 rounded-lg max-w-[80%]">Ask me "How much did I spend this week?" or tell me a new expense!</div>
    </div>
    <div class="p-4 bg-slate-700 flex gap-2">
        <input id="user-input" type="text" placeholder="Type here..." class="flex-1 bg-slate-600 border-none text-white rounded-lg px-4 py-3 outline-none">
        <button onclick="send()" class="bg-blue-600 text-white px-6 py-3 rounded-lg font-bold transition">Send</button>
    </div>
    <div id="sync-status" class="text-white mt-2"></div>
</div>

<script>
async function send() {
    const input = document.getElementById("user-input");
    const msg = input.value;
    if (!msg) return;
    input.value = "";
    const res = await fetch("/chat", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({message: msg})});
    const data = await res.json();
    const chatWindow = document.getElementById("chat-window");
    const div = document.createElement("div");
    div.innerText = data.reply;
    div.className = "text-left bg-slate-700 p-2 rounded max-w-[80%]";
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function syncGmail() {
    const btn = document.getElementById("sync-btn");
    const status = document.getElementById("sync-status");
    btn.disabled = true;
    status.innerText = "⏳ Syncing Gmail...";
    try {
        const res = await fetch("/sync-gmail", {method:"POST"});
        const data = await res.json();
        status.innerText = "✅ " + data.message;
    } catch (err) {
        console.error(err);
        status.innerText = "❌ Sync failed. Check console logs.";
    } finally {
        btn.disabled = false;
    }
}
</script>
</body>
</html>
""")

if __name__ == "__main__":
    print("🚀 Starting Flask app...")
    app.run(host="0.0.0.0", port=8080)