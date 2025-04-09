#!/usr/bin/env python3
"""
News Sentiment Analyzer

This script searches for news about a specified country/region from the past 24 hours,
performs sentiment analysis on article titles, and summarizes the most negative articles.
"""

import os
import sys
import json
import statistics
from datetime import datetime, timedelta
import argparse
import requests
from typing import List, Dict, Any, Tuple
import openai
from dotenv import load_dotenv
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Load environment variables from .env file
load_dotenv()

# Ensure NLTK data is downloaded
try:
    import nltk
    nltk.download('punkt', quiet=True)
except Exception as e:
    print(f"Warning: Could not download NLTK data: {e}")

# Initialize BERT model for sentiment analysis
try:
    tokenizer = AutoTokenizer.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
    model = AutoModelForSequenceClassification.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"BERT model loaded successfully (using {device})")
except Exception as e:
    print(f"Warning: Could not load BERT model: {e}")
    sys.exit(1)

# Configure your API keys here or use environment variables
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Check if API keys are available
if not SERPER_API_KEY:
    print("Error: SERPER_API_KEY not found. Please set it in your .env file or as an environment variable.")
    sys.exit(1)
    
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY not found. Please set it in your .env file or as an environment variable.")
    sys.exit(1)

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Analyze news sentiment for a country or region")
    parser.add_argument("query", help="Country or region name to search for")
    parser.add_argument("--limit", type=int, default=10, 
                        help="Number of negative articles to summarize (default: 10)")
    parser.add_argument("--serper-key", help="Serper API key (overrides environment variable)")
    parser.add_argument("--openai-key", help="OpenAI API key (overrides environment variable)")
    return parser.parse_args()

def search_news(query: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Search for news articles using Serper API.
    
    Args:
        query: The search query (country or region name)
        api_key: Serper API key
        
    Returns:
        List of news article dictionaries
    """
    # Create a search query with time restriction for last 24 hours
    search_query = f"{query} news"
    
    # Set up the Serper API request
    url = "https://google.serper.dev/news"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "q": search_query,
        "timeRange": "1d"  # Last 24 hours
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Extract news items
        if "news" in data:
            return data["news"]
        else:
            print("No news found in the API response")
            return []
    except requests.RequestException as e:
        print(f"Error searching for news: {e}")
        return []

def analyze_sentiment(titles: List[str]) -> List[float]:
    """
    Perform sentiment analysis on a list of article titles using BERT.
    
    Args:
        titles: List of article titles
        
    Returns:
        List of sentiment polarity scores (-1.0 to 1.0)
    """
    sentiment_scores = []
    
    for title in titles:
        if not title:
            continue
            
        # Tokenize the title and prepare it for the model
        inputs = tokenizer(title, return_tensors="pt", padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get model prediction
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            
        # The BERT model used outputs a score from 1-5 where:
        # 1 is very negative, 3 is neutral, 5 is very positive
        # Convert to a scale from -1.0 to 1.0 to match previous TextBlob output
        predicted_class = torch.argmax(logits, dim=1).item()
        
        # Convert from 1-5 scale to -1.0 to 1.0 scale
        # 1 -> -1.0, 2 -> -0.5, 3 -> 0, 4 -> 0.5, 5 -> 1.0
        score = (predicted_class - 3) / 2
        
        sentiment_scores.append(score)
    
    return sentiment_scores

def calculate_statistics(scores: List[float]) -> Tuple[float, float]:
    """
    Calculate mean and standard deviation of sentiment scores.
    
    Args:
        scores: List of sentiment scores
        
    Returns:
        Tuple of (mean, standard_deviation)
    """
    if not scores:
        return 0.0, 0.0
    
    mean = statistics.mean(scores)
    
    # Handle case where there's only one score (std requires at least 2 values)
    if len(scores) > 1:
        std_dev = statistics.stdev(scores)
    else:
        std_dev = 0.0
    
    return mean, std_dev

def get_sentiment_score(title: str) -> float:
    """
    Perform sentiment analysis on a single article title using BERT.
    
    Args:
        title: Article title
        
    Returns:
        Sentiment polarity score (-1.0 to 1.0)
    """
    if not title:
        return 0.0
        
    # Tokenize the title and prepare it for the model
    inputs = tokenizer(title, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
        
    # Get model prediction
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
            
    # The BERT model used outputs a score from 1-5 where:
    # 1 is very negative, 3 is neutral, 5 is very positive
    # Convert to a scale from -1.0 to 1.0 to match previous TextBlob output
    predicted_class = torch.argmax(logits, dim=1).item()
        
    # Convert from 1-5 scale to -1.0 to 1.0 scale
    # 1 -> -1.0, 2 -> -0.5, 3 -> 0, 4 -> 0.5, 5 -> 1.0
    score = (predicted_class - 3) / 2
        
    return score

def summarize_articles(articles: List[Dict[str, Any]], api_key: str, include_both_sentiments: bool = False) -> str:
    """
    Use OpenAI to summarize a list of news articles.
    
    Args:
        articles: List of article dictionaries with titles and snippets
        api_key: OpenAI API key
        include_both_sentiments: Whether to include both positive and negative summaries
        
    Returns:
        Summarized text about the articles
    """
    if not articles:
        return "No articles to summarize."
        
    # Prepare text content from articles
    negative_articles = []
    positive_articles = []
    
    # Group articles by sentiment
    for article in articles:
        title = article.get("title", "")
        sentiment_score = get_sentiment_score(title)
        
        if sentiment_score < 0.4:  # Negative sentiment
            negative_articles.append(article)
        else:
            positive_articles.append(article)
    
    # Prepare article texts
    negative_texts = []
    for i, article in enumerate(negative_articles, 1):
        title = article.get("title", "No title")
        snippet = article.get("snippet", "No snippet")
        negative_texts.append(f"Negative Article {i}:\nTitle: {title}\nSummary: {snippet}\n")
    
    positive_texts = []
    for i, article in enumerate(positive_articles, 1):
        title = article.get("title", "No title")
        snippet = article.get("snippet", "No snippet")
        positive_texts.append(f"Positive Article {i}:\nTitle: {title}\nSummary: {snippet}\n")
    
    # Create the prompt for OpenAI
    prompt = f"""
    Here are news articles about a specific country or region.
    """
    
    if negative_texts:
        prompt += f"""
        NEGATIVE NEWS ARTICLES:
        {"\n".join(negative_texts)}
        """
    
    if positive_texts:
        prompt += f"""
        POSITIVE NEWS ARTICLES:
        {"\n".join(positive_texts)}
        """
    
    prompt += """
    Please provide a concise summary that includes TWO distinct sections with CLEAR and CONSISTENT formatting:
    
    SECTION 1: NEGATIVE NEWS SUMMARY
    1. The main negative events or issues being reported
    2. Common themes or patterns across the negative articles
    
    SECTION 2: POSITIVE NEWS SUMMARY
    1. The main positive developments or achievements being reported
    2. Common themes or patterns of progress across the positive articles
    
    Format requirements:
    - Use proper markdown formatting with clear section headers (## for main sections, ### for subsections)
    - Use bullet points (- ) for each distinct point or event
    - Ensure clean paragraph breaks between sections
    - Keep consistent indentation for bullet points
    - Maintain proper spacing between paragraphs
    - Format each section consistently
    - Avoid using asterisks (*) for formatting
    - Make sure all bullets are properly aligned
    - Keep your response factual, balanced, and under 1000 words
    """
    
    # Try with a manual API call first as a fallback
    try:
        import requests
        print("Attempting direct API call to OpenAI...")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",  # Fallback to a widely available model
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that summarizes news articles objectively and accurately."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 1000
        }
        
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"Direct API call failed with status {response.status_code}: {response.text}")
            # Continue with the standard client as a backup
    except Exception as direct_api_error:
        print(f"Direct API attempt failed: {direct_api_error}")
        # Continue with the standard client
    
    # Standard client approach
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Ensure we're using the correct API key
            print(f"Debug - Using API key for OpenAI: {api_key[:5]}...{api_key[-5:]}")
            
            # Create a fresh client for each attempt
            client = openai.OpenAI(
                api_key=api_key  # Make sure we're using the passed API key
            )
            
            # Try different models in order of preference
            models_to_try = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
            
            last_error = None
            for model in models_to_try:
                try:
                    print(f"Trying model: {model}")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that summarizes news articles objectively and accurately."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0,
                        max_tokens=1000
                    )
                    # If successful, return the result
                    return response.choices[0].message.content
                except Exception as model_error:
                    last_error = model_error
                    print(f"Error with {model} model: {model_error}. Trying next model...")
                    continue
            
            # If we get here, all models failed
            raise last_error or Exception("All models failed without specific error")
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Error calling OpenAI API: {e}. Retrying ({attempt + 1}/{max_retries})...")
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"Failed to get summary after {max_retries} attempts: {e}")
                error_details = str(e)
                # Provide a more detailed error message
                return f"Error: Could not generate summary due to API issues. Details: {error_details}"
                
    # This should never be reached, but just in case
    return "Error: Could not generate summary due to unknown issues."

def main():
    """Main function to run the news sentiment analyzer."""
    args = parse_arguments()
    
    # Get API keys
    serper_key = args.serper_key or SERPER_API_KEY
    openai_key = args.openai_key or OPENAI_API_KEY
    
    # Explicitly print which API key we're using (for debugging)
    print(f"Using OpenAI API key: {openai_key[:5]}...{openai_key[-5:]}")
    
    # Search for news
    print(f"Searching for news about '{args.query}' from the past 24 hours...")
    articles = search_news(args.query, serper_key)
    
    if not articles:
        print("No news articles found.")
        return
    
    print(f"Found {len(articles)} news articles.")
    
    # Extract titles for sentiment analysis
    titles = [article.get("title", "") for article in articles if article.get("title")]
    
    # Analyze sentiment
    print("Analyzing sentiment of article titles...")
    sentiment_scores = analyze_sentiment(titles)
    
    # Calculate statistics
    mean_score, std_dev = calculate_statistics(sentiment_scores)
    
    # Print results
    print("\nSentiment Analysis Results:")
    print(f"Mean sentiment score: {mean_score:.4f} (-1.0 negative to 1.0 positive)")
    print(f"Standard deviation: {std_dev:.4f}\n")
    
    # Find most negative and positive articles
    if sentiment_scores:
        min_score = min(sentiment_scores)
        max_score = max(sentiment_scores)
        min_index = sentiment_scores.index(min_score)
        max_index = sentiment_scores.index(max_score)
        
        print(f"Most negative article (score: {min_score:.4f}):")
        print(f"- {titles[min_index]}\n")
        
        print(f"Most positive article (score: {max_score:.4f}):")
        print(f"- {titles[max_index]}\n")
    
    # Sort articles by sentiment score (ascending)
    articles_with_scores = list(zip(articles, sentiment_scores))
    sorted_articles = sorted(articles_with_scores, key=lambda x: x[1])
    
    # Get the most negative articles
    negative_articles = [article for article, _ in sorted_articles[:args.limit]]
    
    # Summarize negative articles
    print(f"Summarizing the {args.limit} most negative articles using OpenAI...\n")
    summary = summarize_articles(negative_articles, openai_key, include_both_sentiments=True)
    
    if summary.startswith("Error:") or summary.startswith("Unexpected error"):
        print(summary)
        print("\nFalling back to displaying negative articles directly:\n")
        for i, article in enumerate(negative_articles, 1):
            title = article.get("title", "No title")
            snippet = article.get("snippet", "No snippet")
            link = article.get("link", "No link")
            score = next((score for art, score in articles_with_scores if art == article), None)
            print(f"{i}. {title} (sentiment score: {score:.4f})")
            print(f"   {snippet}")
            print(f"   Link: {link}\n")
    else:
        print("=== SUMMARY OF NEGATIVE NEWS ===")
        print(summary)

    # Get the most positive articles
    positive_articles = [article for article, _ in sorted_articles[-args.limit:]]
    
    # Summarize positive articles
    print(f"Summarizing the {args.limit} most positive articles using OpenAI...\n")
    summary = summarize_articles(positive_articles, openai_key, include_both_sentiments=True)
    
    if summary.startswith("Error:") or summary.startswith("Unexpected error"):
        print(summary)
        print("\nFalling back to displaying positive articles directly:\n")
        for i, article in enumerate(positive_articles, 1):
            title = article.get("title", "No title")
            snippet = article.get("snippet", "No snippet")
            link = article.get("link", "No link")
            score = next((score for art, score in articles_with_scores if art == article), None)
            print(f"{i}. {title} (sentiment score: {score:.4f})")
            print(f"   {snippet}")
            print(f"   Link: {link}\n")
    else:
        print("=== SUMMARY OF POSITIVE NEWS ===")
        print(summary)

if __name__ == "__main__":
    main()
