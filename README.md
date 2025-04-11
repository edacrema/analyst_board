# Analyst Board

A comprehensive monitoring and analysis dashboard for global economic trends and events using news sentiment analysis, anomaly detection, and data visualization.

## Overview

Analyst Board is a versatile tool designed to track and analyze economic trends across multiple countries and regions. It leverages natural language processing techniques to assess news sentiment, detect anomalies in economic indicators, and provide valuable insights for analysts, researchers, and policymakers.

## Features

- **News Sentiment Analysis**: Analyzes economic news across 35+ countries and identifies negative sentiment trends
- **Country-Specific News Retrieval**: Retrieves and displays recent economic news for any specified country
- **Anomaly Detection**: Identifies unusual patterns in economic indicators
- **Protest Anomaly Detection**: Specifically monitors and analyzes protest activities across different regions
- **Interactive Dashboard**: User-friendly Gradio interface with visualization capabilities
- **Regional Monitoring**: Pre-configured country groupings for regional analysis:
  - RBB (Asia/Pacific): Afghanistan, Bangladesh, Bhutan, Cambodia, etc.
  - RBN (East Africa): Burundi, Djibouti, Ethiopia, Kenya, etc.
  - RBC (Middle East/Eurasia): Algeria, Armenia, Egypt, Iran, Iraq, etc.

## Installation

1. Clone this repository:
```bash
git clone https://github.com/edacrema/analyst_board.git
cd analyst_board
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Main Application

Run the main application:
```bash
python app.py
```

This will launch the Gradio interface where you can:
- Run sentiment analysis across all monitored countries
- View country-specific economic news
- Access the anomaly detection features

### Monitoring Board

For more advanced monitoring and analysis:
```bash
cd Monitoring_Board
python app.py
```

The Monitoring Board provides additional features including:
- Regional protest anomaly detection
- Economic indicator anomaly detection
- More comprehensive visualization options

## Project Structure

- `app.py`: Main application entry point with Gradio interface
- `sentiment_analysis.py`: Core sentiment analysis functionality
- `news_retrieval.py`: News retrieval and processing utilities
- `requirements.txt`: Project dependencies
- `Monitoring_Board/`: Advanced monitoring and analysis tools
  - `anomaly_detection.py`: Economic indicator anomaly detection
  - `protest_anomaly_detection.py`: Protest activity analysis
  - `app.py`: Enhanced dashboard with additional features

## API Requirements

This project uses the following external APIs:
- **Serper API**: For news retrieval (API key required)

## Dependencies

- gradio
- matplotlib
- requests
- vaderSentiment

## License

[MIT License](LICENSE)
