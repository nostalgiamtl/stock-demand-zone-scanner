"""
Simple technical indicators without pandas-ta (Python 3.14 compatible)
"""

import pandas as pd
import numpy as np


def calculate_rsi(series, period=14):
    """Calculate RSI indicator."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(series, fast=12, slow=26, signal=9):
    """Calculate MACD indicator."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist


def calculate_sma(series, period):
    """Calculate Simple Moving Average."""
    return series.rolling(window=period).mean()


def calculate_indicators(df):
    """
    Calculate all technical indicators.

    Args:
        df (pd.DataFrame): OHLCV data

    Returns:
        dict: Technical indicators
    """
    if df is None or len(df) < 50:
        return None

    try:
        # RSI
        rsi = calculate_rsi(df['Close'], 14)
        current_rsi = rsi.iloc[-1] if not rsi.empty else None

        # MACD
        macd, macd_signal, macd_hist = calculate_macd(df['Close'])
        current_macd = macd.iloc[-1] if not macd.empty else None
        current_macd_signal = macd_signal.iloc[-1] if not macd_signal.empty else None
        current_macd_hist = macd_hist.iloc[-1] if not macd_hist.empty else None

        # Moving Averages
        sma_50 = calculate_sma(df['Close'], 50)
        sma_200 = calculate_sma(df['Close'], 200)

        current_price = df['Close'].iloc[-1]
        ma_50 = sma_50.iloc[-1] if not sma_50.empty else None
        ma_200 = sma_200.iloc[-1] if not sma_200.empty and len(df) >= 200 else None

        # Volume Analysis
        avg_volume_20 = df['Volume'].rolling(window=20).mean().iloc[-1]
        current_volume = df['Volume'].iloc[-1]
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
        macd_trend = None
        if current_macd is not None and current_macd_signal is not None:
            if current_macd > current_macd_signal:
                macd_trend = "Bullish"
            else:
                macd_trend = "Bearish"

        return {
            'rsi': current_rsi,
            'rsi_signal': rsi_signal,
            'macd': current_macd,
            'macd_signal': current_macd_signal,
            'macd_histogram': current_macd_hist,
            'macd_trend': macd_trend,
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
