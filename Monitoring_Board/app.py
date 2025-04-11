import gradio as gr
import matplotlib

matplotlib.use('Agg')  # Ensure Agg backend for Matplotlib

from sentiment_analysis import analyze_countries, filter_negative_sentiments, visualize_results, countries
from news_retrieval import serp_news_show
from anomaly_detection import anomaly_detection_fun
from protest_anomaly_detection import protest_anomaly_detection_fun

RBB = ["Afghanistan", "Bangladesh", "Bhutan", "Cambodia", "Fiji", "India", "Indonesia", "Kyrgyzstan", "Laos",
        "Myanmar", "Nepal", "Pakistan", "Philippines", "Sri Lanka", "Tajikistan"]
RBN = ["Burundi", "Djibouti", "Ethiopia", "Kenya", "Rwanda", "Somalia", "South Sudan",
        "Uganda"]
RBC = ["Algeria", "Armenia", "Egypt", "Iran", "Iraq",
        "Jordan", "Lebanon", "Libya", "Moldova", "Turkey",
        "Tunisia", "Ukraine"]
def sentiment_analysis():
    results = analyze_countries(countries)
    negative_results = filter_negative_sentiments(results)
    graph_ad = visualize_results(negative_results)

    return graph_ad



def country_news(country):
    news = serp_news_show(country)
    return news

def anomaly_detection(indicator):
    anomaly_graphs = anomaly_detection_fun(indicator)
    return anomaly_graphs

def protest_anomaly_detection(list_name):
    # Map the input string to the corresponding list of countries
    if list_name == "RBB":
        country_list = RBB
    elif list_name == "RBN":
        country_list = RBN
    elif list_name == "RBC":
        country_list = RBC
    else:
        # If the input doesn't match any predefined list, return an empty list or a message
        return []

    # Call the function with the mapped country list
    protest_anomaly_graphs = protest_anomaly_detection_fun(country_list)
    return protest_anomaly_graphs



# Create Gradio interface
with gr.Blocks() as demo:
    # Section for anomaly detection
    with gr.Row():
        with gr.Column(scale=1, min_width=50):
            button = gr.Button("Run Sentiment Analysis")
        with gr.Column(scale=4, min_width=800):
            plot_output = gr.Plot()
    button.click(fn=sentiment_analysis, inputs=[], outputs=[plot_output])

    with gr.Row():
        with gr.Column(scale=1, min_width=50):
            indicator_input = gr.Textbox(label='Enter indicator', placeholder='Indicator name')
            indicator_button = gr.Button('Run Anomaly Detection')
        with gr.Column(scale=4, min_width=800):
            indicator_output = gr.Gallery(label='Anomaly Detection Results')
    indicator_button.click(fn=anomaly_detection, inputs=[indicator_input], outputs=[indicator_output])

    with gr.Row():
        with gr.Column(scale=1, min_width=50):
            list_input = gr.Textbox(label='Enter list (RBB,RBN,RBC)', placeholder='RB name')
            list_button = gr.Button('Run Protest Anomaly Detection')
        with gr.Column(scale=4, min_width=800):
            list_output = gr.Gallery(label='Protest Anomaly Detection Results')
    list_button.click(fn=protest_anomaly_detection, inputs=[list_input], outputs=[list_output])

    # Section for country-specific news
    with gr.Row():
        country_input = gr.Textbox(label="Enter country", placeholder="Country name")
        news_output = gr.HTML(label="Country News")
        news_button = gr.Button("Get News")
        news_button.click(fn=country_news, inputs=[country_input], outputs=[news_output])

# Launch the app
demo.launch()
