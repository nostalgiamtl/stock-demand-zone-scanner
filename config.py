"""
Configuration file for the Stock Demand Zone Scanner.
Modify these parameters to customize the scanner behavior.
"""

# ==============================================================================
# DEMAND ZONE DETECTION PARAMETERS
# ==============================================================================

# Minimum number of consecutive weeks of consolidation to form a demand zone
MIN_CONSOLIDATION_WEEKS = 3

# Maximum weekly range (%) during consolidation period
# Lower value = tighter consolidation required
MAX_CONSOLIDATION_RANGE_PCT = 5.0

# Minimum rally percentage after consolidation to qualify as demand zone
# Higher value = stronger zones only
MIN_RALLY_PCT = 10.0

# Maximum number of weeks to look ahead for rally after consolidation
RALLY_LOOKHEAD_WEEKS = 10

# ==============================================================================
# SCANNER SETTINGS
# ==============================================================================

# Default lookback period in years for historical data
DEFAULT_LOOKBACK_YEARS = 2

# Default tolerance for being "at" a demand zone (as decimal, e.g., 0.03 = 3%)
DEFAULT_ZONE_TOLERANCE = 0.03

# ==============================================================================
# DATA FETCHING
# ==============================================================================

# Timeout for fetching stock data (seconds)
DATA_FETCH_TIMEOUT = 10

# Retry attempts if data fetch fails
DATA_FETCH_RETRIES = 2

# ==============================================================================
# UI SETTINGS
# ==============================================================================

# Default sorting column in results table
DEFAULT_SORT_COLUMN = 'Distance from Zone (%)'

# Default sorting order
DEFAULT_SORT_ASCENDING = True

# Number of rows to display in results table
RESULTS_TABLE_HEIGHT = 400

# Chart height in pixels
CHART_HEIGHT = 600

# ==============================================================================
# ADVANCED SETTINGS
# ==============================================================================

# Minimum number of data points required for analysis
MIN_DATA_POINTS = 20

# Demand zone visual colors
MATCHED_ZONE_COLOR = 'rgba(0, 255, 0, 0.3)'  # Green for active zone
OTHER_ZONE_COLOR = 'rgba(100, 200, 255, 0.2)'  # Blue for other zones

# Volume bar colors
VOLUME_UP_COLOR = 'green'
VOLUME_DOWN_COLOR = 'red'
