import sqlite3

#Step 1: Build SQLite connection
connection = sqlite3.connect('database.db')
cursor = connection.cursor()

#Step 2: Create users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT,
               email TEXT UNIQUE,
               password TEXT
               )
               ''')

#Step 3: Create goals table
cursor.execute('''
CREATE TABLE IF NOT EXISTS goals (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id INTEGER,
               text TEXT,
               tone TEXT,
               FOREIGN KEY(user_id) REFERENCES users(id)
                )
               ''')

#Step 4: Create checkins table
cursor.execute('''
CREATE TABLE IF NOT EXISTS checkins (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id INTEGER,
               goal_id INTEGER,
               date DATE,
               completed BOOLEAN,
               timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
               FOREIGN KEY(user_id) REFERENCES users(id),
               FOREIGN KEY(goal_id) REFERENCES goals(id))
               ''')

#Step 5: Create conversations table
cursor.execute('''
CREATE TABLE IF NOT EXISTS conversations (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id INTEGER,
               goal_id INTEGER,
               role TEXT, -- "user" or "gpt"
               message TEXT,
               timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
               FOREIGN KEY(user_id) REFERENCES users(id),
               FOREIGN KEY(goal_id) REFERENCES goals(id)
               )
               ''')

connection.commit()
connection.close()
print("initialise database finished!")