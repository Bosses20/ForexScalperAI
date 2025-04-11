import 'package:equatable/equatable.dart';

abstract class TradingEvent extends Equatable {
  const TradingEvent();

  @override
  List<Object?> get props => [];
}

class LoadTradingData extends TradingEvent {
  const LoadTradingData();
}

class StartBot extends TradingEvent {
  const StartBot();
}

class StopBot extends TradingEvent {
  const StopBot();
}

class ToggleInstrument extends TradingEvent {
  final String symbol;
  final bool isActive;

  const ToggleInstrument({required this.symbol, required this.isActive});

  @override
  List<Object?> get props => [symbol, isActive];
}

class UpdateMarketCondition extends TradingEvent {
  final Map<String, dynamic> marketConditionData;

  const UpdateMarketCondition(this.marketConditionData);

  @override
  List<Object?> get props => [marketConditionData];
}

class UpdateOpenPositions extends TradingEvent {
  final List<Map<String, dynamic>> positions;

  const UpdateOpenPositions(this.positions);

  @override
  List<Object?> get props => [positions];
}

class UpdateTradeHistory extends TradingEvent {
  final List<Map<String, dynamic>> trades;

  const UpdateTradeHistory(this.trades);

  @override
  List<Object?> get props => [trades];
}

class UpdatePerformanceMetrics extends TradingEvent {
  final Map<String, dynamic> metrics;

  const UpdatePerformanceMetrics(this.metrics);

  @override
  List<Object?> get props => [metrics];
}

class UpdateBotStatus extends TradingEvent {
  final Map<String, dynamic> statusData;

  const UpdateBotStatus(this.statusData);

  @override
  List<Object?> get props => [statusData];
}

class TradingError extends TradingEvent {
  final String message;

  const TradingError(this.message);

  @override
  List<Object?> get props => [message];
}
