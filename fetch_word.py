import os
import re
import random
import requests
from datetime import date

def strip_mw(text):
    return re.sub(r'\{[^}]+\}', '', text).strip()

def get_random_word():
    try:
        resp = requests.get("https://random-word-api.herokuapp.com/word", timeout=5)
        word = resp.json()[0]
        print(f"Random word API returned: {word}")
        return word
    except Exception as e:
        print(f"Random word API failed: {e}, using date-based fallback")
        fallback = ["ephemeral","serendipity","eloquent","resilient","tenacity",
                    "ambiguous","diligent","solitude","pragmatic","altruism",
                    "candid","stoic","nostalgia","empathy","meticulous"]
        random.seed(int(date.today().strftime("%Y%m%d")))
        return random.choice(fallback)

def get_mw_data(word, api_key):
    url = f"https://dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={api_key}"
    return requests.get(url).json()

def extract_definition(data):
    if not (isinstance(data, list) and data and isinstance(data[0], dict)):
        return None
    shortdefs = data[0].get("shortdef", [])
    if shortdefs:
        return shortdefs[0]
    return None

def update_readme(word, definition):
    section = f"**{word.capitalize()}**\n\nDefinition: {definition}"

    start_marker = "<!-- WORD_OF_THE_DAY_START -->"
    end_marker = "<!-- WORD_OF_THE_DAY_END -->"

    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    if start_marker not in readme or end_marker not in readme:
        print("ERROR: Markers not found in README.md")
        exit(1)

    new_readme = (
        readme.split(start_marker)[0]
        + start_marker + "\n"
        + section + "\n"
        + end_marker
        + readme.split(end_marker)[1]
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_readme)

def send_email(word, definition, resend_api_key, to_email):
    today = date.today().strftime("%B %d, %Y")
    html = f"""
    <h2>Word of the Day — {today}</h2>
    <h3>{word.capitalize()}</h3>
    <p><strong>Definition:</strong> {definition}</p>
    """
    payload = {
        "from": "Word of the Day <onboarding@resend.dev>",
        "to": [to_email],
        "subject": f"Word of the Day: {word.capitalize()} — {today}",
        "html": html
    }
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {resend_api_key}", "Content-Type": "application/json"},
        json=payload
    )
    if resp.status_code == 200:
        print(f"Email sent to {to_email}")
    else:
        print(f"Email failed: {resp.status_code} {resp.text}")

# Main
api_key = os.environ.get("MW_API_KEY")
resend_api_key = os.environ.get("RESEND_API_KEY")
to_email = os.environ.get("NOTIFY_EMAIL")

for attempt in range(5):
    word = get_random_word()
    data = get_mw_data(word, api_key)
    definition = extract_definition(data)
    if definition:
        print(f"Found: {word} — {definition}")
        break
    else:
        print(f"No MW entry for '{word}', retrying... ({attempt + 1}/5)")
else:
    print("Could not find a valid word after 5 attempts, exiting.")
    exit(1)

update_readme(word, definition)
print(f"Done: {word} — {definition}")

if resend_api_key and to_email:
    send_email(word, definition, resend_api_key, to_email)
else:
    print("Skipping email: RESEND_API_KEY or NOTIFY_EMAIL not set.")
