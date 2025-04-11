import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class MarketConditionsWidget extends StatelessWidget {
  final MarketCondition marketCondition;
  final double confidenceScore;

  const MarketConditionsWidget({
    Key? key,
    required this.marketCondition,
    required this.confidenceScore,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Market Conditions',
                  style: theme.textTheme.titleMedium,
                ),
                _buildConfidenceIndicator(context),
              ],
            ),
            const SizedBox(height: 16),
            _buildMarketConditionInfo(context),
            const SizedBox(height: 16),
            _buildMarketConditionChart(context),
          ],
        ),
      ),
    );
  }

  Widget _buildConfidenceIndicator(BuildContext context) {
    final theme = Theme.of(context);
    final color = _getConfidenceColor(confidenceScore);
    
    return Row(
      children: [
        Text(
          'Confidence: ',
          style: theme.textTheme.bodySmall,
        ),
        Text(
          '${(confidenceScore * 100).toInt()}%',
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        const SizedBox(width: 8),
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
      ],
    );
  }

  Widget _buildMarketConditionInfo(BuildContext context) {
    final theme = Theme.of(context);
    
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Trend icon
        _buildInfoItem(
          context,
          icon: _getTrendIcon(marketCondition.trend),
          title: 'Trend',
          value: _getTrendLabel(marketCondition.trend),
          color: _getTrendColor(marketCondition.trend),
        ),
        
        // Volatility icon
        _buildInfoItem(
          context,
          icon: _getVolatilityIcon(marketCondition.volatility),
          title: 'Volatility',
          value: _getVolatilityLabel(marketCondition.volatility),
          color: _getVolatilityColor(marketCondition.volatility),
        ),
        
        // Liquidity icon
        _buildInfoItem(
          context,
          icon: Icons.waves,
          title: 'Liquidity',
          value: '${marketCondition.liquidity.toStringAsFixed(1)}',
          color: _getLiquidityColor(marketCondition.liquidity),
        ),
      ],
    );
  }

  Widget _buildInfoItem(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String value,
    required Color color,
  }) {
    final theme = Theme.of(context);
    
    return Expanded(
      child: Column(
        children: [
          Icon(
            icon,
            color: color,
            size: 32,
          ),
          const SizedBox(height: 8),
          Text(
            title,
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.onSurface,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMarketConditionChart(BuildContext context) {
    final theme = Theme.of(context);
    
    // These should be replaced with actual historical data
    final List<double> historicalConfidence = marketCondition.historicalConfidence;
    
    if (historicalConfidence.isEmpty) {
      return const SizedBox(height: 100, child: Center(child: Text('No historical data')));
    }
    
    return SizedBox(
      height: 120,
      child: LineChart(
        LineChartData(
          gridData: FlGridData(show: false),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  const intervals = ['1h', '2h', '3h', '4h', 'Now'];
                  if (value.toInt() % ((historicalConfidence.length - 1) ~/ 4) == 0) {
                    final index = value.toInt() ~/ ((historicalConfidence.length - 1) ~/ 4);
                    if (index < intervals.length) {
                      return Text(
                        intervals[index],
                        style: theme.textTheme.bodySmall,
                      );
                    }
                  }
                  return const SizedBox();
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: List.generate(
                historicalConfidence.length,
                (i) => FlSpot(i.toDouble(), historicalConfidence[i]),
              ),
              isCurved: true,
              color: theme.colorScheme.primary,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: theme.colorScheme.primary.withOpacity(0.2),
              ),
            ),
          ],
          minY: 0,
          maxY: 1,
        ),
      ),
    );
  }

  IconData _getTrendIcon(MarketTrend trend) {
    switch (trend) {
      case MarketTrend.bullish:
        return Icons.trending_up;
      case MarketTrend.bearish:
        return Icons.trending_down;
      case MarketTrend.ranging:
        return Icons.trending_flat;
      case MarketTrend.choppy:
        return Icons.shuffle;
    }
  }

  String _getTrendLabel(MarketTrend trend) {
    switch (trend) {
      case MarketTrend.bullish:
        return 'Bullish';
      case MarketTrend.bearish:
        return 'Bearish';
      case MarketTrend.ranging:
        return 'Ranging';
      case MarketTrend.choppy:
        return 'Choppy';
    }
  }

  Color _getTrendColor(MarketTrend trend) {
    switch (trend) {
      case MarketTrend.bullish:
        return Colors.green;
      case MarketTrend.bearish:
        return Colors.red;
      case MarketTrend.ranging:
        return Colors.blue;
      case MarketTrend.choppy:
        return Colors.orange;
    }
  }

  IconData _getVolatilityIcon(MarketVolatility volatility) {
    switch (volatility) {
      case MarketVolatility.low:
        return Icons.speed_outlined;
      case MarketVolatility.medium:
        return Icons.speed;
      case MarketVolatility.high:
        return Icons.shutter_speed;
    }
  }

  String _getVolatilityLabel(MarketVolatility volatility) {
    switch (volatility) {
      case MarketVolatility.low:
        return 'Low';
      case MarketVolatility.medium:
        return 'Medium';
      case MarketVolatility.high:
        return 'High';
    }
  }

  Color _getVolatilityColor(MarketVolatility volatility) {
    switch (volatility) {
      case MarketVolatility.low:
        return Colors.green;
      case MarketVolatility.medium:
        return Colors.orange;
      case MarketVolatility.high:
        return Colors.red;
    }
  }

  Color _getLiquidityColor(double liquidity) {
    if (liquidity >= 8.0) return Colors.green;
    if (liquidity >= 5.0) return Colors.orange;
    return Colors.red;
  }

  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) return Colors.green;
    if (confidence >= 0.5) return Colors.orange;
    return Colors.red;
  }
}

/// Enum representing the market trend
enum MarketTrend {
  bullish,
  bearish,
  ranging,
  choppy,
}

/// Enum representing the market volatility
enum MarketVolatility {
  low,
  medium,
  high,
}

/// Model representing current market conditions
class MarketCondition {
  final MarketTrend trend;
  final MarketVolatility volatility;
  final double liquidity; // 0-10 scale
  final String recommendedStrategy;
  final bool isFavorableForTrading;
  final List<double> historicalConfidence;

  const MarketCondition({
    required this.trend,
    required this.volatility,
    required this.liquidity,
    required this.recommendedStrategy,
    required this.isFavorableForTrading,
    required this.historicalConfidence,
  });

  /// Creates a default instance with moderate settings
  factory MarketCondition.moderate() {
    return MarketCondition(
      trend: MarketTrend.ranging,
      volatility: MarketVolatility.medium,
      liquidity: 7.0,
      recommendedStrategy: 'Balanced',
      isFavorableForTrading: true,
      historicalConfidence: [0.65, 0.68, 0.72, 0.70, 0.75],
    );
  }

  /// Creates an instance from a JSON object
  factory MarketCondition.fromJson(Map<String, dynamic> json) {
    return MarketCondition(
      trend: _trendFromString(json['trend'] ?? 'ranging'),
      volatility: _volatilityFromString(json['volatility'] ?? 'medium'),
      liquidity: json['liquidity']?.toDouble() ?? 7.0,
      recommendedStrategy: json['recommended_strategy'] ?? 'Balanced',
      isFavorableForTrading: json['is_favorable_for_trading'] ?? true,
      historicalConfidence: json['historical_confidence'] != null
          ? List<double>.from(json['historical_confidence'])
          : [0.65, 0.68, 0.72, 0.70, 0.75],
    );
  }

  static MarketTrend _trendFromString(String trend) {
    switch (trend.toLowerCase()) {
      case 'bullish':
        return MarketTrend.bullish;
      case 'bearish':
        return MarketTrend.bearish;
      case 'ranging':
        return MarketTrend.ranging;
      case 'choppy':
        return MarketTrend.choppy;
      default:
        return MarketTrend.ranging;
    }
  }

  static MarketVolatility _volatilityFromString(String volatility) {
    switch (volatility.toLowerCase()) {
      case 'low':
        return MarketVolatility.low;
      case 'medium':
        return MarketVolatility.medium;
      case 'high':
        return MarketVolatility.high;
      default:
        return MarketVolatility.medium;
    }
  }
}
