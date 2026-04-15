# gmail_reader.py
import re
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from datetime import datetime
# Optional DB persist can use db.finance_db.insert_expense via an async bridge if needed.

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    with open("token.json", "r") as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=SCOPES
    )

    if creds.expired:
        creds.refresh(Request())
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def read_messages_and_save(sheet, max_results=200):
    service = get_gmail_service()

    results = service.users().messages().list(
        userId='me',
        q="(credited OR debited OR spent OR transaction OR INR OR ₹)",
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])
    saved = 0

    for msg in messages:
        try:
            txt = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata'
            ).execute()

            snippet = txt.get("snippet", "")
            match = re.search(r'(?:₹|INR)\s?(\d+)', snippet)
            if not match:
                continue

            amount = int(match.group(1))

            snippet_lower = snippet.lower()
            if "uber" in snippet_lower or "ola" in snippet_lower:
                category = "transport"
            elif "amazon" in snippet_lower or "flipkart" in snippet_lower:
                category = "shopping"
            elif "food" in snippet_lower or "swiggy" in snippet_lower or "zomato" in snippet_lower:
                category = "food"
            else:
                category = "other"

            # ✅ Prepare common values
            now = datetime.now()
            description = snippet[:100]

            # ✅ 1. SAVE TO ALLOYDB (SAFE - WON’T BREAK APP)
            #insert_expense(amount, category, description, now)

            # ✅ 2. KEEP EXISTING SHEETS LOGIC (UNCHANGED)
            sheet.append_row([
                str(now),
                amount,
                category,
                description
            ])

            saved += 1

        except Exception as e:
            print("❌ Error processing message:", e)
            continue

    print(f"✅ Total {saved} expenses saved from Gmail")
    return f"✅ {saved} expenses auto-saved from Gmail"
