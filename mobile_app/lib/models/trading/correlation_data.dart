import 'package:equatable/equatable.dart';

/// Model representing correlation data between trading instruments.
/// Based on the multi-asset trading system that manages correlation
/// thresholds, predefined correlation groups, and correlation constraints.
class CorrelationData extends Equatable {
  /// The raw correlation matrix as a nested map:
  /// Map<Symbol1, Map<Symbol2, Correlation>> where correlation is a double
  /// between -1.0 (perfect negative correlation) and 1.0 (perfect positive correlation).
  final Map<String, Map<String, double>> correlationMatrix;

  /// Predefined correlation groups from the configuration
  /// (e.g., "major_pairs", "commodity_currencies", "safe_havens").
  final Map<String, List<String>> correlationGroups;

  /// Correlation thresholds used by the system to validate positions.
  final CorrelationThresholds thresholds;

  /// Trading recommendations based on correlation analysis.
  final List<CorrelationRecommendation> recommendations;

  /// Timestamp when the correlation data was last updated.
  final DateTime timestamp;

  const CorrelationData({
    required this.correlationMatrix,
    required this.correlationGroups,
    required this.thresholds,
    required this.recommendations,
    required this.timestamp,
  });

  /// Creates a default empty instance.
  factory CorrelationData.empty() {
    return CorrelationData(
      correlationMatrix: const {},
      correlationGroups: const {},
      thresholds: CorrelationThresholds.defaultThresholds(),
      recommendations: const [],
      timestamp: DateTime.now(),
    );
  }

  /// Creates a CorrelationData from a JSON object.
  factory CorrelationData.fromJson(Map<String, dynamic> json) {
    // Parse correlation matrix
    final correlationMatrix = <String, Map<String, double>>{};
    if (json['correlation_matrix'] != null) {
      final matrix = json['correlation_matrix'] as Map<String, dynamic>;
      matrix.forEach((key, value) {
        correlationMatrix[key] = (value as Map<String, dynamic>).map(
          (k, v) => MapEntry(k, (v as num).toDouble()),
        );
      });
    }

    // Parse correlation groups
    final correlationGroups = <String, List<String>>{};
    if (json['correlation_groups'] != null) {
      final groups = json['correlation_groups'] as Map<String, dynamic>;
      groups.forEach((key, value) {
        correlationGroups[key] = List<String>.from(value);
      });
    }

    // Parse recommendations
    final recommendations = <CorrelationRecommendation>[];
    if (json['recommendations'] != null) {
      final recos = json['recommendations'] as List;
      for (final reco in recos) {
        recommendations.add(CorrelationRecommendation.fromJson(reco));
      }
    }

    return CorrelationData(
      correlationMatrix: correlationMatrix,
      correlationGroups: correlationGroups,
      thresholds: json['thresholds'] != null
          ? CorrelationThresholds.fromJson(json['thresholds'])
          : CorrelationThresholds.defaultThresholds(),
      recommendations: recommendations,
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'])
          : DateTime.now(),
    );
  }

  /// Converts this CorrelationData to a JSON object.
  Map<String, dynamic> toJson() {
    return {
      'correlation_matrix': correlationMatrix,
      'correlation_groups': correlationGroups,
      'thresholds': thresholds.toJson(),
      'recommendations': recommendations.map((r) => r.toJson()).toList(),
      'timestamp': timestamp.toIso8601String(),
    };
  }

  /// Gets correlation value between two symbols.
  double getCorrelation(String symbol1, String symbol2) {
    if (symbol1 == symbol2) return 1.0; // Perfect correlation with self

    if (correlationMatrix.containsKey(symbol1) &&
        correlationMatrix[symbol1]!.containsKey(symbol2)) {
      return correlationMatrix[symbol1]![symbol2]!;
    }

    if (correlationMatrix.containsKey(symbol2) &&
        correlationMatrix[symbol2]!.containsKey(symbol1)) {
      return correlationMatrix[symbol2]![symbol1]!;
    }

    return 0.0; // Default if no correlation data found
  }

  /// Finds instruments with low correlation to the given symbol.
  List<String> findLowCorrelationInstruments(String symbol, {int limit = 5}) {
    final results = <String, double>{};

    // Get all symbols from the correlation matrix
    final allSymbols = <String>{};
    correlationMatrix.forEach((key, value) {
      allSymbols.add(key);
      value.keys.forEach((innerKey) => allSymbols.add(innerKey));
    });

    // Calculate absolute correlation for each symbol
    for (final otherSymbol in allSymbols) {
      if (otherSymbol != symbol) {
        final correlation = getCorrelation(symbol, otherSymbol).abs();
        results[otherSymbol] = correlation;
      }
    }

    // Sort by correlation (low to high) and take the top 'limit' results
    final sortedSymbols = results.keys.toList()
      ..sort((a, b) => results[a]!.compareTo(results[b]!));

    return sortedSymbols.take(limit).toList();
  }

  /// Finds instruments with high correlation to the given symbol.
  List<String> findHighCorrelationInstruments(String symbol, {int limit = 5}) {
    final results = <String, double>{};

    // Get all symbols from the correlation matrix
    final allSymbols = <String>{};
    correlationMatrix.forEach((key, value) {
      allSymbols.add(key);
      value.keys.forEach((innerKey) => allSymbols.add(innerKey));
    });

    // Calculate correlation for each symbol
    for (final otherSymbol in allSymbols) {
      if (otherSymbol != symbol) {
        final correlation = getCorrelation(symbol, otherSymbol);
        results[otherSymbol] = correlation;
      }
    }

    // Sort by correlation (high to low) and take the top 'limit' results
    final sortedSymbols = results.keys.toList()
      ..sort((a, b) => results[b]!.compareTo(results[a]!));

    return sortedSymbols.take(limit).toList();
  }

  /// Checks if two instruments are eligible to be traded together
  /// based on correlation thresholds.
  bool canTradeTogetherSafely(String symbol1, String symbol2) {
    final correlation = getCorrelation(symbol1, symbol2).abs();
    return correlation <= thresholds.maxSafeCorrelation;
  }

  /// Creates a copy of this CorrelationData with the given fields replaced.
  CorrelationData copyWith({
    Map<String, Map<String, double>>? correlationMatrix,
    Map<String, List<String>>? correlationGroups,
    CorrelationThresholds? thresholds,
    List<CorrelationRecommendation>? recommendations,
    DateTime? timestamp,
  }) {
    return CorrelationData(
      correlationMatrix: correlationMatrix ?? this.correlationMatrix,
      correlationGroups: correlationGroups ?? this.correlationGroups,
      thresholds: thresholds ?? this.thresholds,
      recommendations: recommendations ?? this.recommendations,
      timestamp: timestamp ?? this.timestamp,
    );
  }

  @override
  List<Object?> get props => [
        correlationMatrix,
        correlationGroups,
        thresholds,
        recommendations,
        timestamp,
      ];
}

/// Model representing correlation thresholds used by the trading system.
class CorrelationThresholds extends Equatable {
  /// Maximum correlation value considered safe for trading instruments together.
  final double maxSafeCorrelation;

  /// Correlation above which instruments are considered highly correlated.
  final double highCorrelationThreshold;

  /// Correlation below which instruments are considered inversely correlated.
  final double inverseCorrelationThreshold;

  /// Maximum combined risk for correlated instruments.
  final double maxRiskForCorrelatedPairs;

  const CorrelationThresholds({
    required this.maxSafeCorrelation,
    required this.highCorrelationThreshold,
    required this.inverseCorrelationThreshold,
    required this.maxRiskForCorrelatedPairs,
  });

  /// Default thresholds based on typical trading practices.
  factory CorrelationThresholds.defaultThresholds() {
    return const CorrelationThresholds(
      maxSafeCorrelation: 0.5,
      highCorrelationThreshold: 0.7,
      inverseCorrelationThreshold: -0.7,
      maxRiskForCorrelatedPairs: 1.0,
    );
  }

  /// Creates a CorrelationThresholds from a JSON object.
  factory CorrelationThresholds.fromJson(Map<String, dynamic> json) {
    return CorrelationThresholds(
      maxSafeCorrelation: json['max_safe_correlation']?.toDouble() ?? 0.5,
      highCorrelationThreshold: json['high_correlation_threshold']?.toDouble() ?? 0.7,
      inverseCorrelationThreshold: json['inverse_correlation_threshold']?.toDouble() ?? -0.7,
      maxRiskForCorrelatedPairs: json['max_risk_for_correlated_pairs']?.toDouble() ?? 1.0,
    );
  }

  /// Converts this CorrelationThresholds to a JSON object.
  Map<String, dynamic> toJson() {
    return {
      'max_safe_correlation': maxSafeCorrelation,
      'high_correlation_threshold': highCorrelationThreshold,
      'inverse_correlation_threshold': inverseCorrelationThreshold,
      'max_risk_for_correlated_pairs': maxRiskForCorrelatedPairs,
    };
  }

  @override
  List<Object?> get props => [
        maxSafeCorrelation,
        highCorrelationThreshold,
        inverseCorrelationThreshold,
        maxRiskForCorrelatedPairs,
      ];
}

/// Model representing a trading recommendation based on correlation analysis.
class CorrelationRecommendation extends Equatable {
  /// List of symbols recommended to trade together.
  final List<String> symbols;

  /// Average correlation between these symbols.
  final double averageCorrelation;

  /// Reason for this recommendation.
  final String reason;

  /// Recommended position sizing adjustment factor.
  final double positionSizeFactor;

  const CorrelationRecommendation({
    required this.symbols,
    required this.averageCorrelation,
    required this.reason,
    required this.positionSizeFactor,
  });

  /// Creates a CorrelationRecommendation from a JSON object.
  factory CorrelationRecommendation.fromJson(Map<String, dynamic> json) {
    return CorrelationRecommendation(
      symbols: List<String>.from(json['symbols'] ?? []),
      averageCorrelation: json['average_correlation']?.toDouble() ?? 0.0,
      reason: json['reason'] ?? '',
      positionSizeFactor: json['position_size_factor']?.toDouble() ?? 1.0,
    );
  }

  /// Converts this CorrelationRecommendation to a JSON object.
  Map<String, dynamic> toJson() {
    return {
      'symbols': symbols,
      'average_correlation': averageCorrelation,
      'reason': reason,
      'position_size_factor': positionSizeFactor,
    };
  }

  @override
  List<Object?> get props => [
        symbols,
        averageCorrelation,
        reason,
        positionSizeFactor,
      ];
}
