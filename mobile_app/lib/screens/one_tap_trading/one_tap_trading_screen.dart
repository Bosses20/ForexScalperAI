import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../blocs/one_tap_trading/one_tap_trading_bloc.dart';
import '../../models/bot_server.dart';
import '../../models/market/market_condition.dart';
import '../../widgets/error_banner.dart';
import '../../widgets/one_tap_trading_button.dart';
import '../../widgets/trading_status_dashboard.dart';
import '../../widgets/market_condition_view.dart';
import '../../widgets/status_indicator.dart';

class OneTapTradingScreen extends StatefulWidget {
  final BotServer initialServer;
  
  const OneTapTradingScreen({
    Key? key,
    required this.initialServer,
  }) : super(key: key);

  @override
  State<OneTapTradingScreen> createState() => _OneTapTradingScreenState();
}

class _OneTapTradingScreenState extends State<OneTapTradingScreen> {
  String _tradingFeedback = '';
  bool _showDetailedMarketView = false;
  
  @override
  void initState() {
    super.initState();
    
    // Initialize one-tap trading with the provided server
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<OneTapTradingBloc>().add(
        OneTapTradingStarted(widget.initialServer),
      );
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('One-Tap Trading'),
        elevation: 0,
      ),
      body: BlocConsumer<OneTapTradingBloc, OneTapTradingState>(
        listenWhen: (previous, current) => 
          previous.status != current.status ||
          previous.hasError != current.hasError,
        listener: (context, state) {
          // Update trading feedback based on state changes
          if (state.isTrading) {
            setState(() {
              _tradingFeedback = 'Trading active - following market conditions';
            });
          } else if (state.isAnalyzing) {
            setState(() {
              _tradingFeedback = 'Analyzing market conditions...';
            });
          } else if (state.status == OneTapTradingStatus.readyToTrade) {
            setState(() {
              _tradingFeedback = state.marketCondition?.isFavorableForTrading ?? false
                  ? 'Market conditions favorable - ready to trade'
                  : 'Market conditions unfavorable - trading not recommended';
            });
          } else {
            setState(() {
              _tradingFeedback = '';
            });
          }
        },
        builder: (context, state) {
          return Column(
            children: [
              // Error banners
              if (state.hasConnectionError)
                ConnectionErrorBanner(
                  serverName: state.server?.name ?? 'Unknown',
                  onReconnect: () {
                    if (state.server != null) {
                      context.read<OneTapTradingBloc>().add(
                        OneTapTradingRetryConnection(state.server!),
                      );
                    }
                  },
                  onDismiss: () {
                    context.read<OneTapTradingBloc>().add(
                      OneTapTradingClearError(),
                    );
                  },
                ),
              
              if (state.hasMarketError)
                MarketDataErrorBanner(
                  onRefresh: () {
                    context.read<OneTapTradingBloc>().add(
                      const OneTapTradingMarketAnalysisRequested('EURUSD'),
                    );
                  },
                  onDismiss: () {
                    context.read<OneTapTradingBloc>().add(
                      OneTapTradingClearError(),
                    );
                  },
                ),
              
              if (state.hasBotError)
                BotErrorBanner(
                  errorMessage: state.errorMessage ?? 'Unknown error',
                  onDismiss: () {
                    context.read<OneTapTradingBloc>().add(
                      OneTapTradingClearError(),
                    );
                  },
                ),
              
              // Status dashboard
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: TradingStatusDashboard(
                  serverStatus: StatusData(
                    isActive: state.isConnected,
                    title: 'Server',
                    subtitle: state.server?.name ?? 'Not connected',
                    icon: Icons.dns,
                  ),
                  botStatus: StatusData(
                    isActive: state.isTrading,
                    title: 'Trading Bot',
                    subtitle: _getBotStatusText(state),
                    icon: Icons.smart_toy,
                  ),
                  marketStatus: StatusData(
                    isActive: state.marketCondition?.isFavorableForTrading ?? false,
                    title: 'Market',
                    subtitle: _getMarketStatusText(state.marketCondition),
                    icon: Icons.trending_up,
                  ),
                  onMarketTap: () {
                    setState(() {
                      _showDetailedMarketView = !_showDetailedMarketView;
                    });
                  },
                ),
              ),
              
              // Detailed market view (expandable)
              AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                height: _showDetailedMarketView ? 260 : 0,
                curve: Curves.easeInOut,
                child: SingleChildScrollView(
                  child: state.marketCondition != null
                      ? MarketConditionView(
                          marketCondition: state.marketCondition!,
                        )
                      : const SizedBox(),
                ),
              ),
              
              const Spacer(),
              
              // Trading feedback
              OneTapTradingFeedback(
                isTrading: state.isTrading,
                feedbackMessage: _tradingFeedback,
              ),
              
              // One-tap trading button
              Padding(
                padding: const EdgeInsets.all(24.0),
                child: OneTapTradingButton(
                  isConnected: state.isConnected,
                  isTrading: state.isTrading,
                  marketCondition: state.marketCondition,
                  isLoading: state.isAnalyzing,
                  onTap: () {
                    final bloc = context.read<OneTapTradingBloc>();
                    
                    if (!state.isTrading) {
                      if (state.isConnected) {
                        // If connected but not trading, start trading
                        if (state.server != null) {
                          bloc.add(OneTapTradingStarted(state.server!));
                        }
                      } else {
                        // If not connected, show connection dialog
                        _showServerConnectionDialog(context, state);
                      }
                    }
                  },
                  onStop: () {
                    context.read<OneTapTradingBloc>().add(
                      OneTapTradingStopped(),
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }
  
  String _getBotStatusText(OneTapTradingState state) {
    if (state.isTrading) {
      return 'Active';
    } else if (state.status == OneTapTradingStatus.stopping) {
      return 'Stopping...';
    } else if (state.status == OneTapTradingStatus.analyzing) {
      return 'Analyzing...';
    } else {
      return 'Inactive';
    }
  }
  
  String _getMarketStatusText(MarketCondition? marketCondition) {
    if (marketCondition == null) {
      return 'Unknown';
    }
    
    if (marketCondition.isFavorableForTrading) {
      return '${marketCondition.confidenceScore}% Favorable';
    } else {
      return 'Unfavorable';
    }
  }
  
  void _showServerConnectionDialog(BuildContext context, OneTapTradingState state) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Connection Required'),
        content: const Text(
          'You must connect to a trading server before starting trading. '
          'Would you like to connect now?'
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
            },
            child: const Text('CANCEL'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              
              // Here you would navigate to server selection screen
              // or connect to the last server if available
              if (state.server != null) {
                context.read<OneTapTradingBloc>().add(
                  OneTapTradingStarted(state.server!),
                );
              } else {
                // Navigate to server selection
                // This depends on your navigation setup
              }
            },
            child: const Text('CONNECT'),
          ),
        ],
      ),
    );
  }
}
