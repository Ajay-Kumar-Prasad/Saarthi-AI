import requests
from google import genai
import json
import re

# INIT CLIENT
client = genai.Client(api_key="AIzaSyBtTD6eAilNXiLz3_7dtSJdsdWmGO5spws")


def call_tool(tool, args):
    res = requests.post("http://localhost:8000/execute", json={
        "tool": tool,
        "args": args
    })
    return res.json()["result"]


def chat(user_input):
    tools = requests.get("http://localhost:8000/tools").json()

    prompt = f"""
    You are a finance assistant.

    Available tools:
    {tools}

    If user logs expense → use add_expense  
    If asking total → use get_total_spending  
    If asking last → use get_last_expense  

    Respond ONLY in RAW JSON.
    Do NOT use markdown.
    Example:
    {{
        "tool": "tool_name",
        "args": {{}}
    }}

    User: {user_input}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()

    # 🔥 Remove markdown if model still adds it
    clean_text = re.sub(r"```json|```", "", text).strip()

    try:
        action = json.loads(clean_text)

        result = call_tool(action["tool"], action.get("args", {}))
        return result

    except Exception as e:
        return f"⚠️ Error parsing tool call: {clean_text}"


# RUN LOOP
while True:
    user = input("You: ")
    print("Bot:", chat(user))