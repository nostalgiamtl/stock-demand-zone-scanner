import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.signal import argrelextrema
import config

try:
    import pandas_ta as ta
    USE_PANDAS_TA = True
except ImportError:
    # Fallback to simple indicators if pandas-ta not available
    from indicators_simple import calculate_indicators
    USE_PANDAS_TA = False


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

    def is_at_demand_zone(self, current_price, zones, df):
        """
        Check if current price is at or near any demand zone that previously held and broke out.

        This identifies stocks that:
        1. Had a support zone that held (didn't break down)
        2. Broke out upward from that zone (validated support)
        3. Have NOW pulled back to that same support level (buying opportunity)

        Args:
            current_price (float): Current stock price
            zones (list): List of demand zones
            df (pd.DataFrame): Price data to verify the stock rallied away and came back

        Returns:
            dict: Information about the matched zone or None
        """
        for zone in zones:
            zone_low = zone['zone_low']
            zone_high = zone['zone_high']
            zone_mid = zone['zone_mid']
            formed_date = zone['formed_date']

            # Check if current price is at/near the zone (within 5% above zone high)
            # We want stocks AT support, not way above it
            lower_bound = zone_low * (1 - self.zone_tolerance)
            upper_bound = zone_high * (1 + 0.05)  # Allow up to 5% above zone

            if lower_bound <= current_price <= upper_bound:
                # Verify this zone is "old enough" (formed at least 4 weeks ago)
                # This ensures the rally happened in the PAST, not currently happening
                weeks_since_formation = (df.index[-1] - formed_date).days / 7

                if weeks_since_formation < 4:
                    # Zone too recent, skip it
                    continue

                # Check that price actually rallied away from the zone and came back
                # Look at price action AFTER zone formation
                zone_idx = df.index.get_loc(formed_date)
                if zone_idx + 5 < len(df):
                    # Get price data after zone formation
                    prices_after = df.iloc[zone_idx + 1:]['High']
                    max_price_after = prices_after.max()

                    # Verify price went significantly higher (10%+) after zone formation
                    rally_from_zone = ((max_price_after - zone_high) / zone_high) * 100

                    if rally_from_zone < 10:
                        # Price never really left the zone, skip it
                        continue

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
                    'distance_pct': distance_pct,
                    'weeks_since_formation': round(weeks_since_formation, 1)
                }

        return None

    def calculate_technical_indicators(self, df):
        """
        Calculate technical indicators for the stock.

        Args:
            df (pd.DataFrame): Weekly OHLCV data

        Returns:
            dict: Technical indicators
        """
        # Use simple fallback if pandas-ta not available
        if not USE_PANDAS_TA:
            return calculate_indicators(df)

        if df is None or len(df) < 50:
            return None

        try:
            df_calc = df.copy()

            # RSI (14-period)
            rsi = ta.rsi(df_calc['Close'], length=14)
            current_rsi = rsi.iloc[-1] if not rsi.empty else None

            # MACD
            macd_result = ta.macd(df_calc['Close'])
            if macd_result is not None and not macd_result.empty:
                current_macd = macd_result['MACD_12_26_9'].iloc[-1]
                current_macd_signal = macd_result['MACDs_12_26_9'].iloc[-1]
                current_macd_hist = macd_result['MACDh_12_26_9'].iloc[-1]
            else:
                current_macd = current_macd_signal = current_macd_hist = None

            # Moving Averages
            sma_50 = ta.sma(df_calc['Close'], length=50)
            sma_200 = ta.sma(df_calc['Close'], length=200)

            current_price = df_calc['Close'].iloc[-1]
            ma_50 = sma_50.iloc[-1] if not sma_50.empty else None
            ma_200 = sma_200.iloc[-1] if not sma_200.empty and len(df_calc) >= 200 else None

            # Volume Analysis
            avg_volume_20 = df_calc['Volume'].rolling(window=20).mean().iloc[-1]
            current_volume = df_calc['Volume'].iloc[-1]
            volume_ratio = (current_volume / avg_volume_20) if avg_volume_20 > 0 else 1

            # Calculate position relative to MAs
            above_ma50 = current_price > ma_50 if ma_50 else None
            above_ma200 = current_price > ma_200 if ma_200 else None

            # RSI interpretation
            rsi_signal = None
            if current_rsi:
                if current_rsi < 30:
                    rsi_signal = "Oversold"
                elif current_rsi > 70:
                    rsi_signal = "Overbought"
                else:
                    rsi_signal = "Neutral"

            # MACD interpretation
            macd_signal_text = None
            if current_macd and current_macd_signal:
                if current_macd > current_macd_signal:
                    macd_signal_text = "Bullish"
                else:
                    macd_signal_text = "Bearish"

            return {
                'rsi': current_rsi,
                'rsi_signal': rsi_signal,
                'macd': current_macd,
                'macd_signal': current_macd_signal,
                'macd_histogram': current_macd_hist,
                'macd_trend': macd_signal_text,
                'ma_50': ma_50,
                'ma_200': ma_200,
                'above_ma50': above_ma50,
                'above_ma200': above_ma200,
                'current_volume': current_volume,
                'avg_volume_20': avg_volume_20,
                'volume_ratio': volume_ratio
            }

        except Exception as e:
            print(f"Error calculating indicators: {e}")
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
        matched_zone = self.is_at_demand_zone(current_price, zones, df)

        if matched_zone:
            # Calculate technical indicators
            indicators = self.calculate_technical_indicators(df)

            return {
                'ticker': ticker,
                'current_price': current_price,
                'zone': matched_zone,
                'all_zones': zones,
                'data': df,
                'indicators': indicators
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
