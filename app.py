from flask import Flask, request, render_template, redirect, url_for, session, g, flash, get_flashed_messages
from openai import OpenAI
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from init_db import init_db
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature


#Loading API
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

#Build GPT API client (will put it on .env later)
client = OpenAI(api_key=api_key)
app = Flask(__name__)
app.secret_key = 'supersecret'


# PostgreSQL connection
def get_db():
    if 'db' not in g:
        url = urlparse(os.getenv("DATABASE_URL"))
        g.db = psycopg2.connect(
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        g.db.autocommit = True
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
    error = None
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        #Generate password with hash
        password = generate_password_hash(request.form["password"])
        name = request.form["name"].strip()

        db = get_db()
        existing_user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            return "<p>Email already registered. Please use another email.</p>"
        else:
            session['pending_signup'] = {
                'email': email,
                'password': password,
                'name': name
            }

        return redirect(url_for('goal_setting'))
    return render_template("signup.html")

#Signup-goal setting
@app.route("/goal_setting", methods=["GET", "POST"])
def goal_setting():

    if 'pending_signup' not in session:
        return redirect(url_for('signup'))

    #Prevent double login
    if session.get('goals_set'):
        return redirect(url_for('index'))
    error = None
    if request.method == "POST":
        goal1 = request.form["goal1"].strip()
        goal2 = request.form["goal2"].strip()

        tone1 = "encouraging"
        tone2 = "strict"          

        if not goal1 or not goal2:
            error = "Please enter 2 goals"
        else:
            try:
                signup_data = session["pending_signup"]
                db = get_db()

                db.execute(
                    "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                    (signup_data['email'], signup_data['password'], signup_data['name'])
                )
                db.commit()

                user = db.execute("SELECT * FROM users WHERE email = ?", (signup_data['email'],)).fetchone()

                db.execute(
                    "INSERT INTO goals (user_id, goal_text, tone) VALUES (?, ?, ?)",
                    (user['id'], goal1, "encouraging")
                )
                db.execute(
                    "INSERT INTO goals (user_id, goal_text, tone) VALUES (?, ?, ?)",
                    (user['id'], goal2, "strict")
                )
                db.commit()

                session.pop('pending_signup')
                session['user_id'] = user['id']
                session['email'] = user['email']
                session['goals_set'] = True

                return redirect(url_for('index'))                
            except Exception as e:
                print("Goal setting error:", e)
                error = "Failed, please try it later."

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
            return redirect(url_for('login'))  # Redirect insead of render_template
        
    return render_template("login.html", error=error)


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    # Using Flask as secret_key
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        # Find this email is exist or not?
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        # Show user that this email is not exist.
        if not user:
            if session.get('lang') == 'zh':
                error = "該 Email 不存在"
            else:
                error = "Email not found"
            return render_template("forgot_password.html", error=error)
        

        # Generate token and set reset URL
        s = URLSafeTimedSerializer(app.secret_key)
        token = s.dumps(email, salt="password-reset")
        reset_link = url_for("reset_password", token=token, _external=True)
        return render_template("show_reset_link.html", reset_link=reset_link)
    return render_template("forgot_password.html")

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        #User send new password
        password = request.form["password"]

        s = URLSafeTimedSerializer(app.secret_key)

        try:
            email = s.loads(token, salt="password-reset", max_age=1800)
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

            if not user:
                return "<p>Cannot find user email.</p>"
            
            hashed_pw = generate_password_hash(password)

            db.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_pw, email))
            db.commit()

            return """
    <p>Password is updated, please log in again.</p>
    <a href='/login'>Go to Login Page</a><br>
"""


        except SignatureExpired:
            return "<p>Link has expired, please apply it again.</p>"
        except BadSignature:
            return "<p>Invalid reset link</p>"
    else:
        #Show new password form.
        return render_template("reset_password.html", token=token)

@app.route("/index", methods=["GET", "POST"])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    gpt_model = "gpt-4.1"

    import datetime
    db = get_db()
    goals = db.execute(
        "SELECT id, goal_text, tone FROM goals WHERE user_id = ? ORDER BY id",
        (session['user_id'],)
    ).fetchall()

    goal1_id = goals[0]['id']
    goal2_id = goals[1]['id']

    response = ""

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

    plan1 = session.get("plan1", "")
    plan2 = session.get("plan2", "")

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
        

        # Check if this is a "daily plan generation" request
        elif 'user_note' in request.form:
            user_note = request.form.get("user_note", "").strip()

            # Find the goal
            goal = next((g for g in goals if g['id'] == goal_id), None)
            tone = goal["tone"] if goal else "encouraging"

            instruction = f"Based on the user's goal: {goal['goal_text']}, generate a short, doable plan for today."
            if user_note:
                instruction += f" The user says: '{user_note}."
            if session.get('lang') == 'zh':

                instruction += " Please reply in Traditional Chinese as used in Taiwan."
            if tone == "strict":
                instruction = f"You are a strict and demanding coach. {instruction} Be firm and push the user to do better."
            elif tone == "encouraging":
                instruction = f"You are a warm and supportive coach. {instruction} Encourage the user kindly and positively."
            
            messages = [{"role": "system", "content": instruction}]
            messages.append({"role": "user", "content": "What is the plan"})

            completion = client.chat.completions.create(
                model=gpt_model,
                messages=messages
            )
            plan_text = completion.choices[0].message.content.strip()

            # Storage variable
            plan1 = plan2 = ""
            if goal_id == goal1_id:
                plan1 = plan_text
                session['plan1'] = plan_text
            elif goal_id == goal2_id:
                plan2 = plan_text
                session['plan2'] = plan_text

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
                checked2=checked2,
                plan1=session.get("plan1",""),
                plan2=session.get("plan2","")
            )
            
        # Otherwise it is "GPT Conversation"
        if 'user_input' in request.form:
            user_input = request.form.get("user_input","").strip()
            
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
                
        print(f"Session: {session.get('lang')}")
        # If language is Chinese, use traditional Chinese:
        if session.get('lang') == 'zh':
            instruction += " Please reply in Traditional Chinese as used in Taiwan. "

        # Build message (system + history + user_input)
        messages = [{"role": "system", "content": instruction}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["message"]})
        messages.append({"role": "user", "content": user_input})

        print(messages)

        # Send this to GPT
        from openai import OpenAI
        #client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model = gpt_model,
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
        return redirect(url_for('index'))
    

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
        checked2=checked2,
        plan1=session.get("plan1", ""),
        plan2=session.get("plan2","")
        
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
   app.run(debug=True)
