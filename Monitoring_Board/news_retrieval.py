import requests
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def serp_news_show(query):
    url = "https://google.serper.dev/news"

    payload = json.dumps({
        "q": f"{query} economy",
        "num": 10,
        "tbs": "qdr:w2"
    })
    headers = {
        'X-API-KEY': '3b3c72db78c6fd3049c1fe4f384a0541747fd7f6',  # Replace with your actual API key
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
        print(sentiments)
        # Format the output for HTML
        output = f"<p><strong>Average Sentiment:</strong> {avg_sentiment}</p><p><strong>Sources:</strong></p>"
        for sentiment in sentiments:
            output += f"<p><strong>Title:</strong> {sentiment['title']}<br>"
            output += f"<strong>Source:</strong> {sentiment['source']}<br>"
            output += f"<strong>Date:</strong> {sentiment['date']}<br>"
            output += f"<strong>URL:</strong> <a href='{sentiment['url']}' target='_blank'>{sentiment['url']}</a><br>"
            output += f"<strong>Sentiment Score:</strong> {sentiment['sentiment']}</p>"

        return output
    else:
        return "Failed to retrieve data"
