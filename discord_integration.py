"""
Discord webhook integration for sending stock scan notifications.
"""

from discord_webhook import DiscordWebhook, DiscordEmbed
from datetime import datetime
import json
import os


class DiscordNotifier:
    def __init__(self, webhook_url):
        """
        Initialize Discord notifier.

        Args:
            webhook_url (str): Discord webhook URL
        """
        self.webhook_url = webhook_url

    def send_new_stocks_alert(self, new_stocks, scan_timestamp=None):
        """
        Send alerts for new stocks entering demand zones.
        Sends two separate notifications:
        1. Top 3 stocks with Bullish MACD
        2. Top 3 stocks with Bearish MACD

        Args:
            new_stocks (list): List of new stock results
            scan_timestamp (datetime): When the scan was performed

        Returns:
            bool: Success status
        """
        if not self.webhook_url or not new_stocks:
            return False

        try:
            total_stocks = len(new_stocks)

            # Split stocks by MACD trend
            bullish_stocks = [s for s in new_stocks if s.get('indicators', {}).get('macd_trend') == 'Bullish']
            bearish_stocks = [s for s in new_stocks if s.get('indicators', {}).get('macd_trend') == 'Bearish']
            neutral_stocks = [s for s in new_stocks if s.get('indicators', {}).get('macd_trend') not in ['Bullish', 'Bearish']]

            # Debug logging
            print(f"Discord notification breakdown:")
            print(f"  Total new stocks: {total_stocks}")
            print(f"  Bullish MACD: {len(bullish_stocks)}")
            print(f"  Bearish MACD: {len(bearish_stocks)}")
            print(f"  Neutral/No MACD: {len(neutral_stocks)}")
            if bullish_stocks:
                print(f"  Bullish tickers: {[s['ticker'] for s in bullish_stocks]}")
            if bearish_stocks:
                print(f"  Bearish tickers: {[s['ticker'] for s in bearish_stocks]}")

            # Sort each group by best opportunities (oversold first, then lowest RSI)
            def sort_by_rsi(stocks):
                return sorted(stocks, key=lambda x: (
                    x.get('indicators', {}).get('rsi_signal') != 'Oversold',
                    x.get('indicators', {}).get('rsi', 50)
                ))

            bullish_sorted = sort_by_rsi(bullish_stocks)
            bearish_sorted = sort_by_rsi(bearish_stocks)
            neutral_sorted = sort_by_rsi(neutral_stocks)

            # Send bullish MACD notification (top 3)
            if bullish_sorted:
                self._send_macd_group_alert(
                    bullish_sorted[:3],
                    "Bullish",
                    len(bullish_sorted),
                    total_stocks,
                    scan_timestamp
                )

            # Send bearish MACD notification (top 3)
            if bearish_sorted:
                self._send_macd_group_alert(
                    bearish_sorted[:3],
                    "Bearish",
                    len(bearish_sorted),
                    total_stocks,
                    scan_timestamp
                )

            # If there are neutral stocks and no other groups, send them
            if neutral_sorted and not bullish_sorted and not bearish_sorted:
                self._send_macd_group_alert(
                    neutral_sorted[:3],
                    "Neutral",
                    len(neutral_sorted),
                    total_stocks,
                    scan_timestamp
                )

            return True

        except Exception as e:
            print(f"Error sending Discord notification: {e}")
            return False

    def _send_macd_group_alert(self, stocks, macd_type, group_total, overall_total, scan_timestamp=None):
        """
        Send a Discord alert for a specific MACD group.

        Args:
            stocks (list): Stocks to show (already limited to top 3)
            macd_type (str): "Bullish", "Bearish", or "Neutral"
            group_total (int): Total stocks in this MACD group
            overall_total (int): Total new stocks across all groups
            scan_timestamp (datetime): When the scan was performed
        """
        try:
            webhook = DiscordWebhook(url=self.webhook_url)

            # Set color and emoji based on MACD type
            if macd_type == "Bullish":
                color = 0x00ff00  # Green
                emoji = "📈"
                title = f"{emoji} New Stocks at Support - BULLISH MACD"
            elif macd_type == "Bearish":
                color = 0xff6600  # Orange
                emoji = "📉"
                title = f"{emoji} New Stocks at Support - BEARISH MACD"
            else:
                color = 0xffaa00  # Yellow
                emoji = "➡️"
                title = f"{emoji} New Stocks at Support - NEUTRAL MACD"

            description = f"**{group_total}** stock(s) with {macd_type} MACD at proven support\n"
            description += f"Showing top **{len(stocks)}** opportunities"
            if overall_total > group_total:
                description += f"\n\n*({overall_total} total new stocks across all MACD signals)*"

            embed = DiscordEmbed(
                title=title,
                description=description,
                color=color
            )

            if scan_timestamp:
                embed.set_timestamp(scan_timestamp.timestamp())

            # Add each stock as a field
            for stock in stocks:
                ticker = stock['ticker']
                current_price = stock['current_price']
                zone = stock['zone']
                indicators = stock.get('indicators', {})

                # Build field value with indicators
                field_value = f"**Price:** ${current_price:.2f}\n"
                field_value += f"**Zone:** ${zone['zone_low']:.2f} - ${zone['zone_high']:.2f}\n"
                field_value += f"**Rally:** {zone['rally_pct']:.1f}%\n"

                if indicators:
                    if indicators.get('rsi'):
                        rsi_emoji = "🟢" if indicators.get('rsi_signal') == 'Oversold' else "🟡"
                        field_value += f"{rsi_emoji} **RSI:** {indicators['rsi']:.1f} ({indicators.get('rsi_signal', 'N/A')})\n"
                    if indicators.get('macd_trend'):
                        macd_emoji = "📈" if indicators['macd_trend'] == 'Bullish' else "📉"
                        field_value += f"{macd_emoji} **MACD:** {indicators['macd_trend']}\n"
                    if indicators.get('volume_ratio', 0) > 2:
                        field_value += f"🔥 **Volume:** {indicators['volume_ratio']:.1f}x avg\n"

                embed.add_embed_field(
                    name=f"📊 {ticker}",
                    value=field_value,
                    inline=True
                )

            # Add footer
            remaining = group_total - len(stocks)
            if remaining > 0:
                footer_text = f"Stock Scanner • {remaining} more {macd_type.lower()} stocks not shown"
            else:
                footer_text = "Stock Demand Zone Scanner"

            embed.set_footer(text=footer_text)

            webhook.add_embed(embed)
            response = webhook.execute()

            return response.status_code == 200

        except Exception as e:
            print(f"Error sending {macd_type} MACD alert: {e}")
            return False

    def send_price_alert(self, ticker, alert_type, details):
        """
        Send price alert for a specific stock.

        Args:
            ticker (str): Stock ticker
            alert_type (str): Type of alert (e.g., "Zone Break", "Strong RSI")
            details (dict): Alert details

        Returns:
            bool: Success status
        """
        if not self.webhook_url:
            return False

        try:
            webhook = DiscordWebhook(url=self.webhook_url)

            color = 0xff0000 if "break" in alert_type.lower() else 0xffaa00

            embed = DiscordEmbed(
                title=f"⚠️ Price Alert: {ticker}",
                description=alert_type,
                color=color
            )

            for key, value in details.items():
                embed.add_embed_field(
                    name=key,
                    value=str(value),
                    inline=True
                )

            embed.set_timestamp()
            embed.set_footer(text="Stock Demand Zone Scanner")

            webhook.add_embed(embed)
            response = webhook.execute()

            return response.status_code == 200

        except Exception as e:
            print(f"Error sending price alert: {e}")
            return False

    def send_daily_summary(self, all_stocks, scan_timestamp=None):
        """
        Send daily summary of all stocks at demand zones.

        Args:
            all_stocks (list): All stocks at demand zones
            scan_timestamp (datetime): When scan was performed

        Returns:
            bool: Success status
        """
        if not self.webhook_url:
            return False

        try:
            webhook = DiscordWebhook(url=self.webhook_url)

            embed = DiscordEmbed(
                title="📈 Daily Demand Zone Summary",
                description=f"**{len(all_stocks)}** stocks currently at demand zones",
                color=0x0099ff
            )

            if scan_timestamp:
                embed.set_timestamp(scan_timestamp.timestamp())

            # Summary stats
            if all_stocks:
                avg_rsi = sum(s.get('indicators', {}).get('rsi', 0) or 0 for s in all_stocks) / len(all_stocks)
                oversold_count = sum(1 for s in all_stocks if s.get('indicators', {}).get('rsi_signal') == 'Oversold')
                bullish_macd = sum(1 for s in all_stocks if s.get('indicators', {}).get('macd_trend') == 'Bullish')

                embed.add_embed_field(name="📊 Avg RSI", value=f"{avg_rsi:.1f}", inline=True)
                embed.add_embed_field(name="🔻 Oversold", value=f"{oversold_count}", inline=True)
                embed.add_embed_field(name="📈 Bullish MACD", value=f"{bullish_macd}", inline=True)

            # List top 5 stocks
            embed.add_embed_field(
                name="🔝 Top Stocks",
                value="\n".join([f"• {s['ticker']}: ${s['current_price']:.2f}" for s in all_stocks[:5]]),
                inline=False
            )

            embed.set_footer(text="Stock Demand Zone Scanner")

            webhook.add_embed(embed)
            response = webhook.execute()

            return response.status_code == 200

        except Exception as e:
            print(f"Error sending daily summary: {e}")
            return False


def load_previous_scan():
    """Load previous scan results from file."""
    try:
        if os.path.exists('last_scan.json'):
            with open('last_scan.json', 'r') as f:
                data = json.load(f)
                return set(data.get('tickers', []))
        return set()
    except Exception as e:
        print(f"Error loading previous scan: {e}")
        return set()


def save_current_scan(tickers):
    """Save current scan results to file."""
    try:
        data = {
            'tickers': list(tickers),
            'timestamp': datetime.now().isoformat()
        }
        with open('last_scan.json', 'w') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print(f"Error saving current scan: {e}")
        return False


def detect_new_stocks(current_results):
    """
    Detect new stocks that weren't in the previous scan.

    Args:
        current_results (list): Current scan results

    Returns:
        list: New stocks not in previous scan
    """
    current_tickers = {r['ticker'] for r in current_results}
    previous_tickers = load_previous_scan()

    new_tickers = current_tickers - previous_tickers
    new_stocks = [r for r in current_results if r['ticker'] in new_tickers]

    # Save current scan
    save_current_scan(current_tickers)

    return new_stocks


def detect_price_alerts(results):
    """
    Detect price alerts based on technical indicators.

    Args:
        results (list): Scan results with indicators

    Returns:
        list: List of (ticker, alert_type, details) tuples
    """
    alerts = []

    for result in results:
        ticker = result['ticker']
        indicators = result.get('indicators', {})

        if not indicators:
            continue

        # RSI Oversold alert
        if indicators.get('rsi') and indicators['rsi'] < 30:
            alerts.append((
                ticker,
                "Strong Oversold Signal",
                {
                    "RSI": f"{indicators['rsi']:.1f}",
                    "Price": f"${result['current_price']:.2f}",
                    "Zone": f"${result['zone']['zone_low']:.2f} - ${result['zone']['zone_high']:.2f}"
                }
            ))

        # Bullish MACD with oversold RSI
        if (indicators.get('macd_trend') == 'Bullish' and
            indicators.get('rsi') and indicators['rsi'] < 40):
            alerts.append((
                ticker,
                "Bullish MACD + Low RSI",
                {
                    "RSI": f"{indicators['rsi']:.1f}",
                    "MACD": indicators['macd_trend'],
                    "Price": f"${result['current_price']:.2f}"
                }
            ))

        # High volume alert
        volume_ratio = indicators.get('volume_ratio', 1)
        if volume_ratio > 2:
            alerts.append((
                ticker,
                "High Volume Spike",
                {
                    "Volume Ratio": f"{volume_ratio:.1f}x average",
                    "Price": f"${result['current_price']:.2f}"
                }
            ))

    return alerts
