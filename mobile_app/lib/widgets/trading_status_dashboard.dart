import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../blocs/trading/trading_bloc.dart';
import '../blocs/network_discovery/network_discovery_bloc.dart';
import '../models/bot_server.dart';
import '../models/market/market_condition.dart';
import '../models/trading_model.dart';
import 'status_indicator.dart';

class TradingStatusDashboard extends StatelessWidget {
  final VoidCallback? onServerTap;
  final VoidCallback? onMarketTap;
  final VoidCallback? onBotTap;

  const TradingStatusDashboard({
    Key? key,
    this.onServerTap,
    this.onMarketTap,
    this.onBotTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildHeader(context),
            const Divider(),
            _buildServerStatus(context),
            _buildBotStatus(context),
            _buildMarketStatus(context),
            const Divider(),
            _buildQuickTradeButton(context),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Text(
        'Trading Status',
        style: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _buildServerStatus(BuildContext context) {
    return BlocBuilder<NetworkDiscoveryBloc, NetworkDiscoveryState>(
      builder: (context, state) {
        final BotServer? activeServer = state.activeServer;
        final bool isConnected = activeServer != null;
        
        return ServerStatusIndicator(
          isConnected: isConnected,
          serverName: activeServer?.name ?? 'No Server',
          serverDetails: isConnected 
              ? '${activeServer!.ipAddress}:${activeServer.port}'
              : 'Tap to connect',
          onTap: onServerTap,
        );
      },
    );
  }

  Widget _buildBotStatus(BuildContext context) {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        final bool isRunning = state.botStatus == BotStatus.running;
        String? statusText;
        
        switch (state.botStatus) {
          case BotStatus.running:
            statusText = 'Active - Trading';
            break;
          case BotStatus.starting:
            statusText = 'Starting...';
            break;
          case BotStatus.stopping:
            statusText = 'Stopping...';
            break;
          case BotStatus.stopped:
            statusText = 'Idle';
            break;
          case BotStatus.error:
            statusText = 'Error: ${state.errorMessage ?? "Unknown error"}';
            break;
        }
        
        return BotStatusIndicator(
          isRunning: isRunning,
          status: statusText,
          onTap: onBotTap,
        );
      },
    );
  }

  Widget _buildMarketStatus(BuildContext context) {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        final MarketCondition? marketCondition = state.marketCondition;
        
        // Default values if market condition is null
        String trendText = 'Unknown';
        double confidence = 0.0;
        
        if (marketCondition != null) {
          switch (marketCondition.trend) {
            case TrendType.bullish:
              trendText = 'Bullish';
              break;
            case TrendType.bearish:
              trendText = 'Bearish';
              break;
            case TrendType.ranging:
              trendText = 'Ranging';
              break;
            case TrendType.choppy:
              trendText = 'Choppy';
              break;
            case TrendType.unknown:
              trendText = 'Unknown';
              break;
          }
          
          confidence = marketCondition.confidenceScore;
        }
        
        return MarketStatusIndicator(
          confidenceScore: confidence,
          trend: trendText,
          onTap: onMarketTap,
        );
      },
    );
  }

  Widget _buildQuickTradeButton(BuildContext context) {
    return BlocBuilder<TradingBloc, TradingState>(
      builder: (context, state) {
        final bool isConnected = context.select(
          (NetworkDiscoveryBloc bloc) => bloc.state.activeServer != null
        );
        
        final bool isRunning = state.botStatus == BotStatus.running;
        final bool isStarting = state.botStatus == BotStatus.starting;
        final bool isStopping = state.botStatus == BotStatus.stopping;
        
        final bool canStart = isConnected && !isRunning && !isStarting && !isStopping;
        final bool canStop = isRunning && !isStopping;
        
        final MarketCondition? marketCondition = state.marketCondition;
        final bool isFavorable = marketCondition?.isTradingFavorable() ?? false;
        
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Expanded(
                child: ElevatedButton(
                  onPressed: canStart
                      ? () => context.read<TradingBloc>().add(StartBotEvent())
                      : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: isFavorable ? Colors.green : Colors.orange,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.play_arrow),
                      const SizedBox(width: 8),
                      Text(
                        isFavorable 
                            ? 'START TRADING' 
                            : 'START (Caution)',
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (canStop) ...[
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () => context.read<TradingBloc>().add(StopBotEvent()),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: const Icon(Icons.stop),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}
