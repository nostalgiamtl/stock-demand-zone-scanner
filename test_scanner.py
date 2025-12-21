"""
Quick test script to verify the scanner works before running a full S&P 500 scan.
Tests on a small set of popular tickers.
"""

from stock_scanner import DemandZoneScanner
from utils import format_price, format_percent


def test_scanner():
    """Test the scanner on a few popular stocks."""

    # Test tickers - mix of different sectors
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'JPM', 'V', 'WMT', 'MA']

    print("=" * 60)
    print("Testing Demand Zone Scanner")
    print("=" * 60)
    print(f"\nScanning {len(test_tickers)} test tickers...\n")

    # Initialize scanner
    scanner = DemandZoneScanner(lookback_years=2, zone_tolerance=0.03)

    results = []

    for ticker in test_tickers:
        print(f"Scanning {ticker}...", end=" ")
        result = scanner.scan_ticker(ticker)

        if result:
            print("✓ Found at demand zone!")
            results.append(result)
        else:
            print("✗ No demand zone match")

    print("\n" + "=" * 60)
    print(f"Results: {len(results)} stocks at demand zones")
    print("=" * 60)

    if results:
        print("\nDetailed Results:\n")

        for result in results:
            ticker = result['ticker']
            current_price = result['current_price']
            zone = result['zone']

            print(f"\n📊 {ticker}")
            print(f"   Current Price: {format_price(current_price)}")
            print(f"   Zone Range: {format_price(zone['zone_low'])} - {format_price(zone['zone_high'])}")
            print(f"   Distance from Zone: {format_percent(abs(zone['distance_pct']))}")
            print(f"   Rally After Zone: {format_percent(zone['rally_pct'])}")
            print(f"   Zone Strength: {zone['strength']} weeks")
            print(f"   Zone Formed: {zone['formed_date'].strftime('%Y-%m-%d')}")
            print(f"   Total Zones Found: {len(result['all_zones'])}")

    else:
        print("\nNo stocks found at demand zones in this test set.")
        print("This is normal - try adjusting parameters or test with more tickers.")

    print("\n" + "=" * 60)
    print("Test complete! If this worked, you can run the full Streamlit app.")
    print("Run: streamlit run app.py")
    print("=" * 60)


if __name__ == "__main__":
    test_scanner()
