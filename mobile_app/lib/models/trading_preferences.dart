class TradingPreferences {
  // General settings
  final bool autoConnectToLastServer;
  final bool autoStartTradingOnFavorableConditions;
  
  // Risk management
  final double maxRiskPerTrade;
  final double maxDailyDrawdown;
  final double defaultLotSize;
  
  // Strategy preferences
  final bool adaptToMarketConditions;
  final List<String> preferredStrategies;
  final List<String> preferredCurrencyPairs;
  
  // Session preferences
  final bool tradeAsianSession;
  final bool tradeEuropeanSession;
  final bool tradeAmericanSession;
  
  // Notification settings
  final bool notifyOnTradeExecuted;
  final bool notifyOnTradeCompleted;
  final bool notifyOnError;
  final bool notifyOnMarketConditionChange;

  TradingPreferences({
    this.autoConnectToLastServer = true,
    this.autoStartTradingOnFavorableConditions = false,
    this.maxRiskPerTrade = 1.0,
    this.maxDailyDrawdown = 3.0,
    this.defaultLotSize = 0.01,
    this.adaptToMarketConditions = true,
    this.preferredStrategies = const ['scalping', 'trend_following'],
    this.preferredCurrencyPairs = const ['EURUSD', 'GBPUSD', 'USDJPY'],
    this.tradeAsianSession = false,
    this.tradeEuropeanSession = true,
    this.tradeAmericanSession = true,
    this.notifyOnTradeExecuted = true,
    this.notifyOnTradeCompleted = true,
    this.notifyOnError = true,
    this.notifyOnMarketConditionChange = false,
  });

  TradingPreferences copyWith({
    bool? autoConnectToLastServer,
    bool? autoStartTradingOnFavorableConditions,
    double? maxRiskPerTrade,
    double? maxDailyDrawdown,
    double? defaultLotSize,
    bool? adaptToMarketConditions,
    List<String>? preferredStrategies,
    List<String>? preferredCurrencyPairs,
    bool? tradeAsianSession,
    bool? tradeEuropeanSession,
    bool? tradeAmericanSession,
    bool? notifyOnTradeExecuted,
    bool? notifyOnTradeCompleted,
    bool? notifyOnError,
    bool? notifyOnMarketConditionChange,
  }) {
    return TradingPreferences(
      autoConnectToLastServer: autoConnectToLastServer ?? this.autoConnectToLastServer,
      autoStartTradingOnFavorableConditions: autoStartTradingOnFavorableConditions ?? this.autoStartTradingOnFavorableConditions,
      maxRiskPerTrade: maxRiskPerTrade ?? this.maxRiskPerTrade,
      maxDailyDrawdown: maxDailyDrawdown ?? this.maxDailyDrawdown,
      defaultLotSize: defaultLotSize ?? this.defaultLotSize,
      adaptToMarketConditions: adaptToMarketConditions ?? this.adaptToMarketConditions,
      preferredStrategies: preferredStrategies ?? this.preferredStrategies,
      preferredCurrencyPairs: preferredCurrencyPairs ?? this.preferredCurrencyPairs,
      tradeAsianSession: tradeAsianSession ?? this.tradeAsianSession,
      tradeEuropeanSession: tradeEuropeanSession ?? this.tradeEuropeanSession,
      tradeAmericanSession: tradeAmericanSession ?? this.tradeAmericanSession,
      notifyOnTradeExecuted: notifyOnTradeExecuted ?? this.notifyOnTradeExecuted,
      notifyOnTradeCompleted: notifyOnTradeCompleted ?? this.notifyOnTradeCompleted,
      notifyOnError: notifyOnError ?? this.notifyOnError,
      notifyOnMarketConditionChange: notifyOnMarketConditionChange ?? this.notifyOnMarketConditionChange,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'autoConnectToLastServer': autoConnectToLastServer,
      'autoStartTradingOnFavorableConditions': autoStartTradingOnFavorableConditions,
      'maxRiskPerTrade': maxRiskPerTrade,
      'maxDailyDrawdown': maxDailyDrawdown,
      'defaultLotSize': defaultLotSize,
      'adaptToMarketConditions': adaptToMarketConditions,
      'preferredStrategies': preferredStrategies,
      'preferredCurrencyPairs': preferredCurrencyPairs,
      'tradeAsianSession': tradeAsianSession,
      'tradeEuropeanSession': tradeEuropeanSession,
      'tradeAmericanSession': tradeAmericanSession,
      'notifyOnTradeExecuted': notifyOnTradeExecuted,
      'notifyOnTradeCompleted': notifyOnTradeCompleted,
      'notifyOnError': notifyOnError,
      'notifyOnMarketConditionChange': notifyOnMarketConditionChange,
    };
  }

  factory TradingPreferences.fromJson(Map<String, dynamic> json) {
    return TradingPreferences(
      autoConnectToLastServer: json['autoConnectToLastServer'] ?? true,
      autoStartTradingOnFavorableConditions: json['autoStartTradingOnFavorableConditions'] ?? false,
      maxRiskPerTrade: json['maxRiskPerTrade']?.toDouble() ?? 1.0,
      maxDailyDrawdown: json['maxDailyDrawdown']?.toDouble() ?? 3.0,
      defaultLotSize: json['defaultLotSize']?.toDouble() ?? 0.01,
      adaptToMarketConditions: json['adaptToMarketConditions'] ?? true,
      preferredStrategies: List<String>.from(json['preferredStrategies'] ?? ['scalping', 'trend_following']),
      preferredCurrencyPairs: List<String>.from(json['preferredCurrencyPairs'] ?? ['EURUSD', 'GBPUSD', 'USDJPY']),
      tradeAsianSession: json['tradeAsianSession'] ?? false,
      tradeEuropeanSession: json['tradeEuropeanSession'] ?? true,
      tradeAmericanSession: json['tradeAmericanSession'] ?? true,
      notifyOnTradeExecuted: json['notifyOnTradeExecuted'] ?? true,
      notifyOnTradeCompleted: json['notifyOnTradeCompleted'] ?? true,
      notifyOnError: json['notifyOnError'] ?? true,
      notifyOnMarketConditionChange: json['notifyOnMarketConditionChange'] ?? false,
    );
  }
}
