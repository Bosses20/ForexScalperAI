import 'package:equatable/equatable.dart';

enum MarketTrend {
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
  normal,
  high,
  unknown
}

/// Represents the current market conditions as detected by the
/// MarketConditionDetector in the backend
class MarketCondition extends Equatable {
  final MarketTrend trend;
  final VolatilityLevel volatility;
  final LiquidityLevel liquidity;
  final double tradingFavorability;
  final double confidenceScore;
  final List<String> recommendedStrategies;
  final DateTime timestamp;
  final Map<String, dynamic> additionalMetrics;

  const MarketCondition({
    required this.trend,
    required this.volatility,
    required this.liquidity,
    required this.tradingFavorability,
    required this.confidenceScore,
    required this.recommendedStrategies,
    required this.timestamp,
    this.additionalMetrics = const {},
  });

  /// Parse from JSON response from the API
  factory MarketCondition.fromJson(Map<String, dynamic> json) {
    return MarketCondition(
      trend: _parseMarketTrend(json['trend']),
      volatility: _parseVolatilityLevel(json['volatility']),
      liquidity: _parseLiquidityLevel(json['liquidity']),
      tradingFavorability: json['trading_favorability']?.toDouble() ?? 0.0,
      confidenceScore: json['confidence_score']?.toDouble() ?? 0.0,
      recommendedStrategies: List<String>.from(json['recommended_strategies'] ?? []),
      timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
      additionalMetrics: json['additional_metrics'] ?? {},
    );
  }

  /// Convert to JSON for sending to the API
  Map<String, dynamic> toJson() {
    return {
      'trend': trend.toString().split('.').last,
      'volatility': volatility.toString().split('.').last,
      'liquidity': liquidity.toString().split('.').last,
      'trading_favorability': tradingFavorability,
      'confidence_score': confidenceScore,
      'recommended_strategies': recommendedStrategies,
      'timestamp': timestamp.toIso8601String(),
      'additional_metrics': additionalMetrics,
    };
  }

  /// Helper method to parse market trend from string
  static MarketTrend _parseMarketTrend(String? trendStr) {
    if (trendStr == null) return MarketTrend.unknown;
    
    switch (trendStr.toLowerCase()) {
      case 'bullish':
        return MarketTrend.bullish;
      case 'bearish':
        return MarketTrend.bearish;
      case 'ranging':
        return MarketTrend.ranging;
      case 'choppy':
        return MarketTrend.choppy;
      default:
        return MarketTrend.unknown;
    }
  }

  /// Helper method to parse volatility level from string
  static VolatilityLevel _parseVolatilityLevel(String? levelStr) {
    if (levelStr == null) return VolatilityLevel.unknown;
    
    switch (levelStr.toLowerCase()) {
      case 'low':
        return VolatilityLevel.low;
      case 'medium':
        return VolatilityLevel.medium;
      case 'high':
        return VolatilityLevel.high;
      default:
        return VolatilityLevel.unknown;
    }
  }

  /// Helper method to parse liquidity level from string
  static LiquidityLevel _parseLiquidityLevel(String? levelStr) {
    if (levelStr == null) return LiquidityLevel.unknown;
    
    switch (levelStr.toLowerCase()) {
      case 'low':
        return LiquidityLevel.low;
      case 'normal':
        return LiquidityLevel.normal;
      case 'high':
        return LiquidityLevel.high;
      default:
        return LiquidityLevel.unknown;
    }
  }

  /// Create a copy of this MarketCondition with given fields replaced with new values
  MarketCondition copyWith({
    MarketTrend? trend,
    VolatilityLevel? volatility,
    LiquidityLevel? liquidity,
    double? tradingFavorability,
    double? confidenceScore,
    List<String>? recommendedStrategies,
    DateTime? timestamp,
    Map<String, dynamic>? additionalMetrics,
  }) {
    return MarketCondition(
      trend: trend ?? this.trend,
      volatility: volatility ?? this.volatility,
      liquidity: liquidity ?? this.liquidity,
      tradingFavorability: tradingFavorability ?? this.tradingFavorability,
      confidenceScore: confidenceScore ?? this.confidenceScore,
      recommendedStrategies: recommendedStrategies ?? this.recommendedStrategies,
      timestamp: timestamp ?? this.timestamp,
      additionalMetrics: additionalMetrics ?? this.additionalMetrics,
    );
  }

  /// Returns true if market conditions are favorable for trading
  bool get isFavorableForTrading => tradingFavorability > 0.6;

  /// Gets a color indicator based on the current market trend
  /// Can be used with UI elements to visually represent the trend
  String get trendColorIndicator {
    switch (trend) {
      case MarketTrend.bullish:
        return '#00C853'; // Green
      case MarketTrend.bearish:
        return '#FF3D00'; // Red
      case MarketTrend.ranging:
        return '#1565C0'; // Blue
      case MarketTrend.choppy:
        return '#FFD600'; // Yellow
      case MarketTrend.unknown:
        return '#90A4AE'; // Gray
    }
  }

  /// Gets an icon name based on the current market trend
  /// Can be used with icon widgets to visually represent the trend
  String get trendIconName {
    switch (trend) {
      case MarketTrend.bullish:
        return 'trend_up';
      case MarketTrend.bearish:
        return 'trend_down';
      case MarketTrend.ranging:
        return 'trend_flat';
      case MarketTrend.choppy:
        return 'trend_zigzag';
      case MarketTrend.unknown:
        return 'trend_unknown';
    }
  }

  @override
  List<Object?> get props => [
    trend,
    volatility,
    liquidity,
    tradingFavorability,
    confidenceScore,
    recommendedStrategies,
    timestamp,
    additionalMetrics,
  ];
}

/// Model representing the correlation between trading instruments
class MarketCorrelation extends Equatable {
  final Map<String, Map<String, double>> correlationMatrix;
  final DateTime timestamp;
  
  const MarketCorrelation({
    required this.correlationMatrix,
    required this.timestamp,
  });
  
  factory MarketCorrelation.fromJson(Map<String, dynamic> json) {
    final matrix = <String, Map<String, double>>{};
    
    if (json['correlation_matrix'] != null) {
      json['correlation_matrix'].forEach((key, value) {
        matrix[key] = Map<String, double>.from(value);
      });
    }
    
    return MarketCorrelation(
      correlationMatrix: matrix,
      timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'correlation_matrix': correlationMatrix,
      'timestamp': timestamp.toIso8601String(),
    };
  }
  
  /// Get correlation value between two instruments
  double getCorrelation(String instrument1, String instrument2) {
    if (correlationMatrix.containsKey(instrument1) && 
        correlationMatrix[instrument1]!.containsKey(instrument2)) {
      return correlationMatrix[instrument1]![instrument2]!;
    }
    return 0.0;
  }
  
  @override
  List<Object?> get props => [correlationMatrix, timestamp];
}
