import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_calendar_service():
    # Load the token you just created
    creds = Credentials.from_authorized_user_file('token.json')
    
    # If the token is expired, refresh it automatically
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save the refreshed token
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

service = get_calendar_service()

# --- Example: List the next 10 events ---
print("Getting the upcoming 10 events...")
events_result = service.events().list(calendarId='primary', maxResults=10, 
                                    singleEvents=True, orderBy='startTime').execute()
events = events_result.get('items', [])

if not events:
    print('No upcoming events found.')
for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    print(f"{start} - {event['summary']}")