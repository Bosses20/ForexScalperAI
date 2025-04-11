# Mobile Trading App UI/UX Design

## 1. Design Philosophy

The mobile trading app UI/UX is designed around these core principles:

1. **Clarity** - Information should be presented clearly and concisely, with the most important data immediately visible
2. **Efficiency** - Users should be able to monitor and control their trading bot with minimal taps
3. **Consistency** - Interface elements should be consistent throughout the app
4. **Professional** - The UI should convey professionalism and reliability, inspiring confidence
5. **Adaptability** - The design should adapt to different market conditions and asset types

## 2. Color Scheme

The app will use a dark theme primary color scheme optimized for:
- Reducing eye strain during extended market monitoring
- Emphasizing important data through strategic use of accent colors
- Clearly distinguishing between different market states

**Primary Colors:**
- Background: #121212 (Dark Gray)
- Surface: #1E1E1E (Slightly Lighter Gray)
- Primary: #1565C0 (Deep Blue)
- Secondary: #651FFF (Purple)

**Accent Colors:**
- Positive/Bullish: #00C853 (Green)
- Negative/Bearish: #FF3D00 (Red)
- Warning: #FFD600 (Yellow)
- Neutral: #90A4AE (Gray-Blue)

**Text Colors:**
- Primary Text: #FFFFFF (White)
- Secondary Text: #B0BEC5 (Light Gray)
- Disabled Text: #757575 (Medium Gray)

## 3. Typography

- **Primary Font**: Roboto
- **Monospace Font** (for numerical data): Roboto Mono
- **Font Sizes**:
  - Heading 1: 24sp
  - Heading 2: 20sp
  - Body Text: 16sp
  - Caption: 14sp
  - Small Text: 12sp
- **Line Heights**:
  - Headings: 1.2x
  - Body Text: 1.5x

## 4. User Flow

### Authentication Flow
1. Splash Screen
2. Welcome/Login Screen
   - MT5 credential fields (account, password, server)
   - "Connect" button
3. Connection Setup
   - Automatic discovery of PC backend
   - Manual IP/hostname entry option
4. Dashboard (main screen)

### Main Navigation
- Bottom navigation bar with:
  - Dashboard (main view)
  - Trading (trading controls and history)
  - Market (market conditions and analysis)
  - Assets (multi-asset management)
  - Settings (app configuration)

## 5. Screen Designs

### 5.1 Authentication Screen

**Design Elements:**
- MT5-style login form with:
  - Account field (numeric keyboard)
  - Password field (secure entry)
  - Server field with dropdown of common brokers
  - Remember credentials toggle
  - Connect button
- Background with subtle trading chart pattern
- Logo and app name at top

**Behavior:**
- Validate credential format before submission
- Show spinner during authentication
- Transition to server discovery on successful authentication
- Display clear error messages for authentication failures

### 5.2 Dashboard Screen

**Design Elements:**
- Status Card
  - Bot status indicator (Running/Stopped)
  - Quick action buttons (Start/Stop)
  - Uptime counter
  - Connected account info
- Performance Summary Card
  - Daily P&L with percentage
  - Current drawdown
  - Open positions count
  - Total trades today
- Market Condition Card
  - Visual indicator of current market state (bullish, bearish, ranging, choppy)
  - Volatility meter
  - Trading favorability score with confidence indicator
  - Quick toggle for enabling/disabling trading
- Active Assets Card
  - List of currently active trading instruments
  - Mini sparkline for each showing recent performance
  - Quick toggle to enable/disable each instrument
- Recent Trades Card
  - Scrollable list of most recent 5 trades
  - Instrument, direction, profit/loss for each
  - "View All" button

**Behavior:**
- Real-time updates via WebSocket
- Pull-to-refresh for manual updates
- Tap on any card to navigate to detailed view
- Animated transitions between data updates

### 5.3 Trading Screen

**Design Elements:**
- Trading Controls Card
  - Risk level slider (1-10)
  - Trading mode selection (Conservative, Balanced, Aggressive)
  - Emergency stop button
- Open Positions Card
  - List of all open positions
  - Details: instrument, entry price, current price, P&L
  - Swipe actions to modify or close positions
- Trade History Tab
  - Filterable list of closed trades
  - Daily, weekly, monthly grouping options
  - Performance metrics for selected period
- Performance Charts Tab
  - Equity curve
  - Win/loss ratio
  - Instrument performance comparison

**Behavior:**
- Confirm actions for risk adjustments
- Visual feedback for trading mode changes
- Real-time position updates
- Swipe between tabs for history and charts

### 5.4 Market Conditions Screen

**Design Elements:**
- Market Overview Card
  - Overall market trend visualization
  - Current session indicator (Asian, European, American)
  - Market strength meter
  - Key levels indicator
- Volatility Analysis Card
  - Volatility heat map by instrument
  - Historical volatility chart
  - Volatility forecast
- Market Correlation Matrix
  - Visual correlation heat map
  - Filter by instrument groups
  - Highlight strong correlations
- Strategy Recommendation Card
  - List of optimal strategies for current conditions
  - Confidence score for each
  - Quick apply button for recommended settings

**Behavior:**
- Detailed drill-down on tapping any metric
- Real-time updates of market conditions
- Notifications for significant market changes
- Interactive correlation matrix

### 5.5 Multi-Asset Management Screen

**Design Elements:**
- Asset Overview Card
  - Grid of all available instruments
  - Activity status indicator
  - Performance rating
  - Asset type icon (Forex, Synthetic)
- Portfolio Allocation Chart
  - Pie chart of current exposure by instrument
  - Risk-adjusted allocation view
  - Rebalance suggestions
- Session Schedule Card
  - Timeline of trading sessions
  - Active periods for each instrument
  - Session overlap indicators
- Strategy Assignment Card
  - Matrix of instruments vs. strategies
  - Strength adjustment sliders
  - Auto-optimize button

**Behavior:**
- Drag-and-drop portfolio rebalancing
- Tap to toggle instrument activity
- Long-press for detailed instrument settings
- Interactive session timeline

### 5.6 Settings Screen

**Design Elements:**
- Connection Settings Section
  - Server address/discovery settings
  - Connection mode (local, remote)
  - Auto-reconnect options
- Authentication Settings Section
  - Stored credentials management
  - Biometric authentication toggle
  - Auto-login options
- Notification Settings Section
  - Trade alerts configuration
  - Market condition alerts
  - Performance alerts
- Display Settings Section
  - Chart preferences
  - Theme selection
  - Data refresh rate
- About Section
  - App version
  - Server version
  - Support information

**Behavior:**
- Changes apply immediately where possible
- Confirmation dialog for sensitive settings
- Backup/restore options for settings
- Test connection option

## 6. Components and Widgets

### 6.1 Status Indicators

- **Bot Status Indicator**
  - Green circle with checkmark for running
  - Red circle with x for stopped
  - Yellow circle with exclamation for warnings
  - Spinning blue circle for connecting/initializing

- **Market Condition Indicator**
  - Arrow up (green) for bullish
  - Arrow down (red) for bearish
  - Horizontal arrows (blue) for ranging
  - Zig-zag (yellow) for choppy

- **Confidence Score Meter**
  - Circular gauge from 0-100%
  - Color gradient from red (low) to green (high)
  - Animated transitions between values

### 6.2 Charts and Visualizations

- **Sparkline Chart**
  - Compact line chart showing recent price movement
  - Color-coded based on direction
  - No axes or labels for maximum space efficiency

- **Performance Chart**
  - Line chart with area fill
  - Optional moving average overlay
  - Supports zooming and time period adjustment
  - Tap points for detailed data

- **Correlation Matrix**
  - Heat map visualization
  - Color-coded cells from green (negative correlation) to red (positive correlation)
  - Filterable by instrument groups
  - Adjustable correlation threshold

- **Volatility Meter**
  - Vertical or horizontal gauge
  - Three sections: Low, Medium, High
  - Animated needle showing current level
  - Historical range indicators

### 6.3 Control Elements

- **Quick Action Button**
  - Circular floating action buttons
  - Clear iconography
  - Haptic feedback on press
  - Optional confirmation for critical actions

- **Toggle Switch**
  - Standard Material Design switch
  - Color-coded based on function
  - Smooth animation between states
  - Optional label

- **Adjustment Slider**
  - Continuous slider with discrete markers
  - Current value tooltip on drag
  - Min/max labels
  - Reset to default option

- **Selection Chip**
  - Rounded rectangular buttons
  - Clear selected/unselected state
  - Can be grouped for mutual exclusivity
  - Support for icons and text

### 6.4 Data Display Elements

- **Metric Card**
  - Compact card showing a single metric
  - Large primary value
  - Smaller secondary value (change)
  - Descriptive title
  - Optional icon
  - Color-coded based on value (positive/negative)

- **Trade List Item**
  - Instrument name and icon
  - Direction indicator (Buy/Sell)
  - Entry and exit prices
  - Profit/loss amount and percentage
  - Duration of trade
  - Optional expanded view with more details

- **Asset Status Card**
  - Instrument name and icon
  - Current price with change
  - Activity status indicator
  - Quick toggle for enabling/disabling
  - Mini chart showing recent performance

- **Alert Banner**
  - Appears at top of screen
  - Color-coded by severity
  - Clear message with optional action button
  - Auto-dismiss with timer
  - Swipe to dismiss

## 7. Responsive Design

The app will be designed to work seamlessly across:
- Different screen sizes (phones and tablets)
- Portrait and landscape orientations
- Various pixel densities

**Phone Layout**:
- Single column layout
- Bottom navigation
- Modal dialogs for detailed views
- Scrolling for content that doesn't fit

**Tablet Layout**:
- Two-column layout in landscape
- Persistent navigation rail on the left
- Side-by-side panels for related content
- Less need for drilling down into details

## 8. Accessibility Considerations

- **Color Blindness**:
  - All color-based indicators include secondary visual cues (icons, patterns)
  - Tested with color blindness simulation
  - Alternative color schemes available

- **Text Scaling**:
  - Support for system font size adjustments
  - Layouts that adapt to larger text
  - Minimum touch target size of 48x48dp

- **Screen Readers**:
  - Meaningful content descriptions for all UI elements
  - Proper navigation order
  - Announcements for dynamic content changes

- **Reduced Motion**:
  - Option to minimize animations
  - No essential information conveyed solely through animation

## 9. Design Assets

Assets to be created for the app:
- App icon (adaptive icon for Android)
- Splash screen
- Navigation icons
- Chart illustrations
- Status and state icons
- Currency and instrument icons
- Background patterns and textures

## 10. Implementation Guidelines

- Use Flutter's Material Design components as base
- Create custom widgets for trading-specific elements
- Implement responsive layouts with MediaQuery
- Use hero animations for transitions between related screens
- Implement shimmer loading effects for data-dependent UI
- Ensure consistent spacing and alignment throughout
- Use provider or bloc pattern for state management

## 11. User Testing

Key areas to test with users:
- Authentication flow completeness
- Dashboard clarity and information hierarchy
- Trading control intuitiveness
- Market condition visualization comprehension
- Navigation efficiency between main sections
- Performance under various network conditions
- Handling of error states and recovery
