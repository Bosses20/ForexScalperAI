import 'dart:convert';

/// Represents the MT5 Trading Bot settings
class BotSettings {
  // MT5 Connection Settings
  final MT5ConnectionSettings mt5Connection;
  
  // Trading Settings
  final TradingSettings trading;
  
  // Risk Management Settings
  final RiskManagementSettings riskManagement;
  
  // Strategy Settings
  final StrategySettings strategies;
  
  BotSettings({
    required this.mt5Connection,
    required this.trading,
    required this.riskManagement,
    required this.strategies,
  });
  
  /// Creates settings with default values
  factory BotSettings.defaults() {
    return BotSettings(
      mt5Connection: MT5ConnectionSettings.defaults(),
      trading: TradingSettings.defaults(),
      riskManagement: RiskManagementSettings.defaults(),
      strategies: StrategySettings.defaults(),
    );
  }
  
  /// Creates settings from JSON
  factory BotSettings.fromJson(Map<String, dynamic> json) {
    return BotSettings(
      mt5Connection: MT5ConnectionSettings.fromJson(json['mt5_connection'] ?? {}),
      trading: TradingSettings.fromJson(json['trading'] ?? {}),
      riskManagement: RiskManagementSettings.fromJson(json['risk_management'] ?? {}),
      strategies: StrategySettings.fromJson(json['strategies'] ?? {}),
    );
  }
  
  /// Converts settings to JSON
  Map<String, dynamic> toJson() {
    return {
      'mt5_connection': mt5Connection.toJson(),
      'trading': trading.toJson(),
      'risk_management': riskManagement.toJson(),
      'strategies': strategies.toJson(),
    };
  }
  
  /// Creates a copy with modified values
  BotSettings copyWith({
    MT5ConnectionSettings? mt5Connection,
    TradingSettings? trading,
    RiskManagementSettings? riskManagement,
    StrategySettings? strategies,
  }) {
    return BotSettings(
      mt5Connection: mt5Connection ?? this.mt5Connection,
      trading: trading ?? this.trading,
      riskManagement: riskManagement ?? this.riskManagement,
      strategies: strategies ?? this.strategies,
    );
  }
  
  /// Serializes settings to JSON string
  String serialize() {
    return jsonEncode(toJson());
  }
  
  /// Deserializes settings from JSON string
  static BotSettings deserialize(String json) {
    return BotSettings.fromJson(jsonDecode(json));
  }
}

/// Settings for MT5 Connection
class MT5ConnectionSettings {
  final int maxRetries;
  final int retryDelay;
  final int pingInterval;
  
  MT5ConnectionSettings({
    required this.maxRetries,
    required this.retryDelay,
    required this.pingInterval,
  });
  
  factory MT5ConnectionSettings.defaults() {
    return MT5ConnectionSettings(
      maxRetries: 3,
      retryDelay: 5,
      pingInterval: 60,
    );
  }
  
  factory MT5ConnectionSettings.fromJson(Map<String, dynamic> json) {
    return MT5ConnectionSettings(
      maxRetries: json['max_retries'] ?? 3,
      retryDelay: json['retry_delay'] ?? 5,
      pingInterval: json['ping_interval'] ?? 60,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'max_retries': maxRetries,
      'retry_delay': retryDelay,
      'ping_interval': pingInterval,
    };
  }
  
  MT5ConnectionSettings copyWith({
    int? maxRetries,
    int? retryDelay,
    int? pingInterval,
  }) {
    return MT5ConnectionSettings(
      maxRetries: maxRetries ?? this.maxRetries,
      retryDelay: retryDelay ?? this.retryDelay,
      pingInterval: pingInterval ?? this.pingInterval,
    );
  }
}

/// Trading Instrument (Currency Pair or Synthetic Index)
class TradingInstrument {
  final String name;
  final String type; // forex or synthetic
  final String? subType; // volatility, crash_boom, step
  final String description;
  final bool enabled;
  
  TradingInstrument({
    required this.name,
    required this.type,
    this.subType,
    required this.description,
    this.enabled = true,
  });
  
  factory TradingInstrument.fromJson(Map<String, dynamic> json) {
    return TradingInstrument(
      name: json['name'] ?? '',
      type: json['type'] ?? 'forex',
      subType: json['sub_type'],
      description: json['description'] ?? '',
      enabled: json['enabled'] ?? true,
    );
  }
  
  Map<String, dynamic> toJson() {
    final map = {
      'name': name,
      'type': type,
      'description': description,
      'enabled': enabled,
    };
    
    if (subType != null) {
      map['sub_type'] = subType;
    }
    
    return map;
  }
  
  TradingInstrument copyWith({
    String? name,
    String? type,
    String? subType,
    String? description,
    bool? enabled,
  }) {
    return TradingInstrument(
      name: name ?? this.name,
      type: type ?? this.type,
      subType: subType ?? this.subType,
      description: description ?? this.description,
      enabled: enabled ?? this.enabled,
    );
  }
}

/// Trading Session
class TradingSession {
  final String session;
  final List<int> hours;
  final String description;
  final bool enabled;
  
  TradingSession({
    required this.session,
    required this.hours,
    required this.description,
    this.enabled = true,
  });
  
  factory TradingSession.fromJson(Map<String, dynamic> json) {
    return TradingSession(
      session: json['session'] ?? '',
      hours: (json['hours'] as List?)?.map((e) => e as int).toList() ?? [0, 24],
      description: json['description'] ?? '',
      enabled: json['enabled'] ?? true,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'session': session,
      'hours': hours,
      'description': description,
      'enabled': enabled,
    };
  }
  
  TradingSession copyWith({
    String? session,
    List<int>? hours,
    String? description,
    bool? enabled,
  }) {
    return TradingSession(
      session: session ?? this.session,
      hours: hours ?? this.hours,
      description: description ?? this.description,
      enabled: enabled ?? this.enabled,
    );
  }
}

/// Trading Settings
class TradingSettings {
  final List<TradingInstrument> instruments;
  final List<String> timeframes;
  final String strategyTimeframe;
  final int updateInterval;
  final Map<String, List<TradingSession>> tradeSessions;
  
  TradingSettings({
    required this.instruments,
    required this.timeframes,
    required this.strategyTimeframe,
    required this.updateInterval,
    required this.tradeSessions,
  });
  
  factory TradingSettings.defaults() {
    return TradingSettings(
      instruments: [
        TradingInstrument(name: 'EURUSD', type: 'forex', description: 'Euro vs US Dollar'),
        TradingInstrument(name: 'GBPUSD', type: 'forex', description: 'British Pound vs US Dollar'),
        TradingInstrument(name: 'Volatility 75 Index', type: 'synthetic', subType: 'volatility', description: '75% volatility index'),
      ],
      timeframes: ['M1', 'M5', 'M15'],
      strategyTimeframe: 'M5',
      updateInterval: 1,
      tradeSessions: {
        'forex': [
          TradingSession(
            session: 'london_new_york_overlap',
            hours: [13, 17],
            description: 'London/NY overlap - highest liquidity period',
          ),
        ],
        'synthetic': [
          TradingSession(
            session: 'all_day',
            hours: [0, 24],
            description: '24/7 trading available',
          ),
        ],
      },
    );
  }
  
  factory TradingSettings.fromJson(Map<String, dynamic> json) {
    // Parse instruments
    List<TradingInstrument> instruments = [];
    if (json['instruments'] != null) {
      for (var item in json['instruments']) {
        instruments.add(TradingInstrument.fromJson(item));
      }
    }
    
    // Parse trade sessions
    Map<String, List<TradingSession>> tradeSessions = {};
    if (json['trade_sessions'] != null) {
      for (var entry in (json['trade_sessions'] as Map<String, dynamic>).entries) {
        List<TradingSession> sessions = [];
        for (var session in entry.value) {
          sessions.add(TradingSession.fromJson(session));
        }
        tradeSessions[entry.key] = sessions;
      }
    }
    
    return TradingSettings(
      instruments: instruments,
      timeframes: (json['timeframes'] as List?)?.map((e) => e as String).toList() 
        ?? ['M1', 'M5', 'M15'],
      strategyTimeframe: json['strategy_timeframe'] ?? 'M5',
      updateInterval: json['update_interval'] ?? 1,
      tradeSessions: tradeSessions,
    );
  }
  
  Map<String, dynamic> toJson() {
    // Convert instruments to JSON
    List<Map<String, dynamic>> instrumentsJson = [];
    for (var instrument in instruments) {
      instrumentsJson.add(instrument.toJson());
    }
    
    // Convert trade sessions to JSON
    Map<String, List<Map<String, dynamic>>> tradeSessionsJson = {};
    for (var entry in tradeSessions.entries) {
      List<Map<String, dynamic>> sessions = [];
      for (var session in entry.value) {
        sessions.add(session.toJson());
      }
      tradeSessionsJson[entry.key] = sessions;
    }
    
    return {
      'instruments': instrumentsJson,
      'timeframes': timeframes,
      'strategy_timeframe': strategyTimeframe,
      'update_interval': updateInterval,
      'trade_sessions': tradeSessionsJson,
    };
  }
  
  TradingSettings copyWith({
    List<TradingInstrument>? instruments,
    List<String>? timeframes,
    String? strategyTimeframe,
    int? updateInterval,
    Map<String, List<TradingSession>>? tradeSessions,
  }) {
    return TradingSettings(
      instruments: instruments ?? this.instruments,
      timeframes: timeframes ?? this.timeframes,
      strategyTimeframe: strategyTimeframe ?? this.strategyTimeframe,
      updateInterval: updateInterval ?? this.updateInterval,
      tradeSessions: tradeSessions ?? this.tradeSessions,
    );
  }
}

/// Risk Management Settings
class RiskManagementSettings {
  final double maxRiskPerTrade;
  final double maxDailyRisk;
  final double maxDrawdownPercent;
  final double maxOpenTrades;
  final StopLossSettings stopLoss;
  final TakeProfitSettings takeProfit;
  
  RiskManagementSettings({
    required this.maxRiskPerTrade,
    required this.maxDailyRisk,
    required this.maxDrawdownPercent,
    required this.maxOpenTrades,
    required this.stopLoss,
    required this.takeProfit,
  });
  
  factory RiskManagementSettings.defaults() {
    return RiskManagementSettings(
      maxRiskPerTrade: 0.01,
      maxDailyRisk: 0.05,
      maxDrawdownPercent: 0.15,
      maxOpenTrades: 5,
      stopLoss: StopLossSettings.defaults(),
      takeProfit: TakeProfitSettings.defaults(),
    );
  }
  
  factory RiskManagementSettings.fromJson(Map<String, dynamic> json) {
    return RiskManagementSettings(
      maxRiskPerTrade: json['max_risk_per_trade']?.toDouble() ?? 0.01,
      maxDailyRisk: json['max_daily_risk']?.toDouble() ?? 0.05,
      maxDrawdownPercent: json['max_drawdown_percent']?.toDouble() ?? 0.15,
      maxOpenTrades: json['max_open_trades']?.toDouble() ?? 5,
      stopLoss: StopLossSettings.fromJson(json['stop_loss'] ?? {}),
      takeProfit: TakeProfitSettings.fromJson(json['take_profit'] ?? {}),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'max_risk_per_trade': maxRiskPerTrade,
      'max_daily_risk': maxDailyRisk,
      'max_drawdown_percent': maxDrawdownPercent,
      'max_open_trades': maxOpenTrades,
      'stop_loss': stopLoss.toJson(),
      'take_profit': takeProfit.toJson(),
    };
  }
  
  RiskManagementSettings copyWith({
    double? maxRiskPerTrade,
    double? maxDailyRisk,
    double? maxDrawdownPercent,
    double? maxOpenTrades,
    StopLossSettings? stopLoss,
    TakeProfitSettings? takeProfit,
  }) {
    return RiskManagementSettings(
      maxRiskPerTrade: maxRiskPerTrade ?? this.maxRiskPerTrade,
      maxDailyRisk: maxDailyRisk ?? this.maxDailyRisk,
      maxDrawdownPercent: maxDrawdownPercent ?? this.maxDrawdownPercent,
      maxOpenTrades: maxOpenTrades ?? this.maxOpenTrades,
      stopLoss: stopLoss ?? this.stopLoss,
      takeProfit: takeProfit ?? this.takeProfit,
    );
  }
}

/// Stop Loss Settings
class StopLossSettings {
  final String defaultStrategy; // fixed, atr, structure
  final double fixedSlPips;
  final double atrMultiplier;
  
  StopLossSettings({
    required this.defaultStrategy,
    required this.fixedSlPips,
    required this.atrMultiplier,
  });
  
  factory StopLossSettings.defaults() {
    return StopLossSettings(
      defaultStrategy: 'atr',
      fixedSlPips: 15,
      atrMultiplier: 1.5,
    );
  }
  
  factory StopLossSettings.fromJson(Map<String, dynamic> json) {
    return StopLossSettings(
      defaultStrategy: json['default_strategy'] ?? 'atr',
      fixedSlPips: json['fixed_sl_pips']?.toDouble() ?? 15,
      atrMultiplier: json['atr_multiplier']?.toDouble() ?? 1.5,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'default_strategy': defaultStrategy,
      'fixed_sl_pips': fixedSlPips,
      'atr_multiplier': atrMultiplier,
    };
  }
  
  StopLossSettings copyWith({
    String? defaultStrategy,
    double? fixedSlPips,
    double? atrMultiplier,
  }) {
    return StopLossSettings(
      defaultStrategy: defaultStrategy ?? this.defaultStrategy,
      fixedSlPips: fixedSlPips ?? this.fixedSlPips,
      atrMultiplier: atrMultiplier ?? this.atrMultiplier,
    );
  }
}

/// Take Profit Settings
class TakeProfitSettings {
  final String method; // fixed, risk_ratio, structure
  final double fixedTpPips;
  final double riskRewardRatio;
  final Map<String, double> multipleTargets;
  
  TakeProfitSettings({
    required this.method,
    required this.fixedTpPips,
    required this.riskRewardRatio,
    required this.multipleTargets,
  });
  
  factory TakeProfitSettings.defaults() {
    return TakeProfitSettings(
      method: 'risk_ratio',
      fixedTpPips: 30,
      riskRewardRatio: 2.0,
      multipleTargets: {
        'tp1_ratio': 1.0,
        'tp2_ratio': 2.0,
        'tp1_size': 0.5,
      },
    );
  }
  
  factory TakeProfitSettings.fromJson(Map<String, dynamic> json) {
    // Extract multiple targets
    Map<String, double> multipleTargets = {};
    if (json['multiple_targets'] != null) {
      for (var entry in (json['multiple_targets'] as Map<String, dynamic>).entries) {
        multipleTargets[entry.key] = entry.value.toDouble();
      }
    }
    
    return TakeProfitSettings(
      method: json['method'] ?? 'risk_ratio',
      fixedTpPips: json['fixed_tp_pips']?.toDouble() ?? 30,
      riskRewardRatio: json['risk_reward_ratio']?.toDouble() ?? 2.0,
      multipleTargets: multipleTargets.isEmpty ? {
        'tp1_ratio': 1.0,
        'tp2_ratio': 2.0,
        'tp1_size': 0.5,
      } : multipleTargets,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'method': method,
      'fixed_tp_pips': fixedTpPips,
      'risk_reward_ratio': riskRewardRatio,
      'multiple_targets': multipleTargets,
    };
  }
  
  TakeProfitSettings copyWith({
    String? method,
    double? fixedTpPips,
    double? riskRewardRatio,
    Map<String, double>? multipleTargets,
  }) {
    return TakeProfitSettings(
      method: method ?? this.method,
      fixedTpPips: fixedTpPips ?? this.fixedTpPips,
      riskRewardRatio: riskRewardRatio ?? this.riskRewardRatio,
      multipleTargets: multipleTargets ?? this.multipleTargets,
    );
  }
}

/// Strategy Settings
class StrategySettings {
  final Map<String, bool> enabledStrategies;
  final Map<String, dynamic> strategyParameters;
  
  StrategySettings({
    required this.enabledStrategies,
    required this.strategyParameters,
  });
  
  factory StrategySettings.defaults() {
    return StrategySettings(
      enabledStrategies: {
        'moving_average_cross': true,
        'break_and_retest': true,
        'break_of_structure': true,
        'jhook_pattern': true,
        'ma_rsi_combo': true,
        'stochastic_cross': true,
      },
      strategyParameters: {
        'moving_average_cross': {
          'fast_ma_period': 5,
          'slow_ma_period': 20,
          'ma_type': 'ema',
        },
        'break_and_retest': {
          'lookback_periods': 50,
          'min_level_strength': 3,
        },
        'break_of_structure': {
          'lookback_periods': 20,
          'min_swing_size_pips': 5,
        },
        'jhook_pattern': {
          'lookback_period': 50,
          'trend_strength': 10,
        },
        'ma_rsi_combo': {
          'ma_period': 21,
          'rsi_period': 14,
          'rsi_overbought': 70,
          'rsi_oversold': 30,
        },
        'stochastic_cross': {
          'k_period': 14,
          'd_period': 3,
          'slowing': 3,
          'overbought': 80,
          'oversold': 20,
        },
      },
    );
  }
  
  factory StrategySettings.fromJson(Map<String, dynamic> json) {
    // Extract enabled strategies
    Map<String, bool> enabledStrategies = {};
    if (json['enabled_strategies'] != null) {
      for (var entry in (json['enabled_strategies'] as Map<String, dynamic>).entries) {
        enabledStrategies[entry.key] = entry.value as bool;
      }
    }
    
    // Extract strategy parameters
    Map<String, dynamic> strategyParameters = {};
    if (json['strategy_parameters'] != null) {
      strategyParameters = Map<String, dynamic>.from(json['strategy_parameters']);
    }
    
    return StrategySettings(
      enabledStrategies: enabledStrategies.isEmpty ? {
        'moving_average_cross': true,
        'break_and_retest': true,
        'break_of_structure': true,
        'jhook_pattern': true,
        'ma_rsi_combo': true,
        'stochastic_cross': true,
      } : enabledStrategies,
      strategyParameters: strategyParameters,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'enabled_strategies': enabledStrategies,
      'strategy_parameters': strategyParameters,
    };
  }
  
  StrategySettings copyWith({
    Map<String, bool>? enabledStrategies,
    Map<String, dynamic>? strategyParameters,
  }) {
    return StrategySettings(
      enabledStrategies: enabledStrategies ?? this.enabledStrategies,
      strategyParameters: strategyParameters ?? this.strategyParameters,
    );
  }
}
