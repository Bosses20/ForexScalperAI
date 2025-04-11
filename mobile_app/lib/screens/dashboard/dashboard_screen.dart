import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:mobile_app/blocs/trading/trading_bloc.dart';
import 'package:mobile_app/blocs/trading/trading_event.dart';
import 'package:mobile_app/blocs/trading/trading_state.dart';
import 'package:mobile_app/blocs/network_discovery/network_discovery_bloc.dart';
import 'package:mobile_app/models/market/market_condition.dart';
import 'package:mobile_app/models/trading_model.dart';
import 'package:mobile_app/screens/server_discovery/server_discovery_screen.dart';
import 'package:mobile_app/widgets/cards/market_condition_card.dart';
import 'package:mobile_app/widgets/cards/trading_instrument_card.dart';
import 'package:mobile_app/widgets/dashboard/account_summary_widget.dart';
import 'package:mobile_app/widgets/dashboard/bot_control_panel.dart';
import 'package:mobile_app/widgets/dashboard/correlation_matrix.dart';
import 'package:mobile_app/widgets/dashboard/market_conditions_widget.dart';
import 'package:mobile_app/widgets/dashboard/trading_session_widget.dart';
import 'package:mobile_app/widgets/trading_status_dashboard.dart';
import 'package:mobile_app/widgets/market_condition_view.dart';
import 'package:mobile_app/widgets/error_banner.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final GlobalKey<RefreshIndicatorState> _refreshIndicatorKey = GlobalKey<RefreshIndicatorState>();
  bool _autoStartRequested = false;
  String? _errorMessage;
  bool _showDetailedMarketView = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    
    // Load initial data
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _refreshData();
      
      // Check if we should auto-start trading
      final args = ModalRoute.of(context)?.settings.arguments;
      if (args is Map<String, dynamic> && args.containsKey('autoStartTrading')) {
        _autoStartRequested = args['autoStartTrading'] == true;
        if (_autoStartRequested) {
          _handleAutoStart();
        }
      }
    });
  }

  /// Handle auto-start trading request
  Future<void> _handleAutoStart() async {
    // First check if we're connected to a server
    final networkBloc = BlocProvider.of<NetworkDiscoveryBloc>(context);
    if (networkBloc.state.activeServer == null) {
      setState(() {
        _errorMessage = "Cannot start trading: No server connected";
      });
      return;
    }
    
    // Check market conditions before starting
    final tradingBloc = BlocProvider.of<TradingBloc>(context);
    
    // Wait for data to load before checking conditions
    await Future.delayed(const Duration(seconds: 1));
    
    // Check if the bot is already running
    if (tradingBloc.state.botStatus == BotStatus.running) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Trading bot is already running'),
          backgroundColor: Colors.green,
        ),
      );
      return;
    }
    
    // Check market conditions before starting
    if (tradingBloc.state.marketCondition != null) {
      final condition = tradingBloc.state.marketCondition!;
      
      // Get active instruments based on current market conditions
      List<String> recommendedInstruments = _getRecommendedInstruments(condition);
      
      // Start the trading bot with recommended settings
      if (condition.isTradingFavorable()) {
        tradingBloc.add(StartBotEvent(
          instruments: recommendedInstruments,
          riskLevel: _getRiskLevelForConditions(condition),
          tradingMode: _getTradingModeForConditions(condition),
        ));
        
        // Show success message
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Trading started automatically based on favorable market conditions'),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        // Market conditions not favorable, show warning
        _showUnfavorableMarketDialog(condition);
      }
    } else {
      // If no market condition data is available, ask user if they want to proceed
      _showNoMarketDataDialog();
    }
  }

  void _showUnfavorableMarketDialog(MarketCondition condition) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Caution: Unfavorable Market'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Current market conditions are not optimal for trading:'),
            const SizedBox(height: 12),
            Text('• ${_getTrendDescription(condition.trend)}'),
            Text('• Volatility: ${condition.volatility.toString().split('.').last}'),
            Text('• Confidence Score: ${condition.confidenceScore.toStringAsFixed(0)}%'),
            const SizedBox(height: 12),
            const Text('Starting the bot in these conditions may lead to suboptimal results. Do you want to proceed anyway?'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CANCEL'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              // Start with caution
              final tradingBloc = BlocProvider.of<TradingBloc>(context);
              List<String> recommendedInstruments = _getRecommendedInstruments(condition);
              
              tradingBloc.add(StartBotEvent(
                instruments: recommendedInstruments,
                riskLevel: TradingRiskLevel.low, // Use low risk in unfavorable conditions
                tradingMode: TradingMode.conservative,
              ));
              
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Trading started with conservative settings due to market conditions'),
                  backgroundColor: Colors.orange,
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orange,
            ),
            child: const Text('PROCEED WITH CAUTION'),
          ),
        ],
      ),
    );
  }

  void _showNoMarketDataDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('No Market Data'),
        content: const Text('Unable to analyze current market conditions. Would you like to start trading with default settings?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CANCEL'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              // Start with default settings
              final tradingBloc = BlocProvider.of<TradingBloc>(context);
              tradingBloc.add(const StartBotEvent());
              
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Trading started with default settings'),
                  backgroundColor: Colors.blue,
                ),
              );
            },
            child: const Text('START ANYWAY'),
          ),
        ],
      ),
    );
  }

  String _getTrendDescription(TrendType trend) {
    switch (trend) {
      case TrendType.bullish:
        return 'Bullish market trend';
      case TrendType.bearish:
        return 'Bearish market trend';
      case TrendType.ranging:
        return 'Ranging market (sideways movement)';
      case TrendType.choppy:
        return 'Choppy market (unpredictable movements)';
      case TrendType.unknown:
        return 'Unknown market trend';
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _refreshData() async {
    final tradingBloc = BlocProvider.of<TradingBloc>(context);
    tradingBloc.add(LoadTradingDataEvent());
    return Future.delayed(const Duration(seconds: 1));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Trading Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              _refreshIndicatorKey.currentState?.show();
            },
          ),
          IconButton(
            icon: const Icon(Icons.wifi),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const ServerDiscoveryScreen(),
                ),
              );
            },
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Overview'),
            Tab(text: 'Instruments'),
            Tab(text: 'Positions'),
            Tab(text: 'Performance'),
          ],
        ),
      ),
      body: RefreshIndicator(
        key: _refreshIndicatorKey,
        onRefresh: _refreshData,
        child: BlocListener<TradingBloc, TradingState>(
          listener: (context, state) {
            // Handle errors
            if (state.errorMessage != null && state.errorMessage!.isNotEmpty) {
              setState(() {
                _errorMessage = state.errorMessage;
              });
            } else {
              setState(() {
                _errorMessage = null;
              });
            }
          },
          child: Column(
            children: [
              // Error banner
              if (_errorMessage != null)
                ErrorBanner(
                  message: _errorMessage!,
                  onDismiss: () {
                    setState(() {
                      _errorMessage = null;
                    });
                  },
                ),
                
              // Trading status dashboard
              TradingStatusDashboard(
                onServerTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => const ServerDiscoveryScreen(),
                    ),
                  );
                },
                onMarketTap: () {
                  setState(() {
                    _showDetailedMarketView = !_showDetailedMarketView;
                  });
                },
                onBotTap: () {
                  // Toggle bot status
                  final tradingBloc = BlocProvider.of<TradingBloc>(context);
                  if (tradingBloc.state.botStatus == BotStatus.running) {
                    tradingBloc.add(StopBotEvent());
                  } else if (tradingBloc.state.botStatus == BotStatus.stopped) {
                    _handleAutoStart();
                  }
                },
              ),
              
              // Market condition detailed view (toggled by tapping on market status)
              BlocBuilder<TradingBloc, TradingState>(
                builder: (context, state) {
                  if (_showDetailedMarketView && state.marketCondition != null) {
                    return MarketConditionView(
                      marketCondition: state.marketCondition!,
                      showDetailedView: true,
                    );
                  }
                  return const SizedBox.shrink();
                },
              ),
              
              // Main content
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildOverviewTab(),
                    _buildInstrumentsTab(),
                    _buildPositionsTab(),
                    _buildPerformanceTab(),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  TradingRiskLevel _getRiskLevelForConditions(MarketCondition condition) {
    if (condition.confidenceScore >= 80) {
      return TradingRiskLevel.medium;
    } else if (condition.confidenceScore >= 60) {
      return TradingRiskLevel.low;
    } else {
      return TradingRiskLevel.veryLow;
    }
  }

  TradingMode _getTradingModeForConditions(MarketCondition condition) {
    switch (condition.trend) {
      case TrendType.bullish:
        return condition.volatility == VolatilityLevel.high
            ? TradingMode.conservative
            : TradingMode.aggressive;
      case TrendType.bearish:
        return condition.volatility == VolatilityLevel.high
            ? TradingMode.conservative
            : TradingMode.moderate;
      case TrendType.ranging:
        return TradingMode.moderate;
      case TrendType.choppy:
      case TrendType.unknown:
        return TradingMode.conservative;
    }
  }

  List<String> _getRecommendedInstruments(MarketCondition condition) {
    // This would ideally come from the backend based on market analysis
    // For now, provide reasonable defaults
    switch (condition.trend) {
      case TrendType.bullish:
        return ['EURUSD', 'GBPUSD', 'AUDUSD'];
      case TrendType.bearish:
        return ['USDJPY', 'USDCAD', 'USDCHF'];
      case TrendType.ranging:
        return ['EURUSD', 'GBPJPY', 'EURGBP'];
      case TrendType.choppy:
      case TrendType.unknown:
        return ['EURUSD']; // Stick to major pairs in uncertain conditions
    }
  }

  Widget _buildOverviewTab() {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        return SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Account summary
              AccountSummaryWidget(
                accountInfo: state.accountInfo,
                isLoading: state.isLoading,
              ),
              
              const SizedBox(height: 16),
              
              // Trading session status
              TradingSessionWidget(
                currentSession: state.currentSession,
                nextSession: state.nextSession,
              ),
              
              const SizedBox(height: 16),
              
              // Market conditions
              MarketConditionsWidget(
                marketCondition: state.marketCondition,
                onTap: () {
                  setState(() {
                    _showDetailedMarketView = !_showDetailedMarketView;
                  });
                },
              ),
              
              const SizedBox(height: 16),
              
              // Trading status dashboard (showing active strategies, risk level, etc.)
              TradingStatusDashboard(
                botStatus: state.botStatus,
                activeStrategies: state.activeStrategies,
                activeInstruments: state.activeInstruments,
                riskLevel: state.riskLevel,
                tradingMode: state.tradingMode,
              ),
              
              if (state.errorMessage != null)
                ErrorBanner(
                  message: state.errorMessage!,
                  onDismiss: () {
                    BlocProvider.of<TradingBloc>(context).add(ClearErrorEvent());
                  },
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildInstrumentsTab() {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        if (state.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        
        if (state.availableInstruments.isEmpty) {
          return const Center(
            child: Text('No instruments available'),
          );
        }
        
        return Column(
          children: [
            // Correlation matrix at the top
            if (state.correlationData != null && state.correlationData!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: CorrelationMatrix(correlationData: state.correlationData!),
              ),
            
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.all(8.0),
                itemCount: state.availableInstruments.length,
                itemBuilder: (context, index) {
                  final instrument = state.availableInstruments[index];
                  return TradingInstrumentCard(
                    instrument: instrument,
                    isActive: state.activeInstruments.contains(instrument.symbol),
                    onToggle: (isActive) {
                      if (isActive) {
                        BlocProvider.of<TradingBloc>(context)
                            .add(AddInstrumentEvent(symbol: instrument.symbol));
                      } else {
                        BlocProvider.of<TradingBloc>(context)
                            .add(RemoveInstrumentEvent(symbol: instrument.symbol));
                      }
                    },
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildPositionsTab() {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        if (state.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        
        if (state.positions.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.info_outline, size: 48, color: Colors.grey),
                const SizedBox(height: 16),
                const Text(
                  'No active positions',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                if (state.botStatus != BotStatus.running)
                  const Text(
                    'Start the trading bot to open positions',
                    style: TextStyle(color: Colors.grey),
                  ),
              ],
            ),
          );
        }
        
        return ListView.builder(
          padding: const EdgeInsets.all(8.0),
          itemCount: state.positions.length,
          itemBuilder: (context, index) {
            final position = state.positions[index];
            return Card(
              margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          position.symbol,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 18,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: position.direction == 'buy'
                                ? Colors.green.withOpacity(0.2)
                                : Colors.red.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            position.direction.toUpperCase(),
                            style: TextStyle(
                              color: position.direction == 'buy'
                                  ? Colors.green
                                  : Colors.red,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Entry', style: TextStyle(color: Colors.grey)),
                            Text(position.entryPrice.toString()),
                          ],
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Current', style: TextStyle(color: Colors.grey)),
                            Text(position.currentPrice.toString()),
                          ],
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('P/L', style: TextStyle(color: Colors.grey)),
                            Text(
                              '${position.profitLoss > 0 ? '+' : ''}${position.profitLoss.toStringAsFixed(2)}',
                              style: TextStyle(
                                color: position.profitLoss > 0
                                    ? Colors.green
                                    : position.profitLoss < 0
                                        ? Colors.red
                                        : Colors.grey,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.access_time, size: 16, color: Colors.grey),
                            const SizedBox(width: 4),
                            Text(
                              position.duration,
                              style: const TextStyle(color: Colors.grey),
                            ),
                          ],
                        ),
                        ElevatedButton(
                          onPressed: () {
                            BlocProvider.of<TradingBloc>(context).add(
                              ClosePositionEvent(positionId: position.id),
                            );
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          ),
                          child: const Text('Close Position'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildPerformanceTab() {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        if (state.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        
        return SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Performance Summary',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),
                      _buildPerformanceMetric('Total Trades', state.performanceStats?.totalTrades.toString() ?? 'N/A'),
                      _buildPerformanceMetric('Win Rate', state.performanceStats?.winRate != null 
                          ? '${(state.performanceStats!.winRate * 100).toStringAsFixed(2)}%' 
                          : 'N/A'),
                      _buildPerformanceMetric('Net Profit', state.performanceStats?.netProfit != null 
                          ? '${state.performanceStats!.netProfit > 0 ? '+' : ''}${state.performanceStats!.netProfit.toStringAsFixed(2)}' 
                          : 'N/A'),
                      _buildPerformanceMetric('Average Trade', state.performanceStats?.averageTrade != null 
                          ? '${state.performanceStats!.averageTrade.toStringAsFixed(2)}' 
                          : 'N/A'),
                      _buildPerformanceMetric('Profit Factor', state.performanceStats?.profitFactor != null 
                          ? state.performanceStats!.profitFactor.toStringAsFixed(2) 
                          : 'N/A'),
                    ],
                  ),
                ),
              ),
              
              const SizedBox(height: 16),
              
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Recent Trades',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),
                      if (state.recentTrades.isEmpty)
                        const Center(
                          child: Text(
                            'No recent trades',
                            style: TextStyle(color: Colors.grey),
                          ),
                        )
                      else
                        ListView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: state.recentTrades.length,
                          itemBuilder: (context, index) {
                            final trade = state.recentTrades[index];
                            return ListTile(
                              title: Text(trade.symbol),
                              subtitle: Text(
                                '${trade.direction.toUpperCase()} • ${trade.exitReason}',
                              ),
                              trailing: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text(
                                    '${trade.profitLoss > 0 ? '+' : ''}${trade.profitLoss.toStringAsFixed(2)}',
                                    style: TextStyle(
                                      color: trade.profitLoss > 0
                                          ? Colors.green
                                          : Colors.red,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Text(
                                    trade.timeAgo,
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey,
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
  
  Widget _buildPerformanceMetric(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
