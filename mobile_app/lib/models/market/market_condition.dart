import 'package:equatable/equatable.dart';

enum TrendType {
  bullish,
  bearish,
  ranging,
  choppy,
  unknown
}

enum VolatilityLevel {
  low,
  medium,
  high,
  unknown
}

enum LiquidityLevel {
  low,
  medium,
  high,
  unknown
}

class MarketCondition extends Equatable {
  final TrendType trend;
  final VolatilityLevel volatility;
  final LiquidityLevel liquidity;
  final double confidenceScore; // 0-100 score indicating trading favorability
  final DateTime timestamp;
  final Map<String, dynamic> additionalMetrics;

  const MarketCondition({
    this.trend = TrendType.unknown,
    this.volatility = VolatilityLevel.unknown,
    this.liquidity = LiquidityLevel.unknown,
    this.confidenceScore = 0.0,
    DateTime? timestamp,
    this.additionalMetrics = const {},
  }) : timestamp = timestamp ?? DateTime.now();

  factory MarketCondition.fromJson(Map<String, dynamic> json) {
    return MarketCondition(
      trend: _parseTrendType(json['trend']),
      volatility: _parseVolatilityLevel(json['volatility']),
      liquidity: _parseLiquidityLevel(json['liquidity']),
      confidenceScore: json['confidence_score'] ?? 0.0,
      timestamp: json['timestamp'] != null 
          ? DateTime.parse(json['timestamp']) 
          : DateTime.now(),
      additionalMetrics: json['additional_metrics'] ?? {},
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'trend': trend.toString().split('.').last,
      'volatility': volatility.toString().split('.').last,
      'liquidity': liquidity.toString().split('.').last,
      'confidence_score': confidenceScore,
      'timestamp': timestamp.toIso8601String(),
      'additional_metrics': additionalMetrics,
    };
  }

  static TrendType _parseTrendType(String? value) {
    if (value == null) return TrendType.unknown;
    
    switch (value.toLowerCase()) {
      case 'bullish': return TrendType.bullish;
      case 'bearish': return TrendType.bearish;
      case 'ranging': return TrendType.ranging;
      case 'choppy': return TrendType.choppy;
      default: return TrendType.unknown;
    }
  }

  static VolatilityLevel _parseVolatilityLevel(String? value) {
    if (value == null) return VolatilityLevel.unknown;
    
    switch (value.toLowerCase()) {
      case 'low': return VolatilityLevel.low;
      case 'medium': return VolatilityLevel.medium;
      case 'high': return VolatilityLevel.high;
      default: return VolatilityLevel.unknown;
    }
  }

  static LiquidityLevel _parseLiquidityLevel(String? value) {
    if (value == null) return LiquidityLevel.unknown;
    
    switch (value.toLowerCase()) {
      case 'low': return LiquidityLevel.low;
      case 'medium': return LiquidityLevel.medium;
      case 'high': return LiquidityLevel.high;
      default: return LiquidityLevel.unknown;
    }
  }

  bool isTradingFavorable() {
    return confidenceScore >= 70.0;
  }

  @override
  List<Object?> get props => [
    trend, 
    volatility, 
    liquidity, 
    confidenceScore, 
    timestamp,
    additionalMetrics
  ];
}
