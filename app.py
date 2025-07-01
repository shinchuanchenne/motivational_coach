from flask import Flask, request, render_template, redirect, url_for, session, g
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

#login
@app.route("/set_language", methods=["POST"])
def set_language():
    session['lang'] = request.form.get('lang','en')
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
        # 自動登入
        session['user_id'] = user['id']
        session['email'] = user['email']

        return redirect(url_for('goal_setting'))
    return render_template("signup.html")

#Signup-goal setting
@app.route("/goal_setting", methods=["GET", "POST"])
def goal_setting():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    error = None
    if request.method == "POST":
        goal1 = request.form["goal1"].strip()
        goal2 = request.form["goal2"].strip()
        tone1 = request.form["tone1"]
        tone2 = request.form["tone2"]      

        if tone1 == tone2 and tone1 != "random":
            error = "請為兩個目標設定不同的語氣風格"  
        else:
            import random
            # 如果 tone 是 random，就從另一個 tone 裡隨機指定
            if tone1 == "random":
                tone1 = random.choice(["encouraging", "strict"])
                # 確保 tone2 不同
                if tone2 == tone1:
                    tone2 = "strict" if tone1 == "encouraging" else "encouraging"
            elif tone2 == "random":
                tone2 = "strict" if tone1 == "encouraging" else "encouraging"            


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

            return redirect(url_for('index'))

    return render_template("goal_setting.html", error=error)

@app.route("/")
def home():
    return redirect(url_for('login'))


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
            return redirect(url_for('index'))
        else:
            #Login fail
            error = "帳號或密碼錯誤" if session.get('lang') == 'zh' else "Invalid email or password"

    return render_template("login.html", error=error)



@app.route("/index", methods=["GET", "POST"])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
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
        db = get_db()
        db.execute(
            "INSERT INTO chats (user_input, gpt_response) VALUES (?, ?)",
            (user_input, response)
        )
        db.commit()

        #print(completion)
        print(response)
    return render_template("index.html", response=response, session=session)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
