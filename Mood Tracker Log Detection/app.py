# -*- coding: utf-8 -*-
"""
A simple mood tracking web application built with Flask.
"""
import os
import calendar
import datetime
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

# ==============================================================================
# App & Database Configuration
# ==============================================================================

app = Flask(__name__)

# Set up the database path
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(instance_path, 'mood_logs.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==============================================================================
# Database Model
# ==============================================================================

class MoodLog(db.Model):
    """Represents a single mood log entry in the database."""
    id = db.Column(db.Integer, primary_key=True)
    emotion = db.Column(db.String(50), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    tags = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    log_date = db.Column(db.Date, nullable=False, default=datetime.date.today)

    def __repr__(self):
        return f'<MoodLog {self.log_date.strftime("%Y-%m-%d")} - {self.emotion}>'

# ==============================================================================
# Hooks & Helpers
# ==============================================================================

@app.after_request
def add_no_cache_header(response):
    """
    Add headers to prevent caching, ensuring users always see the latest version.
    """
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ==============================================================================
# Routes
# ==============================================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles the home page, which includes the mood logging form and a summary.
    """
    if request.method == 'POST':
        try:
            emotion_data = request.form['emotion'].split('|')
            emotion = emotion_data[0]
            emoji = emotion_data[1]
            tags = request.form.get('tags')
            notes = request.form.get('notes')
            today = datetime.date.today()

            # Check if a log for today already exists
            existing_log = MoodLog.query.filter_by(log_date=today).first()

            if existing_log:
                # Update the existing log
                existing_log.emotion = emotion
                existing_log.emoji = emoji
                existing_log.tags = tags
                existing_log.notes = notes
            else:
                # Create a new log
                new_log = MoodLog(
                    emotion=emotion, 
                    emoji=emoji, 
                    tags=tags, 
                    notes=notes,
                    log_date=today
                )
                db.session.add(new_log)
            
            db.session.commit()
            return redirect(url_for('index'))
        except (IndexError, KeyError):
            # Handle cases where form data is incomplete
            return "Error: Incomplete form submission.", 400

    # Calculate most frequent mood for the current month
    today = datetime.date.today()
    start_of_month = today.replace(day=1)
    monthly_logs = MoodLog.query.filter(MoodLog.log_date >= start_of_month).all()
    
    most_common_mood = None
    if monthly_logs:
        emotion_counts = Counter(log.emotion for log in monthly_logs)
        most_common_mood = emotion_counts.most_common(1)[0][0]

    return render_template('index.html', most_common_mood=most_common_mood)

@app.route('/api/mood-data')
def mood_data():
    """Provides data for the mood frequency chart."""
    today = datetime.date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    start_of_month = datetime.date(year, month, 1)
    _, num_days = calendar.monthrange(year, month)
    end_of_month = datetime.date(year, month, num_days)

    logs = MoodLog.query.filter(
        MoodLog.log_date.between(start_of_month, end_of_month)
    ).all()
    
    emotion_counts = Counter(log.emotion for log in logs)
    
    # Sort by a predefined order or by frequency
    sorted_emotions = sorted(emotion_counts.keys())
    
    labels = sorted_emotions
    data = [emotion_counts[emotion] for emotion in sorted_emotions]
    
    return jsonify(labels=labels, data=data)

@app.route('/api/monthly-trend')
def monthly_trend():
    """Provides data for the day-wise monthly mood trend chart."""
    today = datetime.date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    start_of_month = datetime.date(year, month, 1)
    _, num_days = calendar.monthrange(year, month)
    end_of_month = datetime.date(year, month, num_days)
    
    monthly_logs = MoodLog.query.filter(
        MoodLog.log_date.between(start_of_month, end_of_month)
    ).order_by(MoodLog.log_date).all()

    if not monthly_logs:
        return jsonify(data_available=False)

    # Simple sentiment mapping
    sentiment_map = {
        'Happy': 2, 'Excited': 3, 'Love': 3, 'Nice': 1,
        'Sad': -2, 'Bad': -1, 'Angry': -3
    }
    
    # Group logs by day and average the sentiment
    daily_sentiment = {}
    for log in monthly_logs:
        day = log.log_date.day
        sentiment = sentiment_map.get(log.emotion, 0)
        if day not in daily_sentiment:
            daily_sentiment[day] = []
        daily_sentiment[day].append(sentiment)

    # Prepare chart data
    labels = [str(d) for d in range(1, num_days + 1)]
    data = []
    for day in range(1, num_days + 1):
        if day in daily_sentiment:
            avg_sentiment = sum(daily_sentiment[day]) / len(daily_sentiment[day])
            data.append(round(avg_sentiment, 2))
        else:
            data.append(None) # Use null for days with no data

    return jsonify(data_available=True, labels=labels, data=data)

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    """Handles chatbot requests for monthly reports."""
    data = request.get_json()
    message = data.get('message', '').lower()
    reply = "I'm sorry, I couldn't process that. Please ask for a report like 'report for January 2023', 'mood on 2023-07-20', or 'recent mood'."

    try:
        # Report for a specific month
        if 'report for' in message:
            parts = message.split()
            month_name = None
            year = datetime.date.today().year

            for i, part in enumerate(parts):
                if part.isdigit() and len(part) == 4:
                    year = int(part)
                else:
                    try:
                        month_num = list(calendar.month_name).index(part.capitalize())
                        month_name = part.capitalize()
                    except ValueError:
                        continue
            
            if month_name:
                month = list(calendar.month_name).index(month_name)
                start_of_month = datetime.date(year, month, 1)
                _, num_days = calendar.monthrange(year, month)
                end_of_month = datetime.date(year, month, num_days)
                
                monthly_logs = MoodLog.query.filter(
                    MoodLog.log_date.between(start_of_month, end_of_month)
                ).all()

                if not monthly_logs:
                    reply = f"No mood data found for {month_name} {year}."
                else:
                    emotion_counts = Counter(log.emotion for log in monthly_logs)
                    most_common = emotion_counts.most_common(1)[0][0]
                    total_entries = len(monthly_logs)
                    
                    reply = (f"Here's your report for {month_name} {year}:\n"
                             f"- You logged your mood {total_entries} times.\n"
                             f"- Your most frequent mood was: {most_common}.\n"
                             f"- Moods you felt: {', '.join(emotion_counts.keys())}.")
            else:
                reply = "Please specify a month for the report (e.g., 'report for July 2023')."

        # Mood for a specific date
        elif 'mood on' in message:
            date_str = message.split('mood on')[-1].strip()
            try:
                log_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                log = MoodLog.query.filter_by(log_date=log_date).first()
                if log:
                    reply = f"On {log_date.strftime('%B %d, %Y')}, you felt {log.emotion}."
                    if log.notes:
                        reply += f" You also wrote: '{log.notes}'."
                else:
                    reply = f"I couldn't find any mood log for {date_str}."
            except ValueError:
                reply = "Please use the format YYYY-MM-DD for the date (e.g., 'mood on 2023-07-25')."

        # Recent mood (last 7 days)
        elif 'recent mood' in message:
            today = datetime.date.today()
            seven_days_ago = today - datetime.timedelta(days=7)
            recent_logs = MoodLog.query.filter(
                MoodLog.log_date.between(seven_days_ago, today)
            ).all()

            if not recent_logs:
                reply = "You haven't logged any moods in the last 7 days."
            else:
                emotion_counts = Counter(log.emotion for log in recent_logs)
                most_common = emotion_counts.most_common(1)[0][0]
                reply = f"Over the last 7 days, your most common mood has been {most_common}."

        # Show monthly trend chart
        elif 'trend' in message or 'graph' in message:
            reply = "Of course, here is the monthly trend graph."
            return jsonify({'reply': reply, 'action': 'show_chart', 'chart_id': 'monthlyTrendChart'})

    except Exception as e:
        # Log the error for debugging if needed
        print(f"Chatbot error: {e}")
        reply = "I seem to be having a little trouble. Please try again."

    return jsonify({'reply': reply})

@app.route('/report')
def report():
    """
    Displays the report page with a calendar view of monthly mood data.
    """
    today = datetime.date.today()
    try:
        year = request.args.get('year', today.year, type=int)
        month = request.args.get('month', today.month, type=int)
        # Ensure month is valid
        if not 1 <= month <= 12:
            month = today.month
    except (ValueError, TypeError):
        year = today.year
        month = today.month

    # Get all logs for the selected month
    start_of_month = datetime.date(year, month, 1)
    _, num_days = calendar.monthrange(year, month)
    end_of_month = datetime.date(year, month, num_days)
    
    monthly_logs = MoodLog.query.filter(
        MoodLog.log_date.between(start_of_month, end_of_month)
    ).all()

    # Group logs by day for quick lookup
    logs_by_day = {}
    for log in monthly_logs:
        day = log.log_date.day
        if day not in logs_by_day:
            logs_by_day[day] = []
        logs_by_day[day].append({
            'emotion': log.emotion,
            'emoji': log.emoji,
            'tags': log.tags,
            'notes': log.notes
        })

    # Calculate most frequent mood for the selected month
    most_common_mood = None
    if monthly_logs:
        emotion_counts = Counter(log.emotion for log in monthly_logs)
        most_common_mood = emotion_counts.most_common(1)[0][0]

    # Prepare data for the calendar grid
    cal = calendar.Calendar()
    month_days = cal.monthdayscalendar(year, month)

    return render_template(
        'report.html',
        year=year,
        month=month,
        month_name=start_of_month.strftime('%B'),
        most_common_mood=most_common_mood,
        month_days=month_days,
        logs_by_day=logs_by_day
    )

# ==============================================================================
# Main Execution
# ==============================================================================

if __name__ == '__main__':
    # The 'debug=True' argument enables the reloader, which is crucial for development
    app.run(debug=True, host='0.0.0.0', port=5000)
