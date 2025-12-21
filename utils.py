import requests
import pandas as pd
from bs4 import BeautifulSoup


def get_sp500_tickers():
    """
    Fetch S&P 500 ticker symbols from Wikipedia.

    Returns:
        list: List of S&P 500 ticker symbols
    """
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        table = soup.find('table', {'class': 'wikitable sortable'})

        tickers = []
        for row in table.findAll('tr')[1:]:
            ticker = row.findAll('td')[0].text.strip()
            tickers.append(ticker)

        return tickers
    except Exception as e:
        print(f"Error fetching S&P 500 tickers: {e}")
        return []


def format_price(price):
    """Format price with 2 decimal places."""
    return f"${price:.2f}"


def format_percent(value):
    """Format percentage with 2 decimal places."""
    return f"{value:.2f}%"
