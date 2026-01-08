import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from stock_scanner import DemandZoneScanner
from utils import get_sp500_tickers, format_price, format_percent
from discord_integration import (
    DiscordNotifier,
    detect_new_stocks,
    detect_price_alerts
)

st.set_page_config(page_title="Stock Demand Zone Scanner", layout="wide", page_icon="📈")


@st.cache_data(ttl=3600, show_spinner=False)
def cached_scan(lookback_years, zone_tolerance, cache_buster=None):
    """
    Cached version of the stock scan. Results are cached for 1 hour.

    Args:
        lookback_years (int): Number of years to look back
        zone_tolerance (float): Tolerance for zone matching
        cache_buster: Dummy parameter to force cache refresh

    Returns:
        tuple: (results, scan_timestamp)
    """
    scanner = DemandZoneScanner(
        lookback_years=lookback_years,
        zone_tolerance=zone_tolerance
    )

    tickers = get_sp500_tickers()

    if not tickers:
        return None, None

    results = scanner.scan_multiple_tickers(tickers)
    scan_timestamp = datetime.now()

    return results, scan_timestamp


def create_stock_chart(result):
    """
    Create an interactive chart showing the stock price with flipped resistance levels marked.

    Args:
        result (dict): Scan result containing stock data and levels

    Returns:
        plotly figure
    """
    df = result['data']
    levels = result['all_levels']
    matched_level = result['level']

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{result['ticker']} - Weekly Chart", "Volume")
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price'
        ),
        row=1, col=1
    )

    # Add all flipped levels as horizontal lines
    for idx, level_data in enumerate(levels):
        is_matched = (level_data['level'] == matched_level['level'])

        color = 'rgba(0, 255, 0, 0.8)' if is_matched else 'rgba(100, 200, 255, 0.5)'
        width = 2 if is_matched else 1

        # Draw horizontal line at the level
        fig.add_hline(
            y=level_data['level'],
            line_color=color,
            line_width=width,
            line_dash='dash' if not is_matched else 'solid',
            row=1, col=1
        )

        # Add label for matched level
        if is_matched:
            fig.add_annotation(
                x=df.index[-1],
                y=level_data['level'],
                text=f"Flipped Level: {format_price(level_data['level'])} ({level_data['resistance_tests']}x tested)",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="green",
                ax=-100,
                ay=-30,
                bgcolor="rgba(0, 255, 0, 0.8)",
                row=1, col=1
            )

    # Volume bars
    colors = ['red' if df['Close'].iloc[i] < df['Open'].iloc[i] else 'green'
              for i in range(len(df))]

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )

    fig.update_layout(
        title=f"{result['ticker']} - Current Price: {format_price(result['current_price'])}",
        xaxis_rangeslider_visible=False,
        height=600,
        showlegend=True,
        hovermode='x unified'
    )

    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig


def main():
    st.title("📈 Supply/Demand Flip Scanner")
    st.markdown("""
    This tool scans S&P 500 + NASDAQ stocks to find **resistance levels that flipped to support**.

    **What are flipped levels?**
    Price levels tested 3+ times as resistance (former supply), then broke above and flipped to become support (new demand).
    These are high-probability setups when price returns to test the flipped level.

    **Pure price action** - indicators are supplementary info only.
    """)

    # Sidebar configuration
    st.sidebar.header("⚙️ Scanner Configuration")

    lookback_years = st.sidebar.slider(
        "Lookback Period (years)",
        min_value=1,
        max_value=5,
        value=2,
        help="How far back to look for historical demand zones"
    )

    zone_tolerance = st.sidebar.slider(
        "Zone Tolerance (%)",
        min_value=1,
        max_value=10,
        value=3,
        help="How close the current price needs to be to a zone (% distance)"
    ) / 100

    min_rally = st.sidebar.slider(
        "Minimum Rally After Zone (%)",
        min_value=5,
        max_value=30,
        value=10,
        help="Minimum price increase after consolidation to qualify as demand zone"
    )

    st.sidebar.markdown("---")

    # Scan and refresh buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        scan_button = st.button("🔍 Start Scan", type="primary", use_container_width=True)
    with col2:
        refresh_button = st.button("🔄 Refresh", help="Clear cache and get fresh data", use_container_width=True)

    # Info about caching
    with st.sidebar.expander("ℹ️ How Updates Work"):
        st.markdown("""
        **Data Caching:**
        - Results are cached for 1 hour
        - Rescans within 1 hour are instant
        - Saves time and API calls

        **Fresh Data:**
        - Click 'Refresh' to clear cache
        - Then 'Start Scan' for latest data
        - Market data has ~15-20 min delay

        **Best Practice:**
        - Run scan once per hour max
        - Use CSV export to save results
        - Refresh only when market moves
        """)

    st.sidebar.markdown("---")

    # Discord Integration
    st.sidebar.header("🔔 Discord Notifications")

    # Check if webhook is configured in secrets
    discord_webhook = None
    webhook_from_secrets = False
    try:
        if hasattr(st, 'secrets') and 'discord' in st.secrets and 'webhook_url' in st.secrets['discord']:
            discord_webhook = st.secrets['discord']['webhook_url']
            webhook_from_secrets = True
            st.sidebar.success("✅ Webhook configured from secrets")
    except:
        pass

    # If no webhook in secrets, allow manual input
    if not webhook_from_secrets:
        enable_discord = st.sidebar.checkbox("Enable Discord Alerts", value=False)
        if enable_discord:
            discord_webhook = st.sidebar.text_input(
                "Discord Webhook URL",
                type="password",
                help="Paste your Discord webhook URL here"
            )
    else:
        enable_discord = True

    if enable_discord or webhook_from_secrets:
        st.sidebar.markdown("**Alert Types:**")
        alert_new_stocks = st.sidebar.checkbox("New stocks testing flipped levels", value=True)
        alert_price_signals = st.sidebar.checkbox("Price alerts (RSI/MACD)", value=False)

        if not webhook_from_secrets:
            with st.sidebar.expander("📘 How to get Webhook URL"):
                st.markdown("""
                1. Go to your Discord server
                2. Server Settings → Integrations
                3. Create Webhook
                4. Copy URL and paste above
                5. [Learn more](https://support.discord.com/hc/en-us/articles/228383668)
                """)
    else:
        alert_new_stocks = False
        alert_price_signals = False

    # Initialize cache buster in session state
    if 'cache_buster' not in st.session_state:
        st.session_state['cache_buster'] = 0

    # Handle refresh button
    if refresh_button:
        st.session_state['cache_buster'] += 1
        cached_scan.clear()
        st.sidebar.success("Cache cleared! Click 'Start Scan' for fresh data.")

    # Scan button
    if scan_button:
        st.session_state['scan_started'] = True
        st.session_state['results'] = None
        st.session_state['scan_timestamp'] = None

    # Initialize scanner
    if st.session_state.get('scan_started', False):
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("Starting scan... (This may take a few minutes for first scan)")

        try:
            # Use cached scan
            results, scan_timestamp = cached_scan(
                lookback_years=lookback_years,
                zone_tolerance=zone_tolerance,
                cache_buster=st.session_state.get('cache_buster', 0)
            )

            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()

            if results is None:
                st.error("Failed to fetch S&P 500 tickers. Please check your internet connection.")
                st.session_state['scan_started'] = False
                return

            st.session_state['results'] = results
            st.session_state['scan_timestamp'] = scan_timestamp
            st.session_state['scan_started'] = False

            # Discord notifications
            if enable_discord and discord_webhook and results:
                notifier = DiscordNotifier(discord_webhook)

                # Detect new stocks
                if alert_new_stocks:
                    new_stocks = detect_new_stocks(results)
                    if new_stocks:
                        success = notifier.send_new_stocks_alert(new_stocks, scan_timestamp)
                        if success:
                            st.sidebar.success(f"🔔 Sent {len(new_stocks)} new stock(s) to Discord!")

                # Price alerts (disabled by default to prevent spam)
                if alert_price_signals:
                    alerts = detect_price_alerts(results)
                    # Only send top 3 alerts to prevent spam
                    alerts_to_send = alerts[:3] if len(alerts) > 5 else alerts
                    for ticker, alert_type, details in alerts_to_send:
                        notifier.send_price_alert(ticker, alert_type, details)
                    if alerts:
                        remaining = len(alerts) - len(alerts_to_send)
                        msg = f"⚠️ Sent {len(alerts_to_send)} price alert(s)"
                        if remaining > 0:
                            msg += f" ({remaining} more not sent)"
                        st.sidebar.info(msg)

        except Exception as e:
            st.error(f"Error during scan: {str(e)}")
            progress_bar.empty()
            status_text.empty()
            st.session_state['scan_started'] = False
            return

    # Display results
    if st.session_state.get('results') is not None:
        results = st.session_state['results']
        scan_timestamp = st.session_state.get('scan_timestamp')

        if not results:
            st.warning("No stocks found testing flipped levels with current settings. Try adjusting the parameters.")
            return

        # Display success message with timestamp
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✅ Found {len(results)} stocks testing flipped resistance levels!")
        with col2:
            if scan_timestamp:
                time_ago = datetime.now() - scan_timestamp
                minutes_ago = int(time_ago.total_seconds() / 60)
                if minutes_ago < 1:
                    st.info("📅 Just now")
                elif minutes_ago < 60:
                    st.info(f"📅 {minutes_ago} min ago")
                else:
                    hours_ago = int(minutes_ago / 60)
                    st.info(f"📅 {hours_ago}h ago")

        # Create results dataframe
        results_data = []
        for result in results:
            level = result['level']
            indicators = result.get('indicators', {})

            row_data = {
                'Ticker': result['ticker'],
                'Current Price': result['current_price'],
                'Flipped Level': level['level'],
                'Resistance Tests': level['resistance_tests'],
                'Distance (%)': abs(level['distance_pct']),
                'Breakout Date': level['breakout_date'],
                'Level Strength': level['strength'],
                'Last Resistance': level['last_resistance_date']
            }

            # Add technical indicators if available
            if indicators:
                row_data['RSI'] = indicators.get('rsi')
                row_data['RSI Signal'] = indicators.get('rsi_signal', 'N/A')
                row_data['MACD'] = indicators.get('macd_trend', 'N/A')
                row_data['Above MA50'] = '✓' if indicators.get('above_ma50') else '✗'
                row_data['Above MA200'] = '✓' if indicators.get('above_ma200') else '✗'
                row_data['Vol Ratio'] = indicators.get('volume_ratio', 1)

            results_data.append(row_data)

        df_results = pd.DataFrame(results_data)

        # Sorting options
        col1, col2 = st.columns([2, 1])
        with col1:
            sort_options = ['Distance (%)', 'Resistance Tests', 'Level Strength', 'RSI', 'Vol Ratio', 'Ticker']
            # Filter out options not in dataframe
            available_options = [opt for opt in sort_options if opt in df_results.columns]
            sort_by = st.selectbox(
                "Sort by",
                options=available_options,
                index=0
            )
        with col2:
            ascending = st.checkbox("Ascending", value=True)

        df_results = df_results.sort_values(by=sort_by, ascending=ascending)

        # Display summary table
        st.subheader("📊 Results Summary")

        # CSV export button
        csv_data = df_results.to_csv(index=False)
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv_data,
            file_name=f"resistance_flip_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download the scan results as a CSV file for further analysis"
        )

        # Format dataframe
        format_dict = {
            'Current Price': '${:.2f}',
            'Flipped Level': '${:.2f}',
            'Resistance Tests': '{:.0f}',
            'Distance (%)': '{:.2f}%',
            'Level Strength': '{:.0f}',
        }

        # Add RSI and Vol Ratio formatting if present
        if 'RSI' in df_results.columns:
            format_dict['RSI'] = '{:.1f}'
        if 'Vol Ratio' in df_results.columns:
            format_dict['Vol Ratio'] = '{:.2f}x'

        st.dataframe(
            df_results.style.format(format_dict),
            use_container_width=True,
            height=400
        )

        # Individual stock charts
        st.subheader("📈 Individual Stock Charts")

        selected_ticker = st.selectbox(
            "Select a stock to view detailed chart",
            options=[r['ticker'] for r in results]
        )

        if selected_ticker:
            selected_result = next(r for r in results if r['ticker'] == selected_ticker)

            # Display level details
            level = selected_result['level']
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Current Price", format_price(selected_result['current_price']))
            with col2:
                st.metric("Flipped Level", format_price(level['level']))
            with col3:
                st.metric("Resistance Tests", f"{level['resistance_tests']}x")
            with col4:
                st.metric("Distance", format_percent(level['distance_pct']))

            # Display chart
            fig = create_stock_chart(selected_result)
            st.plotly_chart(fig, use_container_width=True)

            # Level information
            col1, col2 = st.columns(2)

            with col1:
                with st.expander("ℹ️ Level Details"):
                    st.write(f"**Flipped Level Price:** {format_price(level['level'])}")
                    st.write(f"**Times Tested as Resistance:** {level['resistance_tests']}")
                    st.write(f"**Resistance Test Dates:** {', '.join(level['resistance_dates'])}")
                    st.write(f"**Last Resistance Test:** {level['last_resistance_date']}")
                    st.write(f"**Breakout Date:** {level['breakout_date']}")
                    st.write(f"**Support Test Date:** {level['support_test_date']}")
                    st.write(f"**Current Distance from Level:** {format_percent(level['distance_pct'])}")

                    if abs(level['distance_pct']) <= 2:
                        st.success("✅ Price is AT the flipped level (within 2%)")
                    else:
                        st.info(f"ℹ️ Price is {level['distance_pct']:.1f}% from the level")

            with col2:
                indicators = selected_result.get('indicators', {})
                if indicators:
                    with st.expander("📊 Technical Indicators"):
                        st.write(f"**RSI:** {indicators.get('rsi', 'N/A'):.1f}" if indicators.get('rsi') else "**RSI:** N/A")
                        if indicators.get('rsi_signal'):
                            rsi_color = "🔴" if indicators['rsi_signal'] == "Overbought" else "🟢" if indicators['rsi_signal'] == "Oversold" else "🟡"
                            st.write(f"{rsi_color} {indicators['rsi_signal']}")

                        st.write(f"**MACD Trend:** {indicators.get('macd_trend', 'N/A')}")

                        if indicators.get('ma_50'):
                            st.write(f"**50-Week MA:** {format_price(indicators['ma_50'])}")
                            st.write(f"  {'✅ Above' if indicators.get('above_ma50') else '⬇️ Below'}")

                        if indicators.get('ma_200'):
                            st.write(f"**200-Week MA:** {format_price(indicators['ma_200'])}")
                            st.write(f"  {'✅ Above' if indicators.get('above_ma200') else '⬇️ Below'}")

                        if indicators.get('volume_ratio'):
                            vol_ratio = indicators['volume_ratio']
                            vol_emoji = "🔥" if vol_ratio > 2 else "📊"
                            st.write(f"**Volume Ratio:** {vol_emoji} {vol_ratio:.2f}x")


if __name__ == "__main__":
    main()
