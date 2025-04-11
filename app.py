import gradio as gr
import matplotlib

matplotlib.use('Agg')  # Ensure Agg backend for Matplotlib

from sentiment_analysis import analyze_countries, filter_negative_sentiments, visualize_results, countries
from news_retrieval import serp_news_show


def sentiment_analysis():
    results = analyze_countries(countries)
    negative_results = filter_negative_sentiments(results)
    graph_ad = visualize_results(negative_results)

    return graph_ad



def country_news(country):
    news = serp_news_show(country)
    return news

def anomaly_detection(indicator):
    analyze

# Create Gradio interface
with gr.Blocks() as demo:
    # Section for anomaly detection
    with gr.Row():
        button = gr.Button("Run Anomaly Detection")
        plot_output = gr.Plot()
        button.click(fn=sentiment_analysis, inputs=[], outputs=[plot_output])

    # Section for country-specific news
    with gr.Row():
        country_input = gr.Textbox(label="Enter country", placeholder="Country name")
        news_output = gr.HTML(label="Country News")
        news_button = gr.Button("Get News")
        news_button.click(fn=country_news, inputs=[country_input], outputs=[news_output])

# Launch the app
demo.launch()
