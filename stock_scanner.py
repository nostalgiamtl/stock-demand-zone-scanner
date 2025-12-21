import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.signal import argrelextrema
import config


class DemandZoneScanner:
    def __init__(self, lookback_years=2, zone_tolerance=0.03):
        """
        Initialize the demand zone scanner.

        Args:
            lookback_years (int): Number of years to look back for historical data
            zone_tolerance (float): Price tolerance for being "at" a demand zone (3% default)
        """
        self.lookback_years = lookback_years
        self.zone_tolerance = zone_tolerance

    def fetch_weekly_data(self, ticker):
        """
        Fetch weekly stock data for a given ticker.

        Args:
            ticker (str): Stock ticker symbol

        Returns:
            pd.DataFrame: Weekly OHLCV data or None if error
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * self.lookback_years)

            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date, interval='1wk')

            if df.empty:
                return None

            return df
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None

    def identify_consolidation_zones(self, df):
        """
        Identify consolidation zones where price consolidated before rallying.

        A consolidation zone is defined as:
        1. Multiple weeks of sideways price action (low volatility)
        2. Followed by a significant rally (>10% move up)
        3. Zone hasn't been broken significantly to the downside since formation

        Args:
            df (pd.DataFrame): Weekly OHLCV data

        Returns:
            list: List of dictionaries containing demand zone information
        """
        if df is None or len(df) < config.MIN_DATA_POINTS:
            return []

        zones = []
        df = df.copy()
        df['Range'] = ((df['High'] - df['Low']) / df['Low']) * 100

        # Look for consolidation periods
        min_consolidation_weeks = config.MIN_CONSOLIDATION_WEEKS
        max_range_pct = config.MAX_CONSOLIDATION_RANGE_PCT
        min_rally_pct = config.MIN_RALLY_PCT

        i = 0
        while i < len(df) - min_consolidation_weeks - 5:
            # Check for consolidation
            consolidation_candles = []
            j = i

            # Find consecutive weeks with low range
            while j < len(df) and len(consolidation_candles) < 20:
                if df.iloc[j]['Range'] < max_range_pct:
                    consolidation_candles.append(j)
                    j += 1
                else:
                    if len(consolidation_candles) >= min_consolidation_weeks:
                        break
                    consolidation_candles = []
                    j += 1

            # If we found a consolidation period
            if len(consolidation_candles) >= min_consolidation_weeks:
                consolidation_high = df.iloc[consolidation_candles]['High'].max()
                consolidation_low = df.iloc[consolidation_candles]['Low'].min()
                consolidation_end_idx = consolidation_candles[-1]

                # Check if there was a rally after consolidation
                rally_window = config.RALLY_LOOKHEAD_WEEKS
                if consolidation_end_idx + 5 < len(df):
                    next_highs = df.iloc[consolidation_end_idx + 1:consolidation_end_idx + rally_window + 1]['High']
                    max_next_high = next_highs.max() if len(next_highs) > 0 else 0

                    rally_pct = ((max_next_high - consolidation_high) / consolidation_high) * 100

                    if rally_pct >= min_rally_pct:
                        # This is a valid demand zone
                        zone = {
                            'zone_low': consolidation_low,
                            'zone_high': consolidation_high,
                            'zone_mid': (consolidation_low + consolidation_high) / 2,
                            'formed_date': df.index[consolidation_end_idx],
                            'rally_pct': rally_pct,
                            'strength': len(consolidation_candles)
                        }
                        zones.append(zone)

                i = consolidation_end_idx + 1
            else:
                i += 1

        return zones

    def is_at_demand_zone(self, current_price, zones):
        """
        Check if current price is at or near any demand zone.

        Args:
            current_price (float): Current stock price
            zones (list): List of demand zones

        Returns:
            dict: Information about the matched zone or None
        """
        for zone in zones:
            zone_low = zone['zone_low']
            zone_high = zone['zone_high']

            # Check if current price is within the zone (with tolerance)
            lower_bound = zone_low * (1 - self.zone_tolerance)
            upper_bound = zone_high * (1 + self.zone_tolerance)

            if lower_bound <= current_price <= upper_bound:
                # Calculate distance from zone
                if current_price < zone_low:
                    distance_pct = ((zone_low - current_price) / current_price) * 100
                elif current_price > zone_high:
                    distance_pct = ((current_price - zone_high) / current_price) * 100
                else:
                    distance_pct = 0

                return {
                    **zone,
                    'current_price': current_price,
                    'distance_pct': distance_pct
                }

        return None

    def scan_ticker(self, ticker):
        """
        Scan a single ticker for demand zones.

        Args:
            ticker (str): Stock ticker symbol

        Returns:
            dict: Scan results or None if no zones found
        """
        df = self.fetch_weekly_data(ticker)

        if df is None or df.empty:
            return None

        zones = self.identify_consolidation_zones(df)

        if not zones:
            return None

        current_price = df['Close'].iloc[-1]
        matched_zone = self.is_at_demand_zone(current_price, zones)

        if matched_zone:
            return {
                'ticker': ticker,
                'current_price': current_price,
                'zone': matched_zone,
                'all_zones': zones,
                'data': df
            }

        return None

    def scan_multiple_tickers(self, tickers, progress_callback=None):
        """
        Scan multiple tickers for demand zones.

        Args:
            tickers (list): List of ticker symbols
            progress_callback (callable): Optional callback for progress updates

        Returns:
            list: List of stocks at demand zones
        """
        results = []

        for idx, ticker in enumerate(tickers):
            if progress_callback:
                progress_callback(idx + 1, len(tickers), ticker)

            result = self.scan_ticker(ticker)
            if result:
                results.append(result)

        return results
