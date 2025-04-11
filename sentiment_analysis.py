import requests
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt


def serp_news(query):
    url = "https://google.serper.dev/news"

    payload = json.dumps({
        "q": f"{query} economy",
        "num": 10,
        "tbs": "qdr:w2"
    })
    headers = {
        'X-API-KEY': '3b3c72db78c6fd3049c1fe4f384a0541747fd7f6',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        result = response.json()
        news = result.get('news', [])

        analyzer = SentimentIntensityAnalyzer()
        sentiments = []

        for article in news:
            title = article['title']
            sentiment = analyzer.polarity_scores(title)
            sentiments.append({
                "title": title,
                "source": article['source'],
                "date": article['date'],
                "url": article['link'],
                "sentiment": sentiment
            })

        # Calculate average sentiment
        if sentiments:
            avg_sentiment = {
                "neg": sum(d["sentiment"]["neg"] for d in sentiments) / len(sentiments),
                "neu": sum(d["sentiment"]["neu"] for d in sentiments) / len(sentiments),
                "pos": sum(d["sentiment"]["pos"] for d in sentiments) / len(sentiments),
                "compound": sum(d["sentiment"]["compound"] for d in sentiments) / len(sentiments)
            }
        else:
            avg_sentiment = {"neg": 0.0, "neu": 0.0, "pos": 0.0, "compound": 0.0}

        return {
            "query": query,
            "average_sentiment": avg_sentiment,
            "articles": sentiments
        }
    else:
        return None


def analyze_countries(countries):
    results = []
    for country in countries:
        result = serp_news(country)
        if result:
            results.append(result)
    return results


def filter_negative_sentiments(results):
    return [result for result in results if result['average_sentiment']['compound'] < 0]


def visualize_results(negative_results):
    countries = [result['query'] for result in negative_results]
    sentiments = [result['average_sentiment']['compound'] for result in negative_results]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(countries, sentiments, color='red')
    ax.set_xlabel('Average Compound Sentiment Score')
    ax.set_ylabel('Countries')
    ax.set_title('Countries with Negative Average Sentiment Scores')

    return fig


# List of countries
countries = [
    "Afghanistan", "Bangladesh", "Bhutan", "Cambodia", "Fiji", "India", "Indonesia", "Kyrgyzstan", "Laos",
    "Myanmar", "Nepal", "Pakistan", "Philippines", "Sri Lanka", "Tajikistan",
    "Burundi", "Djibouti", "Ethiopia", "Kenya", "Rwanda", "Somalia", "South Sudan",
    "Uganda", "Algeria", "Armenia", "Egypt", "Iran", "Iraq",
    "Jordan", "Lebanon", "Libya", "Moldova", "Turkey", "West Bank",
    "Tunisia", "Ukraine"
]

# Analyze countries
results = analyze_countries(countries)

# Filter negative sentiments
negative_results = filter_negative_sentiments(results)

# Visualize results
visualize_results(negative_results)