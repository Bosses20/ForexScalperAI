import 'package:equatable/equatable.dart';

/// Represents an individual trading instrument with its properties and status
class TradingInstrument extends Equatable {
  final String symbol;
  final String displayName;
  final String type; // 'forex', 'synthetic', etc.
  final bool isActive;
  final double? currentPrice;
  final double? dailyChange;
  final double? dailyChangePercent;
  final List<double>? recentPrices; // For sparkline chart
  final int? decimalPlaces;
  final String? sessionStatus; // 'open', 'closed', 'pre-market'
  
  const TradingInstrument({
    required this.symbol,
    required this.displayName,
    required this.type,
    required this.isActive,
    this.currentPrice,
    this.dailyChange,
    this.dailyChangePercent,
    this.recentPrices,
    this.decimalPlaces,
    this.sessionStatus,
  });
  
  factory TradingInstrument.fromJson(Map<String, dynamic> json) {
    return TradingInstrument(
      symbol: json['symbol'] ?? '',
      displayName: json['display_name'] ?? json['symbol'] ?? '',
      type: json['type'] ?? 'unknown',
      isActive: json['is_active'] ?? false,
      currentPrice: json['current_price']?.toDouble(),
      dailyChange: json['daily_change']?.toDouble(),
      dailyChangePercent: json['daily_change_percent']?.toDouble(),
      recentPrices: json['recent_prices'] != null 
        ? List<double>.from(json['recent_prices']) 
        : null,
      decimalPlaces: json['decimal_places'],
      sessionStatus: json['session_status'],
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'symbol': symbol,
      'display_name': displayName,
      'type': type,
      'is_active': isActive,
      'current_price': currentPrice,
      'daily_change': dailyChange,
      'daily_change_percent': dailyChangePercent,
      'recent_prices': recentPrices,
      'decimal_places': decimalPlaces,
      'session_status': sessionStatus,
    };
  }
  
  TradingInstrument copyWith({
    String? symbol,
    String? displayName,
    String? type,
    bool? isActive,
    double? currentPrice,
    double? dailyChange,
    double? dailyChangePercent,
    List<double>? recentPrices,
    int? decimalPlaces,
    String? sessionStatus,
  }) {
    return TradingInstrument(
      symbol: symbol ?? this.symbol,
      displayName: displayName ?? this.displayName,
      type: type ?? this.type,
      isActive: isActive ?? this.isActive,
      currentPrice: currentPrice ?? this.currentPrice,
      dailyChange: dailyChange ?? this.dailyChange,
      dailyChangePercent: dailyChangePercent ?? this.dailyChangePercent,
      recentPrices: recentPrices ?? this.recentPrices,
      decimalPlaces: decimalPlaces ?? this.decimalPlaces,
      sessionStatus: sessionStatus ?? this.sessionStatus,
    );
  }
  
  /// Gets asset icon based on the instrument type
  String get assetIcon {
    switch (type.toLowerCase()) {
      case 'forex':
        return 'assets/icons/forex.svg';
      case 'synthetic':
        return 'assets/icons/synthetic.svg';
      case 'crypto':
        return 'assets/icons/crypto.svg';
      case 'commodity':
        return 'assets/icons/commodity.svg';
      case 'stock':
        return 'assets/icons/stock.svg';
      default:
        return 'assets/icons/unknown.svg';
    }
  }
  
  /// Returns true if the instrument price is currently going up
  bool get isPriceGoingUp {
    return dailyChange != null && dailyChange! > 0;
  }
  
  @override
  List<Object?> get props => [
    symbol, 
    displayName, 
    type, 
    isActive, 
    currentPrice,
    dailyChange, 
    dailyChangePercent, 
    recentPrices, 
    decimalPlaces, 
    sessionStatus
  ];
}

/// Represents a completed or active trading position
class TradePosition extends Equatable {
  final String id;
  final String symbol;
  final String direction; // 'buy' or 'sell'
  final double entryPrice;
  final double? exitPrice;
  final double lotSize;
  final DateTime entryTime;
  final DateTime? exitTime;
  final double? profit;
  final double? profitPercent;
  final String? exitReason; // 'tp', 'sl', 'manual', 'strategy', etc.
  final bool isOpen;
  final Map<String, dynamic> additionalInfo;
  
  const TradePosition({
    required this.id,
    required this.symbol,
    required this.direction,
    required this.entryPrice,
    required this.lotSize,
    required this.entryTime,
    this.exitPrice,
    this.exitTime,
    this.profit,
    this.profitPercent,
    this.exitReason,
    this.isOpen = false,
    this.additionalInfo = const {},
  });
  
  factory TradePosition.fromJson(Map<String, dynamic> json) {
    return TradePosition(
      id: json['id'] ?? '',
      symbol: json['symbol'] ?? '',
      direction: json['direction'] ?? '',
      entryPrice: json['entry_price']?.toDouble() ?? 0.0,
      lotSize: json['lot_size']?.toDouble() ?? 0.0,
      entryTime: DateTime.parse(json['entry_time']),
      exitPrice: json['exit_price']?.toDouble(),
      exitTime: json['exit_time'] != null 
          ? DateTime.parse(json['exit_time']) 
          : null,
      profit: json['profit']?.toDouble(),
      profitPercent: json['profit_percent']?.toDouble(),
      exitReason: json['exit_reason'],
      isOpen: json['is_open'] ?? false,
      additionalInfo: json['additional_info'] ?? {},
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'symbol': symbol,
      'direction': direction,
      'entry_price': entryPrice,
      'lot_size': lotSize,
      'entry_time': entryTime.toIso8601String(),
      'exit_price': exitPrice,
      'exit_time': exitTime?.toIso8601String(),
      'profit': profit,
      'profit_percent': profitPercent,
      'exit_reason': exitReason,
      'is_open': isOpen,
      'additional_info': additionalInfo,
    };
  }
  
  /// Returns trade duration as a formatted string
  String get durationFormatted {
    final endTime = exitTime ?? DateTime.now();
    final duration = endTime.difference(entryTime);
    
    if (duration.inDays > 0) {
      return '${duration.inDays}d ${duration.inHours % 24}h';
    } else if (duration.inHours > 0) {
      return '${duration.inHours}h ${duration.inMinutes % 60}m';
    } else if (duration.inMinutes > 0) {
      return '${duration.inMinutes}m ${duration.inSeconds % 60}s';
    } else {
      return '${duration.inSeconds}s';
    }
  }
  
  /// Returns the color representing the trade's direction
  String get directionColor {
    return direction.toLowerCase() == 'buy' ? '#00C853' : '#FF3D00';
  }
  
  /// Returns the icon name for the trade's direction
  String get directionIcon {
    return direction.toLowerCase() == 'buy' ? 'arrow_upward' : 'arrow_downward';
  }
  
  /// Returns true if the trade was profitable
  bool get isProfitable {
    return profit != null && profit! > 0;
  }
  
  @override
  List<Object?> get props => [
    id, 
    symbol, 
    direction, 
    entryPrice, 
    exitPrice,
    lotSize, 
    entryTime, 
    exitTime, 
    profit, 
    profitPercent, 
    exitReason, 
    isOpen,
    additionalInfo
  ];
}

/// Represents the overall status of the trading bot
class BotStatus extends Equatable {
  final bool isRunning;
  final DateTime? startTime;
  final String? accountId;
  final String? accountType;
  final double? accountBalance;
  final double? accountEquity;
  final double? accountMargin;
  final int openPositionsCount;
  final int totalPositionsToday;
  final List<TradingInstrument> activeInstruments;
  final bool isTradingEnabled;
  final String? currentStrategyName;
  final int? riskLevel;
  final String? runningTimeFormatted;
  final Map<String, dynamic> additionalInfo;
  
  const BotStatus({
    required this.isRunning,
    this.startTime,
    this.accountId,
    this.accountType,
    this.accountBalance,
    this.accountEquity,
    this.accountMargin,
    this.openPositionsCount = 0,
    this.totalPositionsToday = 0,
    this.activeInstruments = const [],
    this.isTradingEnabled = false,
    this.currentStrategyName,
    this.riskLevel,
    this.runningTimeFormatted,
    this.additionalInfo = const {},
  });
  
  factory BotStatus.fromJson(Map<String, dynamic> json) {
    return BotStatus(
      isRunning: json['is_running'] ?? false,
      startTime: json['start_time'] != null 
          ? DateTime.parse(json['start_time']) 
          : null,
      accountId: json['account_id'],
      accountType: json['account_type'],
      accountBalance: json['account_balance']?.toDouble(),
      accountEquity: json['account_equity']?.toDouble(),
      accountMargin: json['account_margin']?.toDouble(),
      openPositionsCount: json['open_positions_count'] ?? 0,
      totalPositionsToday: json['total_positions_today'] ?? 0,
      activeInstruments: json['active_instruments'] != null
          ? List<Map<String, dynamic>>.from(json['active_instruments'])
              .map((i) => TradingInstrument.fromJson(i))
              .toList()
          : [],
      isTradingEnabled: json['is_trading_enabled'] ?? false,
      currentStrategyName: json['current_strategy_name'],
      riskLevel: json['risk_level'],
      runningTimeFormatted: json['running_time_formatted'],
      additionalInfo: json['additional_info'] ?? {},
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'is_running': isRunning,
      'start_time': startTime?.toIso8601String(),
      'account_id': accountId,
      'account_type': accountType,
      'account_balance': accountBalance,
      'account_equity': accountEquity,
      'account_margin': accountMargin,
      'open_positions_count': openPositionsCount,
      'total_positions_today': totalPositionsToday,
      'active_instruments': activeInstruments.map((i) => i.toJson()).toList(),
      'is_trading_enabled': isTradingEnabled,
      'current_strategy_name': currentStrategyName,
      'risk_level': riskLevel,
      'running_time_formatted': runningTimeFormatted,
      'additional_info': additionalInfo,
    };
  }
  
  BotStatus copyWith({
    bool? isRunning,
    DateTime? startTime,
    String? accountId,
    String? accountType,
    double? accountBalance,
    double? accountEquity,
    double? accountMargin,
    int? openPositionsCount,
    int? totalPositionsToday,
    List<TradingInstrument>? activeInstruments,
    bool? isTradingEnabled,
    String? currentStrategyName,
    int? riskLevel,
    String? runningTimeFormatted,
    Map<String, dynamic>? additionalInfo,
  }) {
    return BotStatus(
      isRunning: isRunning ?? this.isRunning,
      startTime: startTime ?? this.startTime,
      accountId: accountId ?? this.accountId,
      accountType: accountType ?? this.accountType,
      accountBalance: accountBalance ?? this.accountBalance,
      accountEquity: accountEquity ?? this.accountEquity,
      accountMargin: accountMargin ?? this.accountMargin,
      openPositionsCount: openPositionsCount ?? this.openPositionsCount,
      totalPositionsToday: totalPositionsToday ?? this.totalPositionsToday,
      activeInstruments: activeInstruments ?? this.activeInstruments,
      isTradingEnabled: isTradingEnabled ?? this.isTradingEnabled,
      currentStrategyName: currentStrategyName ?? this.currentStrategyName,
      riskLevel: riskLevel ?? this.riskLevel,
      runningTimeFormatted: runningTimeFormatted ?? this.runningTimeFormatted,
      additionalInfo: additionalInfo ?? this.additionalInfo,
    );
  }
  
  @override
  List<Object?> get props => [
    isRunning,
    startTime,
    accountId,
    accountType,
    accountBalance,
    accountEquity,
    accountMargin,
    openPositionsCount,
    totalPositionsToday,
    activeInstruments,
    isTradingEnabled,
    currentStrategyName,
    riskLevel,
    runningTimeFormatted,
    additionalInfo,
  ];
}

/// Represents the trading performance metrics
class TradingPerformance extends Equatable {
  final double dailyPL;
  final double dailyPLPercentage;
  final double weeklyPL;
  final double weeklyPLPercentage;
  final double monthlyPL;
  final double monthlyPLPercentage;
  final double drawdown;
  final double maxDrawdown;
  final double winRate;
  final int winCount;
  final int lossCount;
  final double profitFactor;
  final int totalTradesToday;
  final double averageTradeTime;
  final Map<String, double> instrumentPerformance;
  
  const TradingPerformance({
    required this.dailyPL,
    required this.dailyPLPercentage,
    required this.weeklyPL,
    required this.weeklyPLPercentage,
    required this.monthlyPL,
    required this.monthlyPLPercentage,
    required this.drawdown,
    required this.maxDrawdown,
    required this.winRate,
    required this.winCount,
    required this.lossCount,
    required this.profitFactor,
    required this.totalTradesToday,
    required this.averageTradeTime,
    required this.instrumentPerformance,
  });
  
  factory TradingPerformance.fromJson(Map<String, dynamic> json) {
    final instrumentPerf = <String, double>{};
    if (json['instrument_performance'] != null) {
      json['instrument_performance'].forEach((key, value) {
        instrumentPerf[key] = value.toDouble();
      });
    }
    
    return TradingPerformance(
      dailyPL: json['daily_pl']?.toDouble() ?? 0.0,
      dailyPLPercentage: json['daily_pl_percentage']?.toDouble() ?? 0.0,
      weeklyPL: json['weekly_pl']?.toDouble() ?? 0.0,
      weeklyPLPercentage: json['weekly_pl_percentage']?.toDouble() ?? 0.0,
      monthlyPL: json['monthly_pl']?.toDouble() ?? 0.0,
      monthlyPLPercentage: json['monthly_pl_percentage']?.toDouble() ?? 0.0,
      drawdown: json['drawdown']?.toDouble() ?? 0.0,
      maxDrawdown: json['max_drawdown']?.toDouble() ?? 0.0,
      winRate: json['win_rate']?.toDouble() ?? 0.0,
      winCount: json['win_count'] ?? 0,
      lossCount: json['loss_count'] ?? 0,
      profitFactor: json['profit_factor']?.toDouble() ?? 0.0,
      totalTradesToday: json['total_trades_today'] ?? 0,
      averageTradeTime: json['average_trade_time']?.toDouble() ?? 0.0,
      instrumentPerformance: instrumentPerf,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'daily_pl': dailyPL,
      'daily_pl_percentage': dailyPLPercentage,
      'weekly_pl': weeklyPL,
      'weekly_pl_percentage': weeklyPLPercentage,
      'monthly_pl': monthlyPL,
      'monthly_pl_percentage': monthlyPLPercentage,
      'drawdown': drawdown,
      'max_drawdown': maxDrawdown,
      'win_rate': winRate,
      'win_count': winCount,
      'loss_count': lossCount,
      'profit_factor': profitFactor,
      'total_trades_today': totalTradesToday,
      'average_trade_time': averageTradeTime,
      'instrument_performance': instrumentPerformance,
    };
  }
  
  /// Returns true if daily performance is positive
  bool get isDailyPositive => dailyPL > 0;
  
  /// Returns true if weekly performance is positive
  bool get isWeeklyPositive => weeklyPL > 0;
  
  /// Returns true if monthly performance is positive
  bool get isMonthlyPositive => monthlyPL > 0;
  
  /// Returns the best performing instrument
  String? get bestPerformingInstrument {
    if (instrumentPerformance.isEmpty) return null;
    
    return instrumentPerformance.entries
        .reduce((a, b) => a.value > b.value ? a : b)
        .key;
  }
  
  /// Returns the worst performing instrument
  String? get worstPerformingInstrument {
    if (instrumentPerformance.isEmpty) return null;
    
    return instrumentPerformance.entries
        .reduce((a, b) => a.value < b.value ? a : b)
        .key;
  }
  
  @override
  List<Object?> get props => [
    dailyPL,
    dailyPLPercentage,
    weeklyPL,
    weeklyPLPercentage,
    monthlyPL,
    monthlyPLPercentage,
    drawdown,
    maxDrawdown,
    winRate,
    winCount,
    lossCount,
    profitFactor,
    totalTradesToday,
    averageTradeTime,
    instrumentPerformance,
  ];
}
