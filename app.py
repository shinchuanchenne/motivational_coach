from flask import Flask, request, render_template, redirect, url_for, session, g
from openai import OpenAI
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
        password = request.form["password"]
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

        return redirect(url_for('login'))

    return render_template("signup.html")


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        email = request.form["email"].strip().lower()
        db = get_db()

        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            db.execute("INSERT INTO users (email) VALUES (?)", (email,))
            db.commit()
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        session['user_id'] = user['id']
        session['email'] = user['email']
        return redirect(url_for('index'))
    return render_template("login.html")


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
