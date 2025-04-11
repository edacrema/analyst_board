import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import io
from PIL import Image

# Define your API key and email
api_key = "QxsB6qMMiqaPPoSrDdEp"
email = "eugenio.dacrema@wfp.org"

# Define the base URL for the API
base_url = "https://api.acleddata.com/acled/read"


# Function to retrieve and process data from the ACLED API
def get_acled_data(country_name):
    # Calculate the date one year ago from today
    one_year_ago = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')

    # Define the query parameters
    params = {
        "key": api_key,
        "email": email,
        "country": country_name,
        "event_type": "Protests",  # Filter for only protests
        "event_date_where": "BETWEEN",
        "event_date": f"{one_year_ago}|{datetime.datetime.now().strftime('%Y-%m-%d')}",
        "limit": 0  # Set to 0 to return all relevant data
    }

    # Make the GET request to the API
    response = requests.get(base_url, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        response_data = response.json()
        print(f"Response for {country_name}:")
        print(response_data)  # Print the entire response for debugging

        if 'data' in response_data:
            data = response_data['data']
            df = pd.DataFrame(data)

            if df.empty:
                return df

            # Convert the event_date column to datetime format
            df['event_date'] = pd.to_datetime(df['event_date'])

            # Extract the month and year from the event_date column
            df['Month'] = df['event_date'].dt.to_period('M')

            # Convert fatalities to numeric type
            df['fatalities'] = pd.to_numeric(df['fatalities'], errors='coerce')

            # Group by the month and calculate the total occurrences and fatalities
            monthly_data = df.groupby('Month').agg(
                Occurrences=('event_date', 'count'),
                Fatalities=('fatalities', 'sum')
            ).reset_index()

            # Convert the Month back to datetime format for plotting
            monthly_data['DateTime'] = monthly_data['Month'].dt.to_timestamp()

            return monthly_data
        else:
            print(f"No 'data' found for {country_name}. Response content: {response_data}")
            return pd.DataFrame()

    else:
        print(f"Failed to retrieve data for {country_name}. Status code: {response.status_code}")
        print(response.text)  # Print the error message from the response
        return pd.DataFrame()


# Function to detect anomalies in monthly occurrences and fatalities
def detect_anomalies(df, threshold=2):
    if df.empty:
        return df  # Return immediately if the DataFrame is empty

    # Calculate moving average and moving standard deviation
    window_size = 10
    df['Occ_Moving_Avg'] = df['Occurrences'].rolling(window=window_size).mean()
    df['Occ_Moving_Std'] = df['Occurrences'].rolling(window=window_size).std()
    df['Fat_Moving_Avg'] = df['Fatalities'].rolling(window=window_size).mean()
    df['Fat_Moving_Std'] = df['Fatalities'].rolling(window=window_size).std()

    # Define the threshold for anomaly detection
    df['Occ_Anomaly'] = (abs(df['Occurrences'] - df['Occ_Moving_Avg']) > threshold * df['Occ_Moving_Std'])
    df['Fat_Anomaly'] = (abs(df['Fatalities'] - df['Fat_Moving_Avg']) > threshold * df['Fat_Moving_Std'])

    return df

# Function to perform anomaly detection and visualize results for each country
def protest_anomaly_detection_fun(country_list):
    all_graphs = []
    threshold = 2
    for country in country_list:
        # Fetch the data from ACLED API for the individual country
        df = get_acled_data(country)

        if df.empty:
            continue  # Skip if the DataFrame is empty

        # Detect anomalies in the data
        df = detect_anomalies(df)

        # Check for anomalies in the last three months
        if df.tail(3)['Occ_Anomaly'].any() or df.tail(3)['Fat_Anomaly'].any():
            fig, ax = plt.subplots(figsize=(14, 7))

            # Plot occurrences
            ax.plot(df['DateTime'], df['Occurrences'], label='Occurrences', color='blue')
            ax.plot(df['DateTime'], df['Occ_Moving_Avg'], label='Occ. Moving Average (10 months)', color='orange')
            ax.fill_between(df['DateTime'], df['Occ_Moving_Avg'] - threshold * df['Occ_Moving_Std'],
                            df['Occ_Moving_Avg'] + threshold * df['Occ_Moving_Std'], color='gray', alpha=0.2,
                            label='Occ. Confidence Interval')
            ax.scatter(df[df['Occ_Anomaly']]['DateTime'], df[df['Occ_Anomaly']]['Occurrences'], color='red', label='Occ. Anomalies')

            # Plot fatalities on the same axis
            ax.plot(df['DateTime'], df['Fatalities'], label='Fatalities', color='green')
            ax.plot(df['DateTime'], df['Fat_Moving_Avg'], label='Fat. Moving Average (10 months)', color='purple')
            ax.fill_between(df['DateTime'], df['Fat_Moving_Avg'] - threshold * df['Fat_Moving_Std'],
                            df['Fat_Moving_Avg'] + threshold * df['Fat_Moving_Std'], color='gray', alpha=0.2,
                            label='Fat. Confidence Interval')
            ax.scatter(df[df['Fat_Anomaly']]['DateTime'], df[df['Fat_Anomaly']]['Fatalities'], color='orange', label='Fat. Anomalies')

            ax.legend()
            ax.set_title(f'Occurrences and Fatalities with Anomaly Detection ({country})')
            ax.set_xlabel('Date')
            ax.set_ylabel('Count')

            # Save the figure to a bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            img = Image.open(buf)
            all_graphs.append(img)
            plt.close(fig)

    return all_graphs




