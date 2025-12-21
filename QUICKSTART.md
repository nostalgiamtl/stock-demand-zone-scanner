# Quick Start Guide

Get the Stock Demand Zone Scanner running in 3 minutes!

## Step 1: Install Dependencies

Open a terminal in this directory and run:

```bash
pip install -r requirements.txt
```

## Step 2: Test the Scanner (Optional)

Before running the full app, test that everything works:

```bash
python test_scanner.py
```

This will scan 10 popular stocks and show you if the scanner is working correctly.

## Step 3: Launch the Streamlit App

```bash
streamlit run app.py
```

Your browser should automatically open to `http://localhost:8501`

## Step 4: Configure and Scan

1. **Adjust settings** in the left sidebar:
   - Lookback Period: 2 years (recommended)
   - Zone Tolerance: 3% (recommended)
   - Minimum Rally: 10% (recommended)

2. **Click "Start Scan"** to begin scanning S&P 500 stocks

3. **Review results** in the table and click on individual stocks to see charts

## Customization

Want to change how demand zones are detected? Edit [config.py](config.py):

```python
# More aggressive: tighter consolidations, bigger rallies
MIN_CONSOLIDATION_WEEKS = 4
MAX_CONSOLIDATION_RANGE_PCT = 3.0
MIN_RALLY_PCT = 15.0

# More lenient: catches more zones
MIN_CONSOLIDATION_WEEKS = 2
MAX_CONSOLIDATION_RANGE_PCT = 7.0
MIN_RALLY_PCT = 7.0
```

## Troubleshooting

### "No module named 'streamlit'"
- Run: `pip install -r requirements.txt`

### "Failed to fetch S&P 500 tickers"
- Check your internet connection
- Wikipedia may be temporarily unavailable

### "No stocks found at demand zones"
- Try increasing the Zone Tolerance to 5-7%
- Try decreasing the Minimum Rally to 7-8%
- Market conditions may mean fewer stocks are at demand zones right now

### Slow scanning
- Normal! Scanning 500 stocks takes 5-15 minutes depending on your internet speed
- Each stock requires downloading 2 years of weekly data

## Tips

1. **Start with test_scanner.py** to verify everything works
2. **Run scans during market hours** for most up-to-date data
3. **Save interesting results** by taking screenshots
4. **Customize config.py** to match your trading style
5. **Run multiple scans** with different parameters to compare results

## Need Help?

- Check [README.md](README.md) for full documentation
- Review [config.py](config.py) for all customization options
- Examine [stock_scanner.py](stock_scanner.py) to understand the algorithm

Happy scanning!
