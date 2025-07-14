# init_db_pg.py
from db import db, app
import models

with app.app_context():
    db.create_all()
    print("PostgreSQL tables created.")
