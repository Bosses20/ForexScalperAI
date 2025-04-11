import 'package:equatable/equatable.dart';

/// Model representing the current summary of trading operations.
class TradingSummary extends Equatable {
  /// Number of currently active trades.
  final int activeTrades;
  
  /// List of symbols (instruments) that are currently being traded.
  final List<String> activeSymbols;
  
  /// Total number of positions opened since the bot was started.
  final int totalPositions;
  
  /// Time elapsed since the bot was started.
  final Duration runningTime;
  
  /// Daily profit or loss amount.
  final double dailyProfitLoss;
  
  /// Daily profit or loss percentage relative to starting balance.
  final double dailyProfitLossPercent;
  
  /// Win/loss ratio of closed trades since the bot was started.
  final double winLossRatio;
  
  /// Current risk exposure as a percentage of total account balance.
  final double currentRiskExposure;

  const TradingSummary({
    required this.activeTrades,
    required this.activeSymbols,
    required this.totalPositions,
    required this.runningTime,
    required this.dailyProfitLoss,
    required this.dailyProfitLossPercent,
    required this.winLossRatio,
    required this.currentRiskExposure,
  });

  /// Creates a default instance with empty values.
  factory TradingSummary.empty() {
    return const TradingSummary(
      activeTrades: 0,
      activeSymbols: [],
      totalPositions: 0,
      runningTime: Duration.zero,
      dailyProfitLoss: 0.0,
      dailyProfitLossPercent: 0.0,
      winLossRatio: 0.0,
      currentRiskExposure: 0.0,
    );
  }
  
  /// Creates a TradingSummary from a JSON object.
  factory TradingSummary.fromJson(Map<String, dynamic> json) {
    return TradingSummary(
      activeTrades: json['active_trades'] ?? 0,
      activeSymbols: List<String>.from(json['active_symbols'] ?? []),
      totalPositions: json['total_positions'] ?? 0,
      runningTime: Duration(seconds: json['running_time_seconds'] ?? 0),
      dailyProfitLoss: json['daily_profit_loss']?.toDouble() ?? 0.0,
      dailyProfitLossPercent: json['daily_profit_loss_percent']?.toDouble() ?? 0.0,
      winLossRatio: json['win_loss_ratio']?.toDouble() ?? 0.0,
      currentRiskExposure: json['current_risk_exposure']?.toDouble() ?? 0.0,
    );
  }
  
  /// Converts this TradingSummary to a JSON object.
  Map<String, dynamic> toJson() {
    return {
      'active_trades': activeTrades,
      'active_symbols': activeSymbols,
      'total_positions': totalPositions,
      'running_time_seconds': runningTime.inSeconds,
      'daily_profit_loss': dailyProfitLoss,
      'daily_profit_loss_percent': dailyProfitLossPercent,
      'win_loss_ratio': winLossRatio,
      'current_risk_exposure': currentRiskExposure,
    };
  }
  
  /// Creates a copy of this TradingSummary with the given fields replaced.
  TradingSummary copyWith({
    int? activeTrades,
    List<String>? activeSymbols,
    int? totalPositions,
    Duration? runningTime,
    double? dailyProfitLoss,
    double? dailyProfitLossPercent,
    double? winLossRatio,
    double? currentRiskExposure,
  }) {
    return TradingSummary(
      activeTrades: activeTrades ?? this.activeTrades,
      activeSymbols: activeSymbols ?? this.activeSymbols,
      totalPositions: totalPositions ?? this.totalPositions,
      runningTime: runningTime ?? this.runningTime,
      dailyProfitLoss: dailyProfitLoss ?? this.dailyProfitLoss,
      dailyProfitLossPercent: dailyProfitLossPercent ?? this.dailyProfitLossPercent,
      winLossRatio: winLossRatio ?? this.winLossRatio,
      currentRiskExposure: currentRiskExposure ?? this.currentRiskExposure,
    );
  }

  @override
  List<Object?> get props => [
    activeTrades,
    activeSymbols,
    totalPositions,
    runningTime,
    dailyProfitLoss,
    dailyProfitLossPercent,
    winLossRatio,
    currentRiskExposure,
  ];
}
