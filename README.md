# Automatic Risk Reporter

This application combines news sentiment analysis and armed conflict data to provide a comprehensive risk assessment platform for different countries and regions.

## Features

- **News Sentiment Analysis**: 
  - Search for news articles from the past 24 hours using the Serper API
  - Analyze sentiment of article titles using TextBlob
  - Calculate mean and standard deviation of sentiment scores
  - Summarize the most negative articles using Anthropic's Claude Sonnet 3.7

- **Armed Conflict Analysis**:
  - Retrieve and analyze data from the ACLED (Armed Conflict Location & Event Data) API
  - Track violent events and fatalities for monitored countries
  - Detect anomalies in conflict patterns using statistical analysis
  - Generate time-series charts of events and fatalities

- **Interactive Map Dashboard**:
  - Web-based interface with interactive map visualization
  - Color-coded risk indicators for monitored countries
  - Detailed view of news sentiment and conflict data by country
  - Historical data storage in SQLite database

## Monitored Countries

The application currently monitors the following countries/regions:
- Ukraine
- Moldova
- Syria
- Lebanon
- Israel
- Libya

## Requirements

- Python 3.7+
- API Keys:
  - Serper API (for news search)
  - Anthropic API (for article summarization)
  - ACLED API (for conflict data)

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your environment variables in a `.env` file:

```
SERPER_API_KEY=your_serper_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
ACLED_API_KEY=your_acled_api_key
ACLED_EMAIL=your_email_for_acled
```

## Usage

### Web Application

To run the web dashboard:

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Command-line Sentiment Analysis

For standalone news sentiment analysis:

```bash
python news_sentiment_analyzer.py "Country Name" --limit 10
```

Options:
- `--limit`: Number of negative articles to summarize (default: 10)
- `--serper-key`: Serper API key (overrides environment variable)
- `--anthropic-key`: Anthropic API key (overrides environment variable)

## Scheduled Analysis

The web application includes a scheduler that automatically runs analysis for all monitored countries once per day. You can also trigger analysis manually through the web interface.

## Data Storage

All analysis results are stored in an SQLite database (`sentiment_results.db`) with the following tables:
- `sentiment_results`: News sentiment analysis results
- `articles`: Individual news articles and their sentiment scores
- `acled_results`: Armed conflict event data and trends
- `acled_alerts`: Detected anomalies in conflict patterns
