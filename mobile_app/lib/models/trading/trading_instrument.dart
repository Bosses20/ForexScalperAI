import 'package:equatable/equatable.dart';

enum InstrumentType {
  forex,
  syntheticIndices,
  crypto,
  commodities,
  stocks,
  unknown
}

enum TradingSession {
  asian,
  european,
  american,
  overlapped,
  allDay,
  custom,
  none
}

class TradingInstrument extends Equatable {
  final String symbol;
  final InstrumentType type;
  final List<TradingSession> activeSessions;
  final double pipValue;
  final double spread;
  final double commissionPerLot;
  final bool isActive;
  final List<double> priceHistory; // Recent prices for sparkline
  final Map<String, double> correlations; // Correlations with other instruments
  final double volatility; // Current volatility measure
  final double strategyStrength; // How well current strategies perform on this instrument
  final Map<String, dynamic> additionalProperties;

  const TradingInstrument({
    required this.symbol,
    this.type = InstrumentType.unknown,
    this.activeSessions = const [TradingSession.none],
    this.pipValue = 0.0,
    this.spread = 0.0,
    this.commissionPerLot = 0.0,
    this.isActive = false,
    this.priceHistory = const [],
    this.correlations = const {},
    this.volatility = 0.0,
    this.strategyStrength = 0.0,
    this.additionalProperties = const {},
  });

  factory TradingInstrument.fromJson(Map<String, dynamic> json) {
    return TradingInstrument(
      symbol: json['symbol'] ?? '',
      type: _parseInstrumentType(json['type']),
      activeSessions: _parseActiveSessions(json['active_sessions']),
      pipValue: json['pip_value']?.toDouble() ?? 0.0,
      spread: json['spread']?.toDouble() ?? 0.0,
      commissionPerLot: json['commission_per_lot']?.toDouble() ?? 0.0,
      isActive: json['is_active'] ?? false,
      priceHistory: _parsePriceHistory(json['price_history']),
      correlations: _parseCorrelations(json['correlations']),
      volatility: json['volatility']?.toDouble() ?? 0.0,
      strategyStrength: json['strategy_strength']?.toDouble() ?? 0.0,
      additionalProperties: json['additional_properties'] ?? {},
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'symbol': symbol,
      'type': type.toString().split('.').last,
      'active_sessions': activeSessions.map((s) => s.toString().split('.').last).toList(),
      'pip_value': pipValue,
      'spread': spread,
      'commission_per_lot': commissionPerLot,
      'is_active': isActive,
      'price_history': priceHistory,
      'correlations': correlations,
      'volatility': volatility,
      'strategy_strength': strategyStrength,
      'additional_properties': additionalProperties,
    };
  }

  static InstrumentType _parseInstrumentType(String? value) {
    if (value == null) return InstrumentType.unknown;
    
    switch (value.toLowerCase()) {
      case 'forex': return InstrumentType.forex;
      case 'synthetic_indices': return InstrumentType.syntheticIndices;
      case 'crypto': return InstrumentType.crypto;
      case 'commodities': return InstrumentType.commodities;
      case 'stocks': return InstrumentType.stocks;
      default: return InstrumentType.unknown;
    }
  }

  static List<TradingSession> _parseActiveSessions(dynamic value) {
    if (value == null || !(value is List)) return [TradingSession.none];
    
    List<TradingSession> sessions = [];
    for (var session in value) {
      switch ((session as String).toLowerCase()) {
        case 'asian': sessions.add(TradingSession.asian); break;
        case 'european': sessions.add(TradingSession.european); break;
        case 'american': sessions.add(TradingSession.american); break;
        case 'overlapped': sessions.add(TradingSession.overlapped); break;
        case 'all_day': sessions.add(TradingSession.allDay); break;
        case 'custom': sessions.add(TradingSession.custom); break;
        default: sessions.add(TradingSession.none); break;
      }
    }
    
    return sessions.isEmpty ? [TradingSession.none] : sessions;
  }

  static List<double> _parsePriceHistory(dynamic value) {
    if (value == null || !(value is List)) return [];
    
    List<double> prices = [];
    for (var price in value) {
      if (price is num) {
        prices.add(price.toDouble());
      }
    }
    
    return prices;
  }

  static Map<String, double> _parseCorrelations(dynamic value) {
    if (value == null || !(value is Map)) return {};
    
    Map<String, double> correlations = {};
    (value as Map).forEach((key, val) {
      if (val is num && key is String) {
        correlations[key] = val.toDouble();
      }
    });
    
    return correlations;
  }

  TradingInstrument copyWith({
    String? symbol,
    InstrumentType? type,
    List<TradingSession>? activeSessions,
    double? pipValue,
    double? spread,
    double? commissionPerLot,
    bool? isActive,
    List<double>? priceHistory,
    Map<String, double>? correlations,
    double? volatility,
    double? strategyStrength,
    Map<String, dynamic>? additionalProperties,
  }) {
    return TradingInstrument(
      symbol: symbol ?? this.symbol,
      type: type ?? this.type,
      activeSessions: activeSessions ?? this.activeSessions,
      pipValue: pipValue ?? this.pipValue,
      spread: spread ?? this.spread,
      commissionPerLot: commissionPerLot ?? this.commissionPerLot,
      isActive: isActive ?? this.isActive,
      priceHistory: priceHistory ?? this.priceHistory,
      correlations: correlations ?? this.correlations,
      volatility: volatility ?? this.volatility,
      strategyStrength: strategyStrength ?? this.strategyStrength,
      additionalProperties: additionalProperties ?? this.additionalProperties,
    );
  }

  @override
  List<Object?> get props => [
    symbol,
    type,
    activeSessions,
    pipValue,
    spread,
    commissionPerLot,
    isActive,
    priceHistory,
    correlations,
    volatility,
    strategyStrength,
    additionalProperties,
  ];
}
