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
TICKERS = [ticker.strip() for ticker in os.environ.get("TICKERS").split(",") if ticker.strip()]

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
            "from": cls.YESTERDAY,
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
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, json=data, headers=headers).json()
        if "error" in response:
            print(f"Groq rejected the request: {response["error"]}")
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Failed to analyze sentiment: {e}")
        return "Score: 0 - Analysis failed."


def format_datetime_pst(timestamp):
    pst = timezone(timedelta(hours=-8))
    return datetime.fromtimestamp(timestamp, pst).strftime("%Y-%m-%d  %I:%M %p PST")


def sort_change_value(value):
    try:
        return abs(float(value))
    except (TypeError, ValueError):
        return float("-inf")


def format_table_cell(value, width, align='left'):
    text = str(value or '')
    if len(text) > width:
        text = text[:width - 1] + '…'
    pad_char = ' '  # preserve monospace alignment in <pre>
    if align == 'right':
        return text.rjust(width, pad_char)
    return text.ljust(width, pad_char)


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
    name_column_width = 15  # Fixed width for the name column in the insider transactions table
    share_column_width = 10  # Fixed width for the shares column
    change_column_width = 10  # Fixed width for the change column
    price_column_width = 8  # Fixed width for the price column
    alerts = []
    txs = []

    for art in articles:
        analysis = analyze_sentiment(art['headline'], art['summary'])

        # Check if score is highly impactful (e.g., contains 'Score: 4', 'Score: 5', 'Score: -4', etc.)
        if any(x in analysis for x in ["4", "5", "-3", "-4", "-5"]):
            timestamp = art.get('datetime')
            readable_time = format_datetime_pst(timestamp) if timestamp else 'Unknown time'
            alerts.append(
                f"{readable_time}\n📰 {art['headline']}\n🤖 AI {analysis}\n🔗 {art['url']}"
            )
    
    
    for tx in insider_txs:
        name = tx.get('name', '') or ''
        msg = (
            "|" + format_table_cell(name, name_column_width)
            + "|" + format_table_cell(tx.get('share', ''), share_column_width, align='right')
            + "|" + format_table_cell(tx.get('change', ''), change_column_width, align='right')
            + "|" + format_table_cell(tx.get('transactionPrice', ''), price_column_width, align='right') + "|"
        )
        txs.append((sort_change_value(tx.get('change')), msg))

    txs.sort(key=lambda item: item[0], reverse=True)
    txs = [msg for _, msg in txs]

    if alerts or txs:
        header_row = (
            "|" + format_table_cell('Name', name_column_width)
            + "|" + format_table_cell('Shares', share_column_width)
            + "|" + format_table_cell('Change', change_column_width)
            + "|" + format_table_cell('Price', price_column_width) + "|"
        )
        divider_row = (
            "|" + '-' * name_column_width
            + "|" + '-' * share_column_width
            + "|" + '-' * change_column_width
            + "|" + '-' * price_column_width + "|"
        )
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
