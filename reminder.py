import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_mail import Mail, Message
from flask import Flask
from dotenv import load_dotenv
import datetime
from openai import OpenAI



# Load API and environment
app = Flask(__name__)
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS") == 'True'
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")
mail = Mail(app)

def get_db():
    url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(url,cursor_factory=RealDictCursor)
    return conn

# GPT generate letter
def generate_email_body(name, goal_text, tone, language="en"):
    if tone == "encouraging":
        prompt = (
            f"You are a warm and supportive coach. Write a short, encouraging daily reminder notification, no more than 100 words. "
            f"to {name} who is working on the goal: '{goal_text}'. End with a motivational call to action to check in today."
            f"Only generate the context of the short letter!, your name will be 'encouraging coach'."
        )
    elif tone == "strict":
        prompt = (
            f"You are a strict and demanding coach. Write a short, firm reminder notification to {name}, no more than 100 words. "
            f"about the goal: '{goal_text}'. Push them to act and end with a strong call to action to check in now."
            f"Only generate the context of the short letter!, your name will be ' strict coach'."

        )
    else:
        prompt = f"Write a motivational email to {name} about their goal: '{goal_text}'."

    if language == 'en':
        prompt += " Please reply in English, no any other language in letter."
    if language == 'zh':
        prompt += " Please reply in Traditional Chinese as used in Taiwan."

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "What should the email say?"}
    ]
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages
    )
    return response.choices[0].message.content.strip()


def find_users_not_checked_in():
    today = datetime.date.today()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.email, u.name, u.language, g.goal_text, g.tone
        FROM users u
        JOIN goals g ON g.user_id = u.id
        LEFT JOIN checkins c 
            ON c.user_id = u.id AND c.goal_id = g.id AND c.date = %s
        WHERE c.id IS NULL
    """, (today,))
    users = cur.fetchall()
    conn.close()
    return users


#Step 4:
def send_reminders():
    users = find_users_not_checked_in()
    if not users:
        print("All user has checked-in today!")
        return
    
    with app.app_context():
        for user in users:
            name = user['name']
            email = user['email']
            goal = user['goal_text']
            tone = user['tone']
            language = user.get('language', 'en')

            # Generated content
            body = generate_email_body(name, goal, tone, language)

            msg = Message(
                subject="Motivational Coach - Daily Reminder",
                recipients=[email],
                body=body
            )
            mail.send(msg)
            print(f"Sent reminder to: {email}")
            print(f"Content: {body}")

if __name__ == "__main__":
    print("Sending daily email reminders (one-time execution)...")
    send_reminders()