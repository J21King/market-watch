import os
import requests

# 1. Load Secrets from Environment Variables
FINNHUB_KEY = os.environ["FINNHUB_API_KEY"]
GROQ_KEY = os.environ["GROQ_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# 2. Config - Add tickers you care about
TICKERS = ["AAPL", "NVDA", "TSLA"]

def get_market_news(ticker):
    url = f"https://finnhub.io{ticker}&from=2026-01-01&to=2026-12-31&token={FINNHUB_KEY}"
    response = requests.get(url).json()
    return response[:3] # Analyze top 3 latest articles

def analyze_sentiment(headline):
    url = "https://groq.com"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    prompt = f"Analyze this market news headline: '{headline}'. Reply ONLY in this exact format: Score: [integer from -5 to 5], Reason: [one short sentence]."
    
    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        res = requests.post(url, json=data, headers=headers).json()
        return res["choices"][0]["message"]["content"]
    except:
        return "Score: 0, Reason: Analysis failed."

def send_telegram(message):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

# Main Logic Run
for ticker in TICKERS:
    articles = get_market_news(ticker)
    for art in articles:
        analysis = analyze_sentiment(art['headline'])
        
        # Check if score is highly impactful (e.g., contains 'Score: 4', 'Score: 5', 'Score: -4', etc.)
        if any(x in analysis for x in ["4", "5", "-4", "-5"]):
            alert_msg = f"🚨 {ticker} ALERT 🚨\n\n📰 {art['headline']}\n\n🤖 AI {analysis}\n\n🔗 {art['url']}"
            send_telegram(alert_msg)
