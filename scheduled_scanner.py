"""
Scheduled scanner script for GitHub Actions.
Runs automated scans and sends Discord notifications.
"""

import os
import json
import numpy as np
from datetime import datetime
from stock_scanner import DemandZoneScanner
from utils import get_sp500_tickers
from discord_integration import (
    DiscordNotifier,
    detect_new_stocks,
    detect_price_alerts
)


def convert_to_json_serializable(obj):
    """
    Convert numpy types and other non-JSON-serializable types to native Python types.

    Args:
        obj: Object to convert

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_to_json_serializable(obj.tolist())
    else:
        return obj


def main():
    """Run scheduled scan and send Discord notifications."""

    print(f"Starting scheduled scan at {datetime.now()}")

    # Get Discord webhook from environment variable
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL not set in environment variables")
        return

    # Initialize scanner
    scanner = DemandZoneScanner(lookback_years=2, zone_tolerance=0.03)

    # Fetch tickers
    print("Fetching stock tickers (S&P 500 + NASDAQ)...")
    tickers = get_sp500_tickers()

    if not tickers:
        print("Error: Failed to fetch stock tickers")
        return

    print(f"Scanning {len(tickers)} tickers (S&P 500 + NASDAQ)...")

    # Scan all tickers
    results = scanner.scan_multiple_tickers(tickers)

    print(f"Found {len(results)} stocks at demand zones")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"scan_results_{timestamp}.json"

    # Prepare results for JSON (convert datetime and numpy types to native Python types)
    json_results = []
    for result in results:
        # Convert zone data
        zone_data = {k: v for k, v in result['zone'].items() if k != 'formed_date'}
        zone_data['formed_date'] = result['zone']['formed_date'].strftime('%Y-%m-%d')

        # Convert indicators to JSON-serializable format
        indicators = convert_to_json_serializable(result.get('indicators', {}))

        json_result = {
            'ticker': result['ticker'],
            'current_price': float(result['current_price']),
            'zone': convert_to_json_serializable(zone_data),
            'indicators': indicators
        }
        json_results.append(json_result)

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_stocks': len(results),
            'results': json_results
        }, f, indent=2)

    print(f"Results saved to {output_file}")

    # Send Discord notifications
    if webhook_url and results:
        notifier = DiscordNotifier(webhook_url)

        # Detect new stocks
        new_stocks = detect_new_stocks(results)

        if new_stocks:
            print(f"Sending {len(new_stocks)} new stock(s) to Discord...")
            success = notifier.send_new_stocks_alert(new_stocks, datetime.now())
            if success:
                print("✅ New stocks alert sent successfully")
            else:
                print("❌ Failed to send new stocks alert")
        else:
            print("No new stocks to report")

        # Price alerts
        alerts = detect_price_alerts(results)

        if alerts:
            print(f"Sending {len(alerts)} price alert(s)...")
            for ticker, alert_type, details in alerts[:5]:  # Limit to 5
                notifier.send_price_alert(ticker, alert_type, details)
            print("✅ Price alerts sent successfully")
        else:
            print("No price alerts to send")

    print(f"Scan completed at {datetime.now()}")


if __name__ == "__main__":
    main()
