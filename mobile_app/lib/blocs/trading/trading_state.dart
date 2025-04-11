import 'package:equatable/equatable.dart';
import 'package:mobile_app/models/market/market_condition.dart';
import 'package:mobile_app/models/trading/trading_instrument.dart';

enum BotStatus {
  running,
  stopped,
  starting,
  stopping,
  error,
  unknown
}

class TradingState extends Equatable {
  final BotStatus botStatus;
  final MarketCondition marketCondition;
  final List<TradingInstrument> activeInstruments;
  final List<Map<String, dynamic>> openPositions;
  final List<Map<String, dynamic>> tradeHistory;
  final Map<String, dynamic> performanceMetrics;
  final bool isLoading;
  final String? errorMessage;

  const TradingState({
    this.botStatus = BotStatus.unknown,
    this.marketCondition = const MarketCondition(),
    this.activeInstruments = const [],
    this.openPositions = const [],
    this.tradeHistory = const [],
    this.performanceMetrics = const {},
    this.isLoading = false,
    this.errorMessage,
  });

  TradingState copyWith({
    BotStatus? botStatus,
    MarketCondition? marketCondition,
    List<TradingInstrument>? activeInstruments,
    List<Map<String, dynamic>>? openPositions,
    List<Map<String, dynamic>>? tradeHistory,
    Map<String, dynamic>? performanceMetrics,
    bool? isLoading,
    String? errorMessage,
  }) {
    return TradingState(
      botStatus: botStatus ?? this.botStatus,
      marketCondition: marketCondition ?? this.marketCondition,
      activeInstruments: activeInstruments ?? this.activeInstruments,
      openPositions: openPositions ?? this.openPositions,
      tradeHistory: tradeHistory ?? this.tradeHistory,
      performanceMetrics: performanceMetrics ?? this.performanceMetrics,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
    );
  }

  @override
  List<Object?> get props => [
    botStatus,
    marketCondition,
    activeInstruments,
    openPositions,
    tradeHistory,
    performanceMetrics,
    isLoading,
    errorMessage,
  ];
}
