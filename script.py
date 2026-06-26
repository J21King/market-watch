import os
import requests
from dotenv import load_dotenv

load_dotenv()

# 1. Load Secrets from Environment Variables
FINNHUB_KEY = os.environ["FINNHUB_API_KEY"]
GROQ_KEY = os.environ["GROQ_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# 2. Config - Add tickers you care about
TICKERS = ["MSFT", "AMZN"]

def get_market_news(ticker):
    # Base URL
    url = "https://finnhub.io/api/v1/company-news?"
    
    query_params = {
        "symbol": ticker,
        "from": "2026-06-01",
        "to": "2026-06-25",
        "token": FINNHUB_KEY
    }
    
    # Requests cleanly merges these together into a legal URL string
    response = requests.get(url, params=query_params).json()
    print(f"Successfully fetched news for {ticker}")
    return response[:3] # Analyze top 3 latest articles

def analyze_sentiment(headline):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    prompt = f"Analyze this market news headline: '{headline}'. Reply ONLY in this exact format: Score: [integer from -5 to 5], Reason: [one short sentence]."
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, json=data, headers=headers).json()
        print("Successfully analyzed sentiment.")  # Debugging line to see the full response
        return response["choices"][0]["message"]["content"]
    except:
        print("Failed to analyze sentiment. Check API response.")
        return "Score: 0, Reason: Analysis failed."

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(url=url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}).json()
        if response.get("ok"):
            print("Telegram notification dispatched successfully!")
        else:
            print(f"Telegram rejected the message. Error details: {response}")
    except Exception as e:
        print(f"Failed to reach Telegram servers. Network error: {e}")


# Main Logic Run
for ticker in TICKERS:
    articles = get_market_news(ticker)
    for art in articles:
        analysis = analyze_sentiment(art['headline'])
        
        # Check if score is highly impactful (e.g., contains 'Score: 4', 'Score: 5', 'Score: -4', etc.)
        if any(x in analysis for x in ["4", "5", "-4", "-5"]):
            alert_msg = f"🚨 {ticker} ALERT 🚨\n\n📰 {art['headline']}\n\n🤖 AI {analysis}\n\n🔗 {art['url']}"
            send_telegram(alert_msg)
            print(f"Alert sent for {ticker}!")
            
print("Run complete.")
