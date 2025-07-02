from flask import Flask, request, render_template, redirect, url_for, session, g, flash, get_flashed_messages
from openai import OpenAI
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
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
        # 儲存到資料庫
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
    
    #Get two data
    db = get_db()
    goals = db.execute(
        "SELECT goal_text, tone FROM goals WHERE user_id = ? ORDER BY id",
        (session['user_id'],)
    ).fetchall()

    #Received form
    response = ""

    if request.method == "POST":
        user_input = request.form["user_input"]

        #Call chatgpt
        completion = client.responses.create(
          model="gpt-3.5-turbo",
            input=user_input,
            instructions="You are a funny assistant, always with a lot of humour."
        )
        response = completion.output_text

        #　Save to conversations
        db = get_db()
        db.execute(
            "INSERT INTO conversations (user_id, goal_id, role, message) VALUES (?, ?, ?, ?)",
            (session['user_id'], None, "user", user_input)
            )
        
        db.execute(
            "INSERT INTO conversations (user_id, goal_id, role, message) VALUES (?, ?, ?, ?)",
            (session['user_id'], None, "gpt", response)
            )
        db.commit()

        #print(completion)
        print(response)
    return render_template("index.html", response=response, session=session, goals=goals)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
