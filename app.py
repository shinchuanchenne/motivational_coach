from flask import Flask, request, render_template, redirect, url_for, session, g, flash, get_flashed_messages
from openai import OpenAI
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import datetime
from dotenv import load_dotenv

#Loading API
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

#Build GPT API client (will put it on .env later)
client = OpenAI(api_key=api_key)
app = Flask(__name__)
app.secret_key = 'supersecret'
DATABASE = 'database.db'


# Connect sqlite
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()

#Redirect to home
@app.route("/")
def home():
    return redirect(url_for('login'))


#login
@app.route("/set_language", methods=["GET"])
def set_language():
    lang = request.args.get('lang', 'en') 
    session['lang'] = lang
    return redirect(url_for('login'))

#Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        #Generate password with hash
        password = generate_password_hash(request.form["password"])
        name = request.form["name"].strip()

        db = get_db()

        existing_user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            return "<p>Email already registered. Please use another email.</p>"

        db.execute(
            "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
            (email, password, name)
        )
        db.commit()

        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        # Auto login
        session['user_id'] = user['id']
        session['email'] = user['email']

        return redirect(url_for('goal_setting'))
    return render_template("signup.html")

#Signup-goal setting
@app.route("/goal_setting", methods=["GET", "POST"])
def goal_setting():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    #Prevent double login
    if session.get('goals_set'):
        return redirect(url_for('index'))
    error = None
    if request.method == "POST":
        goal1 = request.form["goal1"].strip()
        goal2 = request.form["goal2"].strip()

        tone1 = "encouraging"
        tone2 = "strict"  
        # Save to db
        db = get_db()
        db.execute(
            "INSERT INTO goals (user_id, goal_text, tone) VALUES (?, ?, ?)",
            (session['user_id'], goal1, tone1)
            )
        db.execute(
            "INSERT INTO goals (user_id, goal_text, tone) VALUES (?, ?, ?)",
            (session['user_id'], goal2, tone2)
            )
        db.commit()
        session['goals_set'] = True

        return redirect(url_for('index'))

    return render_template("goal_setting.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == 'POST':
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password"], password):
            #Login success
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['goals_set'] = False
            return redirect(url_for('index'))
        else:
            #Login fail
            flash("帳號或密碼錯誤" if session.get('lang') == 'zh' else "Invalid email or password")
            return redirect(url_for('login'))  # ✅ Redirect 而不是 render_template
        
    return render_template("login.html", error=error)


@app.route("/index", methods=["GET", "POST"])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    import datetime
    db = get_db()
    goals = db.execute(
        "SELECT id, goal_text, tone FROM goals WHERE user_id = ? ORDER BY id",
        (session['user_id'],)
    ).fetchall()

    goal1_id = goals[0]['id']
    goal2_id = goals[1]['id']

    response = ""

    if request.method == "POST":
        goal_id = int(request.form["goal_id"])
        today = datetime.date.today()
        
        # Check whether is "check-in" request. 
        if 'checkin' in request.form:
            if request.form.get("checkin") == '1':
                today = datetime.date.today()
                already = db.execute(
                    "SELECT * FROM checkins WHERE user_id = ? AND goal_id = ? AND date = ?",
                    (session['user_id'], goal_id, today)
                ).fetchone()

                if not already:
                    db.execute(
                        "INSERT INTO checkins (user_id, goal_id, date, completed) VALUES (?, ?, ?, ?)",
                        (session['user_id'], goal_id, today, True)
                    )
                    db.commit()
                    flash("Check-in recorded!")
                else:
                    flash("You've already checked in today!")

                return redirect(url_for('index'))
            elif request.form["checkin"] == "0":
                # Undo check-in
                db.execute(
                    "DELETE FROM checkins WHERE user_id = ? AND goal_id = ? AND date = ?",
                    (session['user_id'], goal_id, today)
                )
                db.commit()
                flash("Check-in undone!")
            return redirect(url_for('index'))

        # Otherwise it is "GPT Conversation"
        user_input = request.form["user_input"]
        goal = next((g for g in goals if g["id"] == goal_id), None)
        tone = goal["tone"] if goal else "encouraging"

        db = get_db()

        #Get user data
        user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

        # Get history
        history = db.execute("SELECT role, message FROM conversations WHERE user_id = ? AND goal_id = ? ORDER BY timestamp ASC",
                             (session['user_id'], goal_id)).fetchall()

        instruction = "You are a assistant."
        if tone == "strict":
            instruction = f"You are a strict and demanding coach helping {user['name']} achieve the goal: '{goal['goal_text']}. Be firm and push them to do better."
        elif tone == "encouraging":
            instruction = f"You are a warm and supportive coach who praises the user: {user['name']} stay motivated for the goal: '{goal['goal_text']}. Encourages them with kindness and support."
        
        # Build message (system + history + user_input)
        messages = [{"role": "system", "content": instruction}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["message"]})
        messages.append({"role": "user", "content": user_input})

        print(messages)

        # Send this to GPT
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        response = completion.choices[0].message.content

        db.execute(
            "INSERT INTO conversations (user_id, goal_id, role, message) VALUES (?, ?, ?, ?)",
            (session['user_id'], goal_id, "user", user_input)
        )
        db.execute(
            "INSERT INTO conversations (user_id, goal_id, role, message) VALUES (?, ?, ?, ?)",
            (session['user_id'], goal_id, "assistant", response)
        )
        db.commit()

    # No matter both check-in or conversation need to update the newest record
    history1 = db.execute(
        "SELECT role, message, timestamp FROM conversations WHERE user_id = ? AND goal_id = ? ORDER BY timestamp ASC",
        (session['user_id'], goal1_id)
    ).fetchall()

    history2 = db.execute(
        "SELECT role, message, timestamp FROM conversations WHERE user_id = ? AND goal_id = ? ORDER BY timestamp ASC",
        (session['user_id'], goal2_id)
    ).fetchall()

    checkins1 = db.execute(
        "SELECT date, completed FROM checkins WHERE user_id = ? AND goal_id = ? ORDER BY date DESC",
        (session['user_id'], goal1_id)
    ).fetchall()

    checkins2 = db.execute(
        "SELECT date, completed FROM checkins WHERE user_id = ? AND goal_id = ? ORDER BY date DESC",
        (session['user_id'], goal2_id)
    ).fetchall()

    today = datetime.date.today()
    checked1 = db.execute(
        "SELECT * FROM checkins WHERE user_id = ? AND goal_id = ? AND date = ?",
        (session['user_id'], goal1_id, today)
    ).fetchone()

    checked2 = db.execute(
        "SELECT * FROM checkins WHERE user_id = ? AND goal_id = ? AND date = ?",
        (session['user_id'], goal2_id, today)
    ).fetchone()

    return render_template(
        "index.html",
        response=response,
        session=session,
        goals=goals,
        history1=history1,
        history2=history2,
        checkins1=checkins1,
        checkins2=checkins2,
        checked1=checked1,
        checked2=checked2
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
