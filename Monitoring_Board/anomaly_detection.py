import pandas as pd
import tradingeconomics as te
import matplotlib.pyplot as plt


def get_inflation_series(country_name, indicator):
    api_key = 'e8ff2bc4c8144a3:brx99twm1bw887s'
    te.login(api_key)

    # Fetching data
    data = te.getHistoricalData(country=country_name, indicator=indicator, initDate='2020-01-01')
    # Converting to a DataFrame and dropping unnecessary columns
    df = pd.DataFrame(data)
    columns_to_drop = ['Country', 'Category', 'Frequency', 'HistoricalDataSymbol', 'LastUpdate']
    df = df.drop(columns=columns_to_drop, errors='ignore')

    # Checking if 'DateTime' column exists
    if 'DateTime' not in df.columns:
        print(f"Data for {country_name} does not have 'DateTime' column. Available columns: {df.columns}")
        return pd.DataFrame()  # Return an empty DataFrame if 'DateTime' is missing

    # Converting DateTime to datetime format and sorting by date
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    df = df.sort_values(by='DateTime').reset_index(drop=True)

    return df


def detect_anomalies(country_name, indicator, threshold=2):
    # Fetching the data
    df = get_inflation_series(country_name, indicator)

    if df.empty:
        return df  # Return immediately if the DataFrame is empty

    # Calculate moving average and moving standard deviation
    window_size = 10
    df['Moving_Avg'] = df['Value'].rolling(window=window_size).mean()
    df['Moving_Std'] = df['Value'].rolling(window=window_size).std()

    # Define the threshold for anomaly detection
    df['Anomaly'] = (abs(df['Value'] - df['Moving_Avg']) > threshold * df['Moving_Std'])

    return df


import matplotlib.pyplot as plt
import pandas as pd

import io
from PIL import Image


def anomaly_detection_fun(indicator, threshold=2):
    flagged_graphs = []
    countries = [
        "Afghanistan", "Bangladesh", "Bhutan", "Cambodia", "Fiji", "India", "Indonesia", "Kyrgyzstan", "Laos",
        "Myanmar", "Nepal", "Pakistan", "Philippines", "Sri Lanka", "Tajikistan",
        "Burundi", "Djibouti", "Ethiopia", "Kenya", "Rwanda", "Somalia", "South Sudan",
        "Uganda", "Algeria", "Armenia", "Egypt", "Iran", "Iraq",
        "Jordan", "Lebanon", "Libya", "Moldova", "Turkey",
        "Tunisia", "Ukraine"
    ]
    for country in countries:
        df = detect_anomalies(country, indicator, threshold)

        if df.empty:
            continue  # Skip if the DataFrame is empty

        # Check for anomalies in the last three months
        if df.tail(3)['Anomaly'].any():
            fig, ax = plt.subplots(figsize=(14, 7))
            ax.plot(df['DateTime'], df['Value'], label=f'{indicator}')
            ax.plot(df['DateTime'], df['Moving_Avg'], label='Moving Average (10 months)', color='orange')
            ax.fill_between(df['DateTime'], df['Moving_Avg'] - threshold * df['Moving_Std'],
                            df['Moving_Avg'] + threshold * df['Moving_Std'], color='gray', alpha=0.2,
                            label='Confidence Interval')
            ax.scatter(df[df['Anomaly']]['DateTime'], df[df['Anomaly']]['Value'], color='red', label='Anomalies')
            ax.legend()
            ax.set_title(f'{indicator} with Moving Average and Anomaly Detection ({country})')
            ax.set_xlabel('Date')
            ax.set_ylabel('Value')

            # Save the figure to a bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            img = Image.open(buf)
            flagged_graphs.append(img)
            plt.close(fig)

    return flagged_graphs





