import psycopg2
from psycopg2.extras import RealDictCursor
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

def init_db():
    try:
        #Step 1: Build connection
        load_dotenv()
        url = urlparse(os.getenv("DATABASE_URL"))

        connection = psycopg2.connect(
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        #Step 2: Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT,
                email TEXT UNIQUE,
                password TEXT,
                language TEXT DEFAULT 'en'
            );
        """)

        #Step 3: Create goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                goal_text TEXT,
                tone TEXT
            );
        """)


        #Step 4: Create checkins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkins (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                goal_id INTEGER REFERENCES goals(id),
                date DATE,
                completed BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        #Step 5: Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                goal_id INTEGER REFERENCES goals(id),
                role TEXT, -- "user" or "gpt"
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        connection.commit()
        connection.close()
        print("PostgreSQL database initialised!")
    
    except Exception as e:
        print("Failed to initialise DB:", e)
    finally:
        if 'connection' in locals():
            connection.close()
