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


class SupplyDemandFlipScanner:
    def __init__(self, lookback_years=2, level_tolerance=0.02, min_tests=3):
        """
        Initialize the supply/demand flip scanner.

        Finds levels that were tested multiple times as resistance (former supply),
        then broke above and flipped to become support (new demand).

        Args:
            lookback_years (int): Number of years to look back for historical data
            level_tolerance (float): Price tolerance for identifying same level (2% default)
            min_tests (int): Minimum number of resistance tests required (3 default)
        """
        self.lookback_years = lookback_years
        self.level_tolerance = level_tolerance
        self.min_tests = min_tests

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

    def find_swing_highs(self, df, order=5):
        """
        Find swing high points in price data.

        A swing high is a local maximum where the high is higher than
        'order' bars on both sides.

        Args:
            df (pd.DataFrame): OHLCV data
            order (int): Number of bars on each side to compare

        Returns:
            list: Indices of swing highs
        """
        highs = df['High'].values
        swing_high_indices = argrelextrema(highs, np.greater, order=order)[0]
        return swing_high_indices

    def cluster_levels(self, prices, indices, dates, tolerance):
        """
        Cluster nearby price levels into zones.

        Groups prices that are within tolerance % of each other.

        Args:
            prices (array): Array of price values
            indices (array): Array of indices in original dataframe
            dates (array): Array of dates corresponding to prices
            tolerance (float): Price tolerance for clustering (e.g., 0.02 for 2%)

        Returns:
            list: List of level dictionaries with touches
        """
        if len(prices) == 0:
            return []

        levels = []
        used = set()

        for i in range(len(prices)):
            if i in used:
                continue

            level_price = prices[i]
            touches = [{
                'price': prices[i],
                'index': indices[i],
                'date': dates[i]
            }]
            used.add(i)

            # Find all prices within tolerance of this level
            for j in range(i + 1, len(prices)):
                if j in used:
                    continue

                price_diff_pct = abs(prices[j] - level_price) / level_price

                if price_diff_pct <= tolerance:
                    touches.append({
                        'price': prices[j],
                        'index': indices[j],
                        'date': dates[j]
                    })
                    used.add(j)
                    # Update level price to average
                    level_price = np.mean([t['price'] for t in touches])

            if len(touches) >= 1:
                levels.append({
                    'level': level_price,
                    'touches': touches,
                    'count': len(touches)
                })

        return levels

    def identify_resistance_flips(self, df):
        """
        Identify resistance levels that flipped to support.

        Process:
        1. Find levels tested 3+ times as resistance (rejection points)
        2. Verify price broke above the level
        3. Verify price came back and bounced off it as support
        4. Return valid flipped levels

        Args:
            df (pd.DataFrame): Weekly OHLCV data

        Returns:
            list: List of dictionaries containing flipped level information
        """
        if df is None or len(df) < 30:  # Need enough data
            return []

        # Find swing highs (resistance test points)
        swing_high_indices = self.find_swing_highs(df, order=3)

        if len(swing_high_indices) < self.min_tests:
            return []

        # Get prices and dates at swing highs
        swing_prices = df.iloc[swing_high_indices]['High'].values
        swing_dates = df.iloc[swing_high_indices].index.values

        # Cluster swing highs into resistance levels
        resistance_levels = self.cluster_levels(
            swing_prices,
            swing_high_indices,
            swing_dates,
            self.level_tolerance
        )

        # Filter for levels with minimum tests
        resistance_levels = [l for l in resistance_levels if l['count'] >= self.min_tests]

        flipped_levels = []

        for level_data in resistance_levels:
            level = level_data['level']
            touches = level_data['touches']

            # Get index of last resistance test
            last_test_idx = max([t['index'] for t in touches])
            last_test_date = df.index[last_test_idx]

            # Check if price broke above this level after the tests
            remaining_data = df.iloc[last_test_idx + 1:]

            if len(remaining_data) < 5:  # Need data after breakout
                continue

            # Look for breakout (close above resistance)
            breakout_found = False
            breakout_idx = None

            for i, (idx, row) in enumerate(remaining_data.iterrows()):
                if row['Close'] > level * 1.02:  # Closed 2% above level
                    breakout_found = True
                    breakout_idx = last_test_idx + 1 + i
                    breakout_date = idx
                    break

            if not breakout_found:
                continue

            # Check if price came back to test as support
            data_after_breakout = df.iloc[breakout_idx + 1:]

            if len(data_after_breakout) < 2:
                continue

            # Look for price returning to level and bouncing (support test)
            support_test_found = False
            support_test_date = None
            support_bounce_pct = 0

            for i, (idx, row) in enumerate(data_after_breakout.iterrows()):
                # Check if low came near the level (within tolerance)
                if row['Low'] <= level * (1 + self.level_tolerance * 1.5):
                    # Check if price bounced from here (didn't break below)
                    if row['Close'] > level * 0.98:  # Closed above level
                        support_test_found = True
                        support_test_date = idx

                        # Calculate bounce strength
                        future_data = data_after_breakout.iloc[i:i+5]
                        if len(future_data) > 0:
                            high_after = future_data['High'].max()
                            support_bounce_pct = ((high_after - level) / level) * 100

                        break

            if support_test_found:
                # Calculate weeks between formation and now
                weeks_old = (df.index[-1] - last_test_date).days / 7

                flipped_level = {
                    'level': level,
                    'resistance_tests': len(touches),
                    'resistance_dates': [str(t['date'])[:10] for t in touches],
                    'last_resistance_date': str(last_test_date)[:10],
                    'breakout_date': str(breakout_date)[:10],
                    'support_test_date': str(support_test_date)[:10] if support_test_date else None,
                    'support_bounce_pct': support_bounce_pct,
                    'weeks_old': round(weeks_old, 1),
                    'strength': len(touches)  # More tests = stronger level
                }

                flipped_levels.append(flipped_level)

        return flipped_levels

    def is_currently_testing_flipped_level(self, current_price, flipped_levels):
        """
        Check if current price is testing a flipped resistance-to-support level.

        Looking for:
        - Price is at or near the flipped level (within tolerance)
        - Level has proven itself (multiple resistance tests + successful flip)

        Args:
            current_price (float): Current stock price
            flipped_levels (list): List of flipped resistance levels

        Returns:
            dict: Information about the matched level or None
        """
        if not flipped_levels:
            return None

        for level_data in flipped_levels:
            level = level_data['level']

            # Check if current price is at/near the level
            # Allow ±2% for at the level, up to +5% for bouncing from it
            lower_bound = level * (1 - self.level_tolerance)
            upper_bound = level * (1 + 0.05)  # 5% above for already bouncing

            if lower_bound <= current_price <= upper_bound:
                # Calculate distance from level
                distance_pct = ((current_price - level) / level) * 100

                return {
                    **level_data,
                    'current_price': current_price,
                    'distance_pct': round(distance_pct, 2)
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
        Scan a single ticker for resistance levels that flipped to support.

        Process:
        1. Find levels tested 3+ times as resistance
        2. Verify they broke above and flipped to support
        3. Check if current price is testing the flipped level
        4. Add technical indicators as supplementary info

        Args:
            ticker (str): Stock ticker symbol

        Returns:
            dict: Scan results or None if no matches found
        """
        df = self.fetch_weekly_data(ticker)

        if df is None or df.empty:
            return None

        # Find resistance levels that flipped to support
        flipped_levels = self.identify_resistance_flips(df)

        if not flipped_levels:
            return None

        current_price = df['Close'].iloc[-1]

        # Check if current price is testing any flipped level
        matched_level = self.is_currently_testing_flipped_level(current_price, flipped_levels)

        if matched_level:
            # Calculate technical indicators (supplementary info)
            indicators = self.calculate_technical_indicators(df)

            return {
                'ticker': ticker,
                'current_price': current_price,
                'level': matched_level,  # Changed from 'zone' to 'level'
                'all_levels': flipped_levels,  # All flipped levels found
                'data': df,
                'indicators': indicators
            }

        return None

    def scan_multiple_tickers(self, tickers, progress_callback=None):
        """
        Scan multiple tickers for resistance-to-support flips.

        Args:
            tickers (list): List of ticker symbols
            progress_callback (callable): Optional callback for progress updates

        Returns:
            list: List of stocks testing flipped resistance levels
        """
        results = []

        for idx, ticker in enumerate(tickers):
            if progress_callback:
                progress_callback(idx + 1, len(tickers), ticker)

            result = self.scan_ticker(ticker)
            if result:
                results.append(result)

        return results


# Backward compatibility alias
DemandZoneScanner = SupplyDemandFlipScanner
