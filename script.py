import os
import requests
# from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone


### Uncomment import and load dotenv to load secrets from local env variables
# load_dotenv()
FINNHUB_KEY = os.environ["FINNHUB_API_KEY"]
GROQ_KEY = os.environ["GROQ_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Config - Tickers to be analyzed
TICKERS = ["MSFT", "AMZN", "SPCX", "TSLA", "AVGO", "NVDA"]

class MarketWatch:
    TODAY = datetime.now(timezone.utc).date().isoformat()
    YESTERDAY = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()

    @classmethod
    def get_market_news(cls, ticker):
        url = "https://finnhub.io/api/v1/company-news?"

        query_params = {
            "symbol": ticker,
            "from": cls.YESTERDAY,
            "to": cls.TODAY,
            "token": FINNHUB_KEY
        }

        try:
            response = requests.get(url, params=query_params).json()
        except Exception as e:
            print(f"Failed to fetch news for {ticker}: {e}")
            return []

        print(f"Successfully fetched news for {ticker} ({len(response)} items)")
        return response[:5]  # Return top 5 latest articles to analyze

    @classmethod
    def get_insider_transactions(cls, ticker):
        url = f"https://finnhub.io/api/v1/stock/insider-transactions?"

        query_params = {
            "symbol": ticker,
            # "from": cls.YESTERDAY,
            "from": "2026-06-10",  # Fetch from the start of the year for more data
            "to": cls.TODAY,
            "token": FINNHUB_KEY
        }

        try:
            response = requests.get(url, params=query_params).json()
        except Exception as e:
            print(f"Failed to fetch insider transactions for {ticker}: {e}")
            return []

        print(f"Successfully fetched insider transactions for {ticker}")
        return response.get("data", [])


def analyze_sentiment(headline, summary):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    prompt = f"Analyze this market news headline: '{headline}' and summary: '{summary}'. Reply ONLY in this exact format: Score: [integer from -5 to 5] - [one short sentence]."
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, json=data, headers=headers).json()
        return response["choices"][0]["message"]["content"]
    except:
        return "Score: 0 - Analysis failed."


def format_datetime_pst(timestamp):
    pst = timezone(timedelta(hours=-8))
    return datetime.fromtimestamp(timestamp, pst).strftime("%Y-%m-%d  %I:%M %p PST")


def sort_change_value(value):
    try:
        return abs(float(value))
    except (TypeError, ValueError):
        return float("-inf")


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message,
        "link_preview_options": {
            "is_disabled": True
        },
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url=url, json=data).json()
        if not response.get("ok"):
            print(f"Telegram rejected the message. Error details: {response}")
    except Exception as e:
        print(f"Failed to reach Telegram servers. Network error: {e}")


# Main Logic Run
for ticker in TICKERS:
    articles = MarketWatch.get_market_news(ticker)
    insider_txs = MarketWatch.get_insider_transactions(ticker)
    alerts = []
    txs = []

    for art in articles:
        analysis = analyze_sentiment(art['headline'], art['summary'])

        # Check if score is highly impactful (e.g., contains 'Score: 4', 'Score: 5', 'Score: -4', etc.)
        if any(x in analysis for x in ["4", "5", "-4", "-5"]):
            timestamp = art.get('datetime')
            readable_time = format_datetime_pst(timestamp) if timestamp else 'Unknown time'
            alerts.append(
                f"{readable_time}\n📰 {art['headline']}\n🤖 AI {analysis}\n🔗 {art['url']}"
            )
    
    
    for tx in insider_txs:
        msg = (
            f"| {tx.get('name', ''):<20}"
            f"| {str(tx.get('share', '')):<10}"
            f"| {str(tx.get('change', '')):<10}"
            f"| {str(tx.get('transactionPrice', '')):<6} |"
        )
        txs.append((sort_change_value(tx.get('change')), msg))

    txs.sort(key=lambda item: item[0], reverse=True)
    txs = [msg for _, msg in txs]

    if alerts:
        header_row = f"| {'Name':<20}| {'Shares':<10}| {'Change':<10}| {'Price':<6} |"
        divider_row = "|---------------------|-----------|-----------|--------|"
        insider_block = "\n".join([header_row, divider_row, *txs])
        alert_msg = (
            f"🚨 {ticker} ALERTS 🚨\n\n"
            + "\n\n".join(alerts)
            + f"\n\n💰 {ticker} INSIDER TRADES 💰\n"
            + f"<pre>{insider_block}</pre>"
        )
        send_telegram(alert_msg)
        print(f"Alert sent for {ticker}!")

print("Run complete.")
