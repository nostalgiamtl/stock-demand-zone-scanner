"""
Scheduled scanner script for GitHub Actions.
Runs automated scans and sends Discord notifications.
"""

import os
import json
from datetime import datetime
from stock_scanner import DemandZoneScanner
from utils import get_sp500_tickers
from discord_integration import (
    DiscordNotifier,
    detect_new_stocks,
    detect_price_alerts
)


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
    print("Fetching S&P 500 tickers...")
    tickers = get_sp500_tickers()

    if not tickers:
        print("Error: Failed to fetch S&P 500 tickers")
        return

    print(f"Scanning {len(tickers)} tickers...")

    # Scan all tickers
    results = scanner.scan_multiple_tickers(tickers)

    print(f"Found {len(results)} stocks at demand zones")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"scan_results_{timestamp}.json"

    # Prepare results for JSON (convert datetime to string)
    json_results = []
    for result in results:
        json_result = {
            'ticker': result['ticker'],
            'current_price': result['current_price'],
            'zone': {
                **result['zone'],
                'formed_date': result['zone']['formed_date'].strftime('%Y-%m-%d')
            },
            'indicators': result.get('indicators', {})
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
