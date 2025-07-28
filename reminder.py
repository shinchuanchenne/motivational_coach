import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_mail import Mail, Message
from flask import Flask
from dotenv import load_dotenv
import datetime
import schedule
import time

app = Flask(__name__)
load_dotenv()

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

def find_users_not_checked_in():
    today = datetime.date.today()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.email, u.name
        FROM users u
        JOIN goals g ON g.user_id = u.id
        LEFT JOIN checkins c ON c.user_id = u.id AND c.goal_id = g.id AND c.date = %s
        WHERE c.id IS NULL
        GROUP BY u.email, u.name;
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
            msg = Message(
                subject="Motivational Coach - Daily Reminder",
                recipients=[user["email"]],
                body=f"Hi {user['name']},\n\nDon't forget to check in with your motivational coach today!\n\nSee you on the platform!"
            )
            mail.send(msg)
            print(f"Send notification to {user['email']}")


#Step 5 check
schedule.every(1).minutes.do(send_reminders)

print("⏰ Email Reminder Testing (1 time every minute)...")

while True:
    schedule.run_pending()
    time.sleep(10)