#!/usr/bin/env python3
"""
News Sentiment Map Application

This web application displays sentiment analysis results for multiple countries on an interactive map.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_apscheduler import APScheduler
import news_sentiment_analyzer as nsa
import acled_analyzer as acled
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environment

# Initialize Flask app
app = Flask(__name__)
scheduler = APScheduler()
scheduler.init_app(app)

# Configuration
class Config:
    SCHEDULER_API_ENABLED = True
    COUNTRIES = [
        "Ukraine",
        "Moldova", 
        "Syria", 
        "Lebanon", 
        "Israel", 
        "Libya"
    ]
    # Country coordinates for map markers (approximate center points)
    COUNTRY_COORDINATES = {
        "Ukraine": [49.0, 31.0],
        "Moldova": [47.4, 28.5],
        "Syria": [35.0, 38.0],
        "Lebanon": [33.8, 35.8],
        "Israel": [31.5, 34.8],
        "Libya": [27.0, 17.0]
    }
    DB_PATH = "sentiment_results.db"

app.config.from_object(Config)

# Database setup
def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(app.config['DB_PATH'])
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sentiment_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        mean_score REAL NOT NULL,
        std_dev REAL NOT NULL,
        most_negative_title TEXT NOT NULL,
        most_negative_score REAL NOT NULL,
        most_positive_title TEXT NOT NULL,
        most_positive_score REAL NOT NULL,
        summary TEXT,
        article_count INTEGER
    )
    ''')
    
    # Check if articles table exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        snippet TEXT,
        link TEXT,
        sentiment_score REAL NOT NULL,
        FOREIGN KEY (result_id) REFERENCES sentiment_results (id)
    )
    ''')
    
    # Create ACLED results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS acled_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        has_anomalies BOOLEAN NOT NULL,
        total_events INTEGER NOT NULL,
        total_fatalities INTEGER NOT NULL,
        events_trend_pct INTEGER,
        fatalities_trend_pct INTEGER,
        chart_path TEXT,
        weekly_events INTEGER,
        weekly_fatalities INTEGER
    )
    ''')
    
    # Add table for ACLED alerts
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS acled_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        alert_text TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Routes
@app.route('/')
def index():
    """Render the main page with the map."""
    return render_template('index.html', countries=app.config['COUNTRIES'],
                           country_coordinates=app.config['COUNTRY_COORDINATES'])

@app.route('/api/results/<country>')
def get_country_results(country):
    """Get the most recent sentiment analysis results for a country."""
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    
    # Get the most recent analysis for the country
    cursor = conn.execute('''
    SELECT id, timestamp, country, mean_score, std_dev, 
           most_negative_title, most_negative_score,
           most_positive_title, most_positive_score, 
           summary
    FROM sentiment_results 
    WHERE country = ? 
    ORDER BY timestamp DESC LIMIT 1
    ''', (country,))
    
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return jsonify({"error": f"No results found for {country}"}), 404
    
    # Convert to dictionary
    result_dict = dict(result)
    
    # Get articles for this result
    cursor = conn.execute('''
    SELECT title, snippet, link, sentiment_score
    FROM articles
    WHERE result_id = ?
    ORDER BY sentiment_score ASC
    ''', (result_dict["id"],))
    
    articles = []
    for row in cursor:
        articles.append({
            "title": row["title"],
            "snippet": row["snippet"],
            "link": row["link"],
            "sentiment_score": row["sentiment_score"]
        })
    
    result_dict["articles"] = articles
    
    # Get ACLED data for this country
    acled_data = acled.run_analysis_for_country(country)
    result_dict["acled"] = acled_data
    
    conn.close()
    
    # Return the combined results
    return jsonify({
        "country": result_dict["country"],
        "timestamp": result_dict["timestamp"],
        "mean_score": result_dict["mean_score"],
        "std_dev": result_dict["std_dev"],
        "most_negative_title": result_dict["most_negative_title"],
        "most_negative_score": result_dict["most_negative_score"],
        "most_positive_title": result_dict["most_positive_title"],
        "most_positive_score": result_dict["most_positive_score"],
        "summary": result_dict["summary"],
        "articles": result_dict["articles"],
        "acled": result_dict["acled"]
    })

@app.route('/api/results')
def get_all_results():
    """Get the latest sentiment analysis results for all countries."""
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    results = {}
    
    for country in app.config['COUNTRIES']:
        # Get the latest result for each country
        cursor.execute('''
        SELECT * FROM sentiment_results 
        WHERE country = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
        ''', (country,))
        
        result = cursor.fetchone()
        
        if result:
            results[country] = {
                'mean_score': result['mean_score'],
                'timestamp': result['timestamp']
            }
    
    conn.close()
    return jsonify(results)

@app.route('/api/coordinates')
def get_country_coordinates():
    """Return the country coordinates as a JSON object"""
    return jsonify(app.config['COUNTRY_COORDINATES'])

# Scheduled tasks
def analyze_country(country):
    """Run sentiment analysis for a specific country and store results in the database."""
    print(f"Starting analysis for {country}...")
    
    # Create a namespace object for arguments
    class Args:
        query = country
        limit = 10
        serper_key = None
        openai_key = None
    
    args = Args()
    
    # Get API keys
    serper_key = os.environ.get("SERPER_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    # Search for news
    articles = nsa.search_news(args.query, serper_key)
    
    if not articles:
        print(f"No news articles found for {country}.")
        return
    
    # Extract titles for sentiment analysis
    titles = [article.get("title", "") for article in articles if article.get("title")]
    
    # Analyze sentiment
    sentiment_scores = nsa.analyze_sentiment(titles)
    
    # Calculate statistics
    mean_score, std_dev = nsa.calculate_statistics(sentiment_scores)
    
    # Combine articles with their sentiment scores
    articles_with_scores = list(zip(articles, sentiment_scores))
    
    # Sort articles by sentiment score (most negative first)
    sorted_articles = sorted(articles_with_scores, key=lambda x: x[1])
    
    # Get the most negative and most positive articles
    most_negative = sorted_articles[0]
    most_positive = sorted_articles[-1]
    
    # Prepare for display
    min_score = most_negative[1]
    most_negative_title = most_negative[0].get('title', 'No title')
    
    max_score = most_positive[1]
    most_positive_title = most_positive[0].get('title', 'No title')
    
    # Get all articles for the combined summary (both negative and positive)
    all_articles_with_sentiment = []
    for article, score in sorted_articles:
        article_copy = article.copy()
        article_copy["sentiment_score"] = score
        all_articles_with_sentiment.append(article_copy)
    
    # Create a combined summary with both negative and positive news
    summary = nsa.summarize_articles(all_articles_with_sentiment, openai_key)
    
    # Analyze ACLED violent events data
    acled_results = acled.run_analysis_for_country(country)
    
    # Store results in database
    conn = sqlite3.connect(app.config['DB_PATH'])
    cursor = conn.cursor()
    
    # Check if the article_count column exists
    cursor.execute("PRAGMA table_info(sentiment_results)")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Default query without article_count
    insert_query = '''
    INSERT INTO sentiment_results 
    (country, timestamp, mean_score, std_dev, most_negative_title, most_negative_score, 
     most_positive_title, most_positive_score, summary)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    params = [
        country, 
        datetime.now().isoformat(), 
        mean_score, 
        std_dev, 
        most_negative_title, 
        min_score, 
        most_positive_title, 
        max_score, 
        summary
    ]
    
    # If article_count column exists, include it
    if 'article_count' in columns:
        insert_query = '''
        INSERT INTO sentiment_results 
        (country, timestamp, mean_score, std_dev, most_negative_title, most_negative_score, 
         most_positive_title, most_positive_score, summary, article_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params.append(len(articles))
    
    cursor.execute(insert_query, params)
    
    result_id = cursor.lastrowid
    
    # Store individual articles
    for article, score in sorted_articles:
        cursor.execute('''
        INSERT INTO articles
        (result_id, title, snippet, link, sentiment_score)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            result_id,
            article.get('title', 'No title'),
            article.get('snippet', 'No snippet'),
            article.get('link', 'No link'),
            score
        ))
    
    # Store ACLED results if data is available
    if acled_results["has_data"]:
        # Generate and save chart if we have data
        if acled_results["has_data"]:
            # Save chart to static directory
            chart_path = None
            df = acled.get_acled_data(country)
            if not df.empty:
                df = acled.detect_anomalies(df)
                chart_path = acled.generate_event_chart(country, df)
        
        cursor.execute('''
        INSERT INTO acled_results
        (country, timestamp, has_anomalies, total_events, total_fatalities, events_trend_pct, fatalities_trend_pct, chart_path, weekly_events, weekly_fatalities)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            country,
            datetime.now().isoformat(),
            acled_results["has_anomalies"],
            acled_results["total_events"],
            acled_results["total_fatalities"],
            acled_results.get("events_trend_pct", 0),
            acled_results.get("fatalities_trend_pct", 0),
            chart_path,
            acled_results.get("weekly_events", 0),
            acled_results.get("weekly_fatalities", 0)
        ))
        
        # Store alerts if there are anomalies
        if acled_results["has_anomalies"]:
            # Get specific alerts data
            alerts = acled.get_latest_alerts([country])
            
            for alert_country in alerts.get("countries_with_alerts", []):
                if alert_country["country"] == country:
                    # Add alert for events if there's an anomaly
                    if alert_country["has_event_anomalies"]:
                        cursor.execute('''
                        INSERT INTO acled_alerts
                        (country, timestamp, alert_text)
                        VALUES (?, ?, ?)
                        ''', (
                            country,
                            datetime.now().isoformat(),
                            "Event anomaly detected"
                        ))
                    
                    # Add alert for fatalities if there's an anomaly
                    if alert_country["has_fatality_anomalies"]:
                        cursor.execute('''
                        INSERT INTO acled_alerts
                        (country, timestamp, alert_text)
                        VALUES (?, ?, ?)
                        ''', (
                            country,
                            datetime.now().isoformat(),
                            "Fatality anomaly detected"
                        ))
    
    conn.commit()
    conn.close()
    
    print(f"Analysis completed for {country}.")
    return True

@app.route('/api/analyze/<country>', methods=['POST'])
def trigger_analysis(country):
    """API endpoint to manually trigger analysis for a country."""
    if country not in app.config['COUNTRIES']:
        return jsonify({"error": "Invalid country"}), 400
    
    success = analyze_country(country)
    
    if success:
        return jsonify({"status": "success", "message": f"Analysis completed for {country}"})
    else:
        return jsonify({"status": "error", "message": "Analysis failed"}), 500

def run_scheduled_analysis():
    """Run sentiment analysis for all countries one by one."""
    print("Starting scheduled analysis...")
    
    for country in app.config['COUNTRIES']:
        analyze_country(country)
    
    print("Scheduled analysis completed.")

# Schedule the sentiment analysis to run daily
@scheduler.task('interval', id='analyze_all_countries', hours=24, misfire_grace_time=900)
def scheduled_task():
    run_scheduled_analysis()

# Schedule the analysis to run on startup (after a short delay)
@scheduler.task('date', id='analyze_on_startup', run_date=datetime.now() + timedelta(seconds=10))
def startup_task():
    run_scheduled_analysis()

# Start the scheduler when the app starts
scheduler.start()

# Add routes for ACLED data
@app.route('/api/acled/<country>')
def get_country_acled(country):
    """Get the latest ACLED violent events data for a specific country."""
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get the latest ACLED results for the country
    cursor.execute('''
    SELECT * FROM acled_results 
    WHERE country = ? 
    ORDER BY timestamp DESC 
    LIMIT 1
    ''', (country,))
    
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return jsonify({"error": "No ACLED data available for this country"}), 404
    
    # Get any associated alerts
    cursor.execute('''
    SELECT alert_text FROM acled_alerts 
    WHERE country = ? 
    ORDER BY timestamp DESC 
    LIMIT 10
    ''', (country,))
    
    alerts = cursor.fetchall()
    anomalies = [alert['alert_text'] for alert in alerts]
    
    # Convert result to dict and format as expected by frontend
    result_dict = {
        'country': result['country'],
        'timestamp': result['timestamp'],
        'has_data': True,
        'has_anomalies': bool(result['has_anomalies']),
        'total_events': result['total_events'],
        'total_fatalities': result['total_fatalities'],
        'events_trend_pct': result['events_trend_pct'],
        'fatalities_trend_pct': result['fatalities_trend_pct'],
        'chart_path': result['chart_path'],
        'anomalies': anomalies
    }
    
    # Safely add weekly data if columns exist
    try:
        result_dict['weekly_events'] = result['weekly_events']
        result_dict['weekly_fatalities'] = result['weekly_fatalities']
    except (IndexError, KeyError):
        # Fallback to calculating rough weekly average if weekly data not available
        weeks = 52  # Assuming data is for a year
        result_dict['weekly_events'] = int(result['total_events'] / weeks)
        result_dict['weekly_fatalities'] = int(result['total_fatalities'] / weeks)
    
    conn.close()
    return jsonify(result_dict)

@app.route('/api/acled')
def get_all_acled():
    try:
        conn = sqlite3.connect(app.config['DB_PATH'])
        cursor = conn.cursor()
        
        # Get the latest results from acled_results table
        cursor.execute('''
            SELECT country, total_events as event_count, total_fatalities as fatality_count, datetime(timestamp)
            FROM acled_results
            WHERE timestamp = (SELECT MAX(timestamp) FROM acled_results GROUP BY country)
        ''')
        results = cursor.fetchall()
        
        # Get anomalies from acled_alerts table
        cursor.execute('''
            SELECT country, alert_text as explanation
            FROM acled_alerts
            WHERE timestamp = (SELECT MAX(timestamp) FROM acled_alerts GROUP BY country)
        ''')
        anomalies = cursor.fetchall()
        
        # Create the response dictionary
        acled_data = {}
        
        # Process results
        for country, event_count, fatality_count, timestamp in results:
            acled_data[country] = {
                'event_count': event_count,
                'fatality_count': fatality_count,
                'timestamp': str(timestamp),
                'anomaly': False,  # Default to no anomaly
                'explanation': ''  # Default empty explanation
            }
        
        # Process anomalies
        for country, explanation in anomalies:
            if country in acled_data:
                acled_data[country]['anomaly'] = True
                acled_data[country]['explanation'] = explanation
        
        # Print final data for debugging
        print("ACLED data:", acled_data)
        
        conn.close()
        return jsonify(acled_data)
    except Exception as e:
        print(f"Error in get_all_acled: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)  # use_reloader=False is needed with APScheduler
