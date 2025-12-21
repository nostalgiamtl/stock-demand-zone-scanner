# Stock Demand Zone Scanner

A Streamlit web application that scans S&P 500 stocks to identify those trading at multi-year demand zones using weekly timeframe analysis.

## What are Demand Zones?

Demand zones are price consolidation areas where:
1. Price consolidated sideways for multiple weeks (low volatility)
2. Then rallied significantly (10%+ move upward)
3. Price has now returned to that zone, potentially offering support

These zones often act as support levels where buyers step in, making them interesting areas for potential reversals.

## Features

- **Automated Scanning**: Scans all S&P 500 stocks automatically
- **Weekly Timeframe Analysis**: Uses weekly candles for multi-year perspective
- **Visual Charts**: Interactive charts showing demand zones and current price
- **Customizable Parameters**:
  - Lookback period (1-5 years)
  - Zone tolerance (how close price needs to be)
  - Minimum rally requirement after consolidation
- **Sortable Results**: Sort by distance, rally %, zone strength, or ticker
- **Detailed Analytics**: View volume, zone formation dates, and strength metrics

## Installation

1. Clone this repository or download the files

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Configure scanner settings in the sidebar:
   - **Lookback Period**: How many years of historical data to analyze
   - **Zone Tolerance**: How close the current price needs to be (%)
   - **Minimum Rally**: Minimum price increase after consolidation to qualify as a demand zone

3. Click "Start Scan" to begin scanning S&P 500 stocks

4. Review results:
   - Summary table shows all stocks at demand zones
   - Sort and filter results
   - Click on individual stocks to view detailed charts

## How It Works

### Demand Zone Detection Algorithm

1. **Fetch Weekly Data**: Downloads 2+ years of weekly OHLCV data
2. **Find Consolidation Periods**: Identifies periods where price moved sideways (< 5% range) for 3+ weeks
3. **Verify Rally**: Confirms that price rallied 10%+ after the consolidation
4. **Check Current Price**: Determines if current price is at or near the zone (within tolerance)

### Parameters

- **Consolidation**: Min 3 weeks, max 5% weekly range
- **Rally**: Min 10% upward move after consolidation ends
- **Tolerance**: Default 3% distance from zone (configurable)

## File Structure

```
stock-identifier-simba/
├── app.py                 # Streamlit UI application
├── stock_scanner.py       # Core scanning logic and demand zone detection
├── utils.py              # Helper functions (S&P 500 ticker fetcher, formatters)
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Deployment

### Streamlit Cloud (Free)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Deploy!

### Local Network

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Then access from other devices on your network at `http://YOUR_IP:8501`

## Customization

### Scanning Different Stock Universes

Edit [utils.py](utils.py) to modify the `get_sp500_tickers()` function to return your custom ticker list.

### Adjusting Detection Logic

Modify [stock_scanner.py](stock_scanner.py) parameters:
- `min_consolidation_weeks`: Minimum weeks of consolidation (default: 3)
- `max_range_pct`: Maximum range during consolidation (default: 5%)
- `min_rally_pct`: Minimum rally after consolidation (default: 10%)

## Limitations

- Data source: Yahoo Finance (via yfinance) - free but may have delays
- S&P 500 only by default (customizable)
- Weekly timeframe analysis (not intraday)
- Historical analysis only (not predictive)

## Disclaimer

This tool is for educational and research purposes only. It does not constitute financial advice. Always do your own research and consult with a financial advisor before making investment decisions.

## License

MIT License - feel free to modify and use as needed
