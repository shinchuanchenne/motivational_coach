# Motivational Coach

Motivational Coach is a habit-building web app built with Flask, the GPT-4 API, and PostgreSQL. It supports two contrasting AI coaching styles: a “Good Cop” that encourages users with a supportive tone, and a “Bad Cop” that pushes users with a stricter tone. Users can set personal goals, track daily check-ins, and chat with the AI coaches to stay motivated.

## Overview

Motivational Coach is a Flask-based web application designed to help users build habits and stay motivated through AI-powered coaching. The app combines goal setting, daily check-ins, and conversational support in a simple web interface.

A key feature of the project is its use of two contrasting coaching styles: a “Good Cop” that motivates users with encouragement and positive reinforcement, and a “Bad Cop” that pushes users with a stricter and more demanding tone. By interacting with these two coaching personas, users can receive different types of motivational support while working towards their personal goals.

The project was built to explore how different motivational tones can shape user experience in a habit-building system, while also providing hands-on experience in full-stack web development with Flask, database integration, and LLM API usage.

## Features

- User sign up, login, and logout
- Goal setting for personalised habit-building support
- Two contrasting AI coaching styles:
  - **Good Cop** for encouragement and positive reinforcement
  - **Bad Cop** for stricter, pressure-based motivation
- Daily check-in system to track consistency
- AI-generated daily action plans based on user goals
- Chat-based interaction with AI coaches
- Conversation history tracking
- Password reset flow
- Language switching support

## User Flow

1. **Sign up**  
   Create an account with email, password, and name.

2. **Set goals**  
   Define personal goals for the motivational coaching experience.

3. **Log in**  
   Access the main dashboard after authentication.

4. **Track daily progress**  
   Complete daily check-ins to maintain consistency.

5. **Receive AI coaching**  
   Interact with two AI coaching styles:
   - **Good Cop** for supportive encouragement
   - **Bad Cop** for stricter motivation

6. **Generate daily plans**  
   Get AI-generated action plans based on your goals and current progress.

7. **Review conversation history**  
   Continue your habit-building journey with stored chat records and ongoing coaching support.

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite (development), PostgreSQL (Railway deployment)
- **AI Integration:** OpenAI API
- **Authentication:** Session-based authentication
- **Deployment:** Previously deployed on Railway
- **Other Tools:** Gunicorn, python-dotenv, Werkzeug

## Project Structure

```
motivational_coach/
├── app.py                   # Main Flask application and routes
├── init_db.py               # Database initialisation script
├── reminder.py              # Reminder-related logic
├── database.db              # Local SQLite database used during development
├── requirements.txt         # Project dependencies
├── static/                  # CSS and JavaScript files
│   ├── login_style.css
│   ├── script.js
│   └── style.css
├── templates/               # HTML templates for the web interface
│   ├── forgot_password.html
│   ├── goal_setting.html
│   ├── how_to_use.html
│   ├── index.html
│   ├── login.html
│   ├── reset_email_sent.html
│   ├── reset_password.html
│   ├── show_reset_link.html
│   └── signup.html
└── README.md
```

## How the AI Coaching Works

The app uses the OpenAI API to generate motivational responses and daily action plans based on the user’s goals and input.

Each coaching style is defined through a different prompt design:

- **Good Cop** uses an encouraging and supportive tone, focusing on positive reinforcement and motivation.
- **Bad Cop** uses a stricter and more demanding tone, pushing the user through pressure and accountability.

When a user interacts with the system, their input is combined with the selected coaching style and sent to the language model. The generated response is then shown in the web interface and stored as part of the conversation history.

This design allows the app to provide two contrasting motivational experiences while helping users stay engaged with their goals and daily habits.
