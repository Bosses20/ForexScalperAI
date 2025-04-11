import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import '../blocs/trading/trading_bloc.dart';
import '../blocs/market/market_bloc.dart';
import '../models/trading_model.dart';
import '../models/market_model.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../widgets/cards/status_card.dart';
import '../widgets/cards/performance_card.dart';
import '../widgets/cards/market_condition_card.dart';
import '../widgets/cards/active_assets_card.dart';
import '../widgets/cards/recent_trades_card.dart';
import '../widgets/shared/error_widget.dart';
import '../widgets/shared/loading_widget.dart';

class DashboardScreen extends StatefulWidget {
  final ApiService apiService;
  final WebSocketService wsService;

  const DashboardScreen({
    Key? key,
    required this.apiService,
    required this.wsService,
  }) : super(key: key);

  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late TradingBloc _tradingBloc;
  late MarketBloc _marketBloc;
  final refreshKey = GlobalKey<RefreshIndicatorState>();

  @override
  void initState() {
    super.initState();
    _tradingBloc = BlocProvider.of<TradingBloc>(context);
    _marketBloc = BlocProvider.of<MarketBloc>(context);
    
    // Initial data load
    _loadDashboardData();
    
    // Listen for WebSocket connection status changes
    widget.wsService.connectionStatus.listen((status) {
      if (status == ConnectionStatus.connected) {
        // Refresh data when WebSocket connects/reconnects
        _loadDashboardData();
      }
    });
  }

  Future<void> _loadDashboardData() async {
    _tradingBloc.add(LoadTradingDataEvent());
    _marketBloc.add(LoadMarketConditionsEvent());
  }

  Future<void> _handleRefresh() async {
    await _loadDashboardData();
    return Future.delayed(Duration(milliseconds: 300));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Trading Dashboard'),
        actions: [
          BlocBuilder<TradingBloc, TradingState>(
            builder: (context, state) {
              if (state is TradingLoadedState) {
                return Switch(
                  value: state.botStatus.isRunning,
                  onChanged: (value) {
                    if (value) {
                      _tradingBloc.add(StartBotEvent());
                    } else {
                      _tradingBloc.add(StopBotEvent());
                    }
                  },
                  activeColor: Colors.green,
                );
              }
              return SizedBox.shrink();
            },
          ),
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: () {
              refreshKey.currentState?.show();
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        key: refreshKey,
        onRefresh: _handleRefresh,
        child: _buildDashboardContent(),
      ),
    );
  }

  Widget _buildDashboardContent() {
    return SingleChildScrollView(
      physics: AlwaysScrollableScrollPhysics(),
      padding: EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildStatusSection(),
          SizedBox(height: 16),
          _buildPerformanceSection(),
          SizedBox(height: 16),
          _buildMarketConditionSection(),
          SizedBox(height: 16),
          _buildActiveAssetsSection(),
          SizedBox(height: 16),
          _buildRecentTradesSection(),
        ],
      ),
    );
  }

  Widget _buildStatusSection() {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        if (state is TradingLoadingState) {
          return StatusCardSkeleton();
        } else if (state is TradingLoadedState) {
          return StatusCard(
            botStatus: state.botStatus,
            onStartPressed: () => _tradingBloc.add(StartBotEvent()),
            onStopPressed: () => _tradingBloc.add(StopBotEvent()),
          );
        } else if (state is TradingErrorState) {
          return ErrorCard(
            message: state.message,
            onRetry: () => _tradingBloc.add(LoadTradingDataEvent()),
          );
        }
        return StatusCardSkeleton();
      },
    );
  }

  Widget _buildPerformanceSection() {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        if (state is TradingLoadingState) {
          return PerformanceCardSkeleton();
        } else if (state is TradingLoadedState) {
          return PerformanceCard(
            dailyPL: state.performance.dailyPL,
            dailyPLPercentage: state.performance.dailyPLPercentage,
            currentDrawdown: state.performance.drawdown,
            openPositions: state.botStatus.openPositionsCount,
            totalTradesDay: state.performance.totalTradesToday,
          );
        } else if (state is TradingErrorState) {
          return ErrorCard(
            message: "Couldn't load performance data",
            onRetry: () => _tradingBloc.add(LoadTradingDataEvent()),
          );
        }
        return PerformanceCardSkeleton();
      },
    );
  }

  Widget _buildMarketConditionSection() {
    return BlocBuilder<MarketBloc, MarketState>(
      builder: (context, state) {
        if (state is MarketLoadingState) {
          return MarketConditionCardSkeleton();
        } else if (state is MarketLoadedState) {
          return MarketConditionCard(
            marketCondition: state.marketCondition,
            onToggleTradingEnabled: (enabled) {
              _tradingBloc.add(UpdateTradingEnabledEvent(enabled));
            },
          );
        } else if (state is MarketErrorState) {
          return ErrorCard(
            message: state.message,
            onRetry: () => _marketBloc.add(LoadMarketConditionsEvent()),
          );
        }
        return MarketConditionCardSkeleton();
      },
    );
  }

  Widget _buildActiveAssetsSection() {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        if (state is TradingLoadingState) {
          return ActiveAssetsCardSkeleton();
        } else if (state is TradingLoadedState) {
          return ActiveAssetsCard(
            activeAssets: state.botStatus.activeInstruments,
            onAssetToggled: (instrument, active) {
              _tradingBloc.add(ToggleInstrumentEvent(instrument, active));
            },
          );
        } else if (state is TradingErrorState) {
          return ErrorCard(
            message: "Couldn't load active assets",
            onRetry: () => _tradingBloc.add(LoadTradingDataEvent()),
          );
        }
        return ActiveAssetsCardSkeleton();
      },
    );
  }

  Widget _buildRecentTradesSection() {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        if (state is TradingLoadingState) {
          return RecentTradesCardSkeleton();
        } else if (state is TradingLoadedState) {
          return RecentTradesCard(
            recentTrades: state.recentTrades,
            onViewAllPressed: () {
              Navigator.pushNamed(context, '/trading/history');
            },
          );
        } else if (state is TradingErrorState) {
          return ErrorCard(
            message: "Couldn't load recent trades",
            onRetry: () => _tradingBloc.add(LoadTradingDataEvent()),
          );
        }
        return RecentTradesCardSkeleton();
      },
    );
  }
}
