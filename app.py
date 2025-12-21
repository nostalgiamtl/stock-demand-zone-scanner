import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from stock_scanner import DemandZoneScanner
from utils import get_sp500_tickers, format_price, format_percent

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
    Create an interactive chart showing the stock price with demand zones marked.

    Args:
        result (dict): Scan result containing stock data and zones

    Returns:
        plotly figure
    """
    df = result['data']
    zones = result['all_zones']
    matched_zone = result['zone']

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

    # Add all demand zones as rectangles
    for idx, zone in enumerate(zones):
        is_matched = (zone['zone_low'] == matched_zone['zone_low'] and
                     zone['zone_high'] == matched_zone['zone_high'])

        color = 'rgba(0, 255, 0, 0.3)' if is_matched else 'rgba(100, 200, 255, 0.2)'

        fig.add_shape(
            type="rect",
            x0=zone['formed_date'],
            x1=df.index[-1],
            y0=zone['zone_low'],
            y1=zone['zone_high'],
            fillcolor=color,
            line=dict(color=color, width=1),
            row=1, col=1
        )

        # Add label for matched zone
        if is_matched:
            fig.add_annotation(
                x=df.index[-1],
                y=zone['zone_mid'],
                text=f"Active Zone: {format_price(zone['zone_low'])}-{format_price(zone['zone_high'])}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="green",
                ax=-100,
                ay=0,
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
    st.title("📈 Stock Demand Zone Scanner")
    st.markdown("""
    This tool scans S&P 500 stocks to find those trading at **multi-year demand zones** using weekly timeframe analysis.

    **What are demand zones?**
    Areas where the price consolidated before rallying significantly. When price returns to these zones,
    they often act as support levels for potential reversals.
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
            st.warning("No stocks found at demand zones with current settings. Try adjusting the parameters.")
            return

        # Display success message with timestamp
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✅ Found {len(results)} stocks at demand zones!")
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
            zone = result['zone']
            results_data.append({
                'Ticker': result['ticker'],
                'Current Price': result['current_price'],
                'Zone Low': zone['zone_low'],
                'Zone High': zone['zone_high'],
                'Distance from Zone (%)': abs(zone['distance_pct']),
                'Rally After Zone (%)': zone['rally_pct'],
                'Zone Strength (weeks)': zone['strength'],
                'Zone Formed': zone['formed_date'].strftime('%Y-%m-%d')
            })

        df_results = pd.DataFrame(results_data)

        # Sorting options
        col1, col2 = st.columns([2, 1])
        with col1:
            sort_by = st.selectbox(
                "Sort by",
                options=['Distance from Zone (%)', 'Rally After Zone (%)', 'Zone Strength (weeks)', 'Ticker'],
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
            file_name=f"demand_zone_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            help="Download the scan results as a CSV file for further analysis"
        )

        st.dataframe(
            df_results.style.format({
                'Current Price': '${:.2f}',
                'Zone Low': '${:.2f}',
                'Zone High': '${:.2f}',
                'Distance from Zone (%)': '{:.2f}%',
                'Rally After Zone (%)': '{:.2f}%',
                'Zone Strength (weeks)': '{:.0f}'
            }),
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

            # Display zone details
            zone = selected_result['zone']
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Current Price", format_price(selected_result['current_price']))
            with col2:
                st.metric("Zone Range", f"{format_price(zone['zone_low'])} - {format_price(zone['zone_high'])}")
            with col3:
                st.metric("Rally After Zone", format_percent(zone['rally_pct']))
            with col4:
                st.metric("Zone Strength", f"{zone['strength']} weeks")

            # Display chart
            fig = create_stock_chart(selected_result)
            st.plotly_chart(fig, use_container_width=True)

            # Zone information
            with st.expander("ℹ️ Zone Details"):
                st.write(f"**Zone Formation Date:** {zone['formed_date'].strftime('%Y-%m-%d')}")
                st.write(f"**Zone Price Range:** {format_price(zone['zone_low'])} - {format_price(zone['zone_high'])}")
                st.write(f"**Current Distance from Zone:** {format_percent(abs(zone['distance_pct']))}")
                st.write(f"**Rally Percentage After Formation:** {format_percent(zone['rally_pct'])}")
                st.write(f"**Consolidation Period:** {zone['strength']} weeks")

                if zone['distance_pct'] <= 0:
                    st.success("✅ Price is currently INSIDE the demand zone")
                else:
                    st.info("ℹ️ Price is near the demand zone (within tolerance)")


if __name__ == "__main__":
    main()
