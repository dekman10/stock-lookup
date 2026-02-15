import re
import socket

import requests
import yfinance as yf
from flask import Flask, render_template, request

app = Flask(__name__)


def format_large_number(num):
    if num is None:
        return "N/A"
    if num >= 1_000_000_000_000:
        return f"${num / 1_000_000_000_000:.2f}T"
    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f}B"
    if num >= 1_000_000:
        return f"${num / 1_000_000:.2f}M"
    return f"${num:,.0f}"


def format_price(value):
    return f"${value:,.2f}" if value else "N/A"


def format_change(current_price, previous_close):
    if current_price and previous_close:
        change = current_price - previous_close
        change_pct = (change / previous_close) * 100
        sign = "+" if change >= 0 else ""
        return f"{sign}{change:.2f} ({sign}{change_pct:.2f}%)"
    return "N/A"


def validate_ticker(ticker):
    if not ticker or not re.match(r'^[A-Za-z.\-]{1,10}$', ticker):
        return False, "Invalid ticker. Use 1-10 letters (e.g. AAPL, BRK-B, BRK.B)."
    return True, None


def fetch_stock_data(ticker_symbol):
    """Fetch stock data and return a dict, or (None, error_message) on failure."""
    stock = yf.Ticker(ticker_symbol)

    try:
        info = stock.info
    except (requests.ConnectionError, requests.Timeout, socket.gaierror):
        return None, "No internet connection. Please check your network and try again."
    except requests.HTTPError as e:
        return None, f"Server error: {e}"
    except Exception as e:
        return None, f"Error fetching data: {e}"

    name = info.get("shortName") or info.get("longName")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

    if not name or (not current_price and not previous_close):
        return None, f"'{ticker_symbol.upper()}' is not a valid ticker symbol or has no market data."

    data = {
        "name": name,
        "ticker": ticker_symbol.upper(),
        "current_price": current_price,
        "previous_close": previous_close,
        "change": format_change(current_price, previous_close),
        "change_positive": current_price >= previous_close if current_price and previous_close else None,
        "high_52": format_price(info.get("fiftyTwoWeekHigh")),
        "low_52": format_price(info.get("fiftyTwoWeekLow")),
        "market_cap": format_large_number(info.get("marketCap")),
        "currency": info.get("currency", "USD"),
        "recommendation": (info.get("recommendationKey") or "").upper() or None,
        "target_mean": format_price(info.get("targetMeanPrice")),
        "target_high": format_price(info.get("targetHighPrice")),
        "target_low": format_price(info.get("targetLowPrice")),
        "num_analysts": info.get("numberOfAnalystOpinions"),
        "current_price_fmt": format_price(current_price),
        "previous_close_fmt": format_price(previous_close),
    }
    return data, None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/lookup", methods=["POST"])
def lookup():
    ticker = request.form.get("ticker", "").strip()
    valid, err = validate_ticker(ticker)
    if not valid:
        return render_template("index.html", error=err)

    data, err = fetch_stock_data(ticker)
    if err:
        return render_template("index.html", error=err)

    return render_template("index.html", stock=data)


@app.route("/compare", methods=["POST"])
def compare():
    ticker1 = request.form.get("ticker1", "").strip()
    ticker2 = request.form.get("ticker2", "").strip()

    valid1, err1 = validate_ticker(ticker1)
    valid2, err2 = validate_ticker(ticker2)
    if not valid1:
        return render_template("index.html", error=err1)
    if not valid2:
        return render_template("index.html", error=err2)

    data1, err1 = fetch_stock_data(ticker1)
    if err1:
        return render_template("index.html", error=err1)

    data2, err2 = fetch_stock_data(ticker2)
    if err2:
        return render_template("index.html", error=err2)

    return render_template("index.html", compare=[data1, data2])


if __name__ == "__main__":
    app.run(debug=True)
