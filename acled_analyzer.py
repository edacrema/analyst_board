#!/usr/bin/env python3
"""
ACLED Event Analyzer

This module retrieves data from the ACLED (Armed Conflict Location & Event Data) API,
analyzes trends in violent events, and detects anomalies.
"""

import os
import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import io
from PIL import Image
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Get ACLED API credentials from environment variables
ACLED_API_KEY = os.environ.get("ACLED_API_KEY")
ACLED_EMAIL = os.environ.get("ACLED_EMAIL")

# Define the base URL for the API
BASE_URL = "https://api.acleddata.com/acled/read"

def get_acled_data(country_name: str, days: int = 365) -> pd.DataFrame:
    """
    Retrieve violent event data for a specified country from the ACLED API.
    
    Args:
        country_name: Name of the country to retrieve data for
        days: Number of days to look back (default: 365)
        
    Returns:
        DataFrame containing the processed ACLED data
    """
    if not ACLED_API_KEY or not ACLED_EMAIL:
        print("Error: ACLED API credentials not found in environment variables.")
        return pd.DataFrame()
    
    # Calculate the date X days ago from today
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Define the query parameters - focus on violent events
    params = {
        "key": ACLED_API_KEY,
        "email": ACLED_EMAIL,
        "country": country_name,
        "event_date_where": "BETWEEN",
        "event_date": f"{start_date}|{end_date}",
        # Include all violent event types (not just protests like in the example)
        "event_type": "Violence against civilians|Explosions/Remote violence|Battles",
        "limit": 0  # Return all matching records
    }
    
    try:
        # Make the API request
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        data = response.json()
        
        if 'data' in data and data['data']:
            df = pd.DataFrame(data['data'])
            
            # Process the DataFrame
            df['event_date'] = pd.to_datetime(df['event_date'])
            # Group by week instead of month
            df['Week'] = df['event_date'].dt.to_period('W')
            df['fatalities'] = pd.to_numeric(df['fatalities'], errors='coerce')
            
            # Group by week and calculate statistics
            weekly_data = df.groupby('Week').agg(
                Events=('event_date', 'count'),
                Fatalities=('fatalities', 'sum')
            ).reset_index()
            
            # Convert Week back to datetime for plotting
            weekly_data['DateTime'] = weekly_data['Week'].dt.to_timestamp()
            
            return weekly_data
        else:
            print(f"No data found for {country_name}")
            return pd.DataFrame()
    
    except requests.RequestException as e:
        print(f"Error retrieving ACLED data for {country_name}: {e}")
        return pd.DataFrame()

def detect_anomalies(df: pd.DataFrame, threshold: float = 2.0) -> pd.DataFrame:
    """
    Detect anomalies in event and fatality data based on moving averages.
    
    Args:
        df: DataFrame containing event data
        threshold: Number of standard deviations to consider as anomaly threshold
        
    Returns:
        DataFrame with added anomaly detection columns
    """
    if df.empty or len(df) < 3:
        return df
    
    # Use a 12-week moving average window for anomaly detection
    window_size = 12
    
    # Make sure we have enough data for the window size
    if len(df) < window_size:
        window_size = max(3, len(df) // 2)
    
    # Calculate moving averages and standard deviations
    df['Events_MA'] = df['Events'].rolling(window=window_size).mean()
    df['Events_MSTD'] = df['Events'].rolling(window=window_size).std()
    df['Fatalities_MA'] = df['Fatalities'].rolling(window=window_size).mean()
    df['Fatalities_MSTD'] = df['Fatalities'].rolling(window=window_size).std()
    
    # Define anomalies as data points that exceed mean + (threshold * std)
    df['Events_Anomaly'] = df['Events'] > (df['Events_MA'] + threshold * df['Events_MSTD'])
    df['Fatalities_Anomaly'] = df['Fatalities'] > (df['Fatalities_MA'] + threshold * df['Fatalities_MSTD'])
    
    return df

def generate_event_chart(country: str, df: pd.DataFrame, threshold: float = 2.0) -> Optional[str]:
    """
    Generate a chart showing events, fatalities, and anomalies over time.
    
    Args:
        country: Country name for chart title
        df: DataFrame with anomaly detection results
        threshold: Threshold used for anomaly detection
        
    Returns:
        Path to saved chart file (for web display) or None if generation failed
    """
    if df.empty:
        return None
    
    try:
        # Create a figure with two y-axes
        fig, ax1 = plt.subplots(figsize=(12, 6))
        ax2 = ax1.twinx()
        
        # Plot events (bars) on the left axis
        ax1.bar(df['DateTime'], df['Events'], alpha=0.5, color='blue', label='Events')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Event Count', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        
        # Plot fatalities (line) on the right axis
        ax2.plot(df['DateTime'], df['Fatalities'], color='red', label='Fatalities')
        ax2.set_ylabel('Fatalities', color='red')
        ax2.tick_params(axis='y', labelcolor='red')
        
        # Title and grid
        plt.title(f'Weekly Violent Events in {country}')
        ax1.grid(True, alpha=0.3)
        
        # Plot moving averages
        if 'Events_MA' in df.columns and not df['Events_MA'].isna().all():
            ax1.plot(df['DateTime'], df['Events_MA'], 'b--', alpha=0.7, label='Events 12-week MA')
        
        if 'Fatalities_MA' in df.columns and not df['Fatalities_MA'].isna().all():
            ax2.plot(df['DateTime'], df['Fatalities_MA'], 'r--', alpha=0.7, label='Fatalities 12-week MA')
        
        # Highlight anomalies if present
        event_anomalies = df[df['Events_Anomaly'] == True] if 'Events_Anomaly' in df.columns else pd.DataFrame()
        fatality_anomalies = df[df['Fatalities_Anomaly'] == True] if 'Fatalities_Anomaly' in df.columns else pd.DataFrame()
        
        if not event_anomalies.empty:
            ax1.scatter(event_anomalies['DateTime'], event_anomalies['Events'], 
                       color='purple', marker='^', s=100, label='Event Anomalies', zorder=5)
        
        if not fatality_anomalies.empty:
            ax2.scatter(fatality_anomalies['DateTime'], fatality_anomalies['Fatalities'], 
                       color='darkred', marker='*', s=150, label='Fatality Anomalies', zorder=5)
        
        # Create combined legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='best')
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        
        # Tight layout to prevent clipping of labels
        plt.tight_layout()
        
        # Create directory for output if it doesn't exist
        output_dir = os.path.join('static', 'charts')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the chart
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{country.lower().replace(' ', '_')}_acled_chart_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path, dpi=100)
        plt.close()
        
        return output_path
    
    except Exception as e:
        print(f"Error generating chart for {country}: {e}")
        return None

def get_latest_alerts(countries: List[str]) -> Dict[str, Any]:
    """
    Get the latest alerts for specified countries.
    
    Args:
        countries: List of country names to get alerts for
        
    Returns:
        Dictionary with countries that have alerts
    """
    result = {
        "timestamp": datetime.datetime.now().isoformat(),
        "countries_with_alerts": []
    }
    
    for country in countries:
        df = get_acled_data(country)
        
        if not df.empty and len(df) >= 3:
            # Get anomaly detection results
            df = detect_anomalies(df)
            
            # Check for anomalies in the most recent week
            latest_week = df.iloc[-1]
            has_event_anomaly = 'Events_Anomaly' in df.columns and latest_week.get('Events_Anomaly', False)
            has_fatality_anomaly = 'Fatalities_Anomaly' in df.columns and latest_week.get('Fatalities_Anomaly', False)
            
            if has_event_anomaly or has_fatality_anomaly:
                week_str = latest_week['DateTime'].strftime('%Y-Week %U')
                
                country_alert = {
                    "country": country,
                    "week": week_str,
                    "has_event_anomaly": bool(has_event_anomaly),
                    "has_fatality_anomaly": bool(has_fatality_anomaly),
                    "events_trend_pct": 0,
                    "fatalities_trend_pct": 0
                }
                
                # Add event statistics if there's an event anomaly
                if has_event_anomaly:
                    events_trend = ((latest_week['Events'] / latest_week['Events_MA']) - 1) * 100 if latest_week['Events_MA'] > 0 else 0
                    country_alert["events_trend_pct"] = int(round(events_trend))
                    country_alert["events_value"] = int(latest_week['Events'])
                    country_alert["events_expected"] = int(latest_week['Events_MA'])
                
                # Add fatality statistics if there's a fatality anomaly
                if has_fatality_anomaly:
                    fatalities_trend = ((latest_week['Fatalities'] / latest_week['Fatalities_MA']) - 1) * 100 if latest_week['Fatalities_MA'] > 0 else 0
                    country_alert["fatalities_trend_pct"] = int(round(fatalities_trend))
                    country_alert["fatalities_value"] = int(latest_week['Fatalities'])
                    country_alert["fatalities_expected"] = int(latest_week['Fatalities_MA'])
                
                result["countries_with_alerts"].append(country_alert)
    
    return result

def run_analysis_for_country(country: str) -> Dict[str, Any]:
    """
    Run a complete violence event analysis for a single country.
    
    Args:
        country: Country name to analyze
        
    Returns:
        Dictionary with analysis results
    """
    results = {
        "country": country,
        "timestamp": datetime.datetime.now().isoformat(),
        "has_data": False,
        "has_anomalies": False,
        "total_events": 0,
        "total_fatalities": 0,
        "chart_path": None,
        "anomalies": []
    }
    
    # Get the data
    df = get_acled_data(country)
    
    if df.empty:
        return results
    
    # Set has_data flag and overall counts
    results["has_data"] = True
    results["total_events"] = int(df['Events'].sum())
    results["total_fatalities"] = int(df['Fatalities'].sum())
    
    # Add latest weekly figures
    if not df.empty:
        latest_week = df.iloc[-1]
        results["weekly_events"] = int(latest_week['Events'])
        results["weekly_fatalities"] = int(latest_week['Fatalities'])
    
    # Detect anomalies
    df = detect_anomalies(df)
    
    # Check for recent anomalies (last 4 weeks)
    recent_df = df.tail(4)
    has_event_anomalies = 'Events_Anomaly' in recent_df.columns and recent_df['Events_Anomaly'].any()
    has_fatality_anomalies = 'Fatalities_Anomaly' in recent_df.columns and recent_df['Fatalities_Anomaly'].any()
    results["has_anomalies"] = bool(has_event_anomalies or has_fatality_anomalies)
    
    # Create list of anomaly descriptions for frontend display
    if results["has_anomalies"]:
        anomalies = []
        
        for _, row in recent_df[
            (recent_df.get('Events_Anomaly', pd.Series([False] * len(recent_df))) | 
             recent_df.get('Fatalities_Anomaly', pd.Series([False] * len(recent_df))))
        ].iterrows():
            week_str = row['DateTime'].strftime('Week %U, %Y')
            
            if 'Events_Anomaly' in recent_df.columns and row.get('Events_Anomaly', False):
                anomalies.append(f"Unusual spike in violent events in {week_str}: {int(row['Events'])} events (expected around {int(row['Events_MA'])})")
            
            if 'Fatalities_Anomaly' in recent_df.columns and row.get('Fatalities_Anomaly', False):
                anomalies.append(f"Unusual spike in fatalities in {week_str}: {int(row['Fatalities'])} deaths (expected around {int(row['Fatalities_MA'])})")
        
        results["anomalies"] = anomalies
    
    # Generate chart if data exists
    chart_path = generate_event_chart(country, df)
    if chart_path:
        results["has_chart"] = True
        results["chart_path"] = f"/{chart_path.replace('\\', '/')}"
        
    # Add trends information
    if len(df) >= 3:
        # Calculate trend by comparing most recent week with the moving average
        latest_week = df.iloc[-1]
        
        # Calculate events trend
        if 'Events_MA' in latest_week and latest_week['Events_MA'] > 0:
            events_trend = ((latest_week['Events'] / latest_week['Events_MA']) - 1) * 100
            results["events_trend_pct"] = int(round(events_trend))
        else:
            results["events_trend_pct"] = 0
            
        # Calculate fatalities trend
        if 'Fatalities_MA' in latest_week and latest_week['Fatalities_MA'] > 0:
            fatalities_trend = ((latest_week['Fatalities'] / latest_week['Fatalities_MA']) - 1) * 100
            results["fatalities_trend_pct"] = int(round(fatalities_trend))
        else:
            results["fatalities_trend_pct"] = 0
    else:
        # Not enough data for trend calculation
        results["events_trend_pct"] = 0
        results["fatalities_trend_pct"] = 0
    
    return results
