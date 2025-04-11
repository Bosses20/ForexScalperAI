import 'package:flutter/material.dart';
import '../models/market/market_condition.dart';

class MarketConditionView extends StatelessWidget {
  final MarketCondition marketCondition;
  final bool showDetailedView;

  const MarketConditionView({
    Key? key,
    required this.marketCondition,
    this.showDetailedView = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(context),
            const SizedBox(height: 16),
            _buildMarketSummary(context),
            if (showDetailedView) ...[
              const Divider(height: 32),
              _buildDetailedAnalysis(context),
            ],
            const SizedBox(height: 16),
            _buildRecommendations(context),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    final bool isFavorable = marketCondition.isTradingFavorable();
    
    return Row(
      children: [
        Icon(
          isFavorable ? Icons.check_circle : Icons.info,
          color: isFavorable ? Colors.green : Colors.orange,
          size: 24,
        ),
        const SizedBox(width: 8),
        Text(
          'Market Analysis',
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const Spacer(),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: _getConfidenceColor().withOpacity(0.2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            '${marketCondition.confidenceScore.toStringAsFixed(0)}% Confidence',
            style: TextStyle(
              color: _getConfidenceColor(),
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildMarketSummary(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: [
        _buildConditionIndicator(
          'Trend',
          _getTrendName(),
          _getTrendIcon(),
          _getTrendColor(),
        ),
        _buildConditionIndicator(
          'Volatility',
          _getVolatilityName(),
          _getVolatilityIcon(),
          _getVolatilityColor(),
        ),
        _buildConditionIndicator(
          'Liquidity',
          _getLiquidityName(),
          _getLiquidityIcon(),
          _getLiquidityColor(),
        ),
      ],
    );
  }

  Widget _buildConditionIndicator(
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Column(
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: Colors.grey,
          ),
        ),
      ],
    );
  }

  Widget _buildDetailedAnalysis(BuildContext context) {
    final additionalMetrics = marketCondition.additionalMetrics;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Detailed Analysis',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        if (additionalMetrics.containsKey('atr'))
          _buildMetricItem('ATR', additionalMetrics['atr']),
        if (additionalMetrics.containsKey('trend_strength'))
          _buildMetricItem('Trend Strength', 
              '${(additionalMetrics['trend_strength'] * 100).toStringAsFixed(0)}%'),
        if (additionalMetrics.containsKey('pivot_points'))
          _buildMetricItem('Key Level Proximity', 
              additionalMetrics['pivot_points']),
        if (additionalMetrics.containsKey('volume_trend'))
          _buildMetricItem('Volume Analysis', 
              additionalMetrics['volume_trend']),
      ],
    );
  }

  Widget _buildMetricItem(String label, dynamic value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          Text(
            value.toString(),
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  Widget _buildRecommendations(BuildContext context) {
    List<String> strategies = [];
    if (marketCondition.additionalMetrics.containsKey('recommended_strategies')) {
      strategies = List<String>.from(
          marketCondition.additionalMetrics['recommended_strategies']);
    }

    if (strategies.isEmpty) {
      strategies = _getGenericStrategies();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Recommended Strategies',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        ...strategies.map((strategy) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            children: [
              const Icon(Icons.check_circle_outline, size: 16, color: Colors.green),
              const SizedBox(width: 8),
              Expanded(child: Text(strategy)),
            ],
          ),
        )).toList(),
      ],
    );
  }

  Color _getConfidenceColor() {
    final score = marketCondition.confidenceScore;
    if (score >= 70) return Colors.green;
    if (score >= 50) return Colors.orange;
    return Colors.red;
  }

  String _getTrendName() {
    switch (marketCondition.trend) {
      case TrendType.bullish: return 'Bullish';
      case TrendType.bearish: return 'Bearish';
      case TrendType.ranging: return 'Ranging';
      case TrendType.choppy: return 'Choppy';
      case TrendType.unknown: return 'Unknown';
    }
  }

  IconData _getTrendIcon() {
    switch (marketCondition.trend) {
      case TrendType.bullish: return Icons.trending_up;
      case TrendType.bearish: return Icons.trending_down;
      case TrendType.ranging: return Icons.trending_flat;
      case TrendType.choppy: return Icons.shuffle;
      case TrendType.unknown: return Icons.help_outline;
    }
  }

  Color _getTrendColor() {
    switch (marketCondition.trend) {
      case TrendType.bullish: return Colors.green;
      case TrendType.bearish: return Colors.red;
      case TrendType.ranging: return Colors.blue;
      case TrendType.choppy: return Colors.orange;
      case TrendType.unknown: return Colors.grey;
    }
  }

  String _getVolatilityName() {
    switch (marketCondition.volatility) {
      case VolatilityLevel.low: return 'Low';
      case VolatilityLevel.medium: return 'Medium';
      case VolatilityLevel.high: return 'High';
      case VolatilityLevel.unknown: return 'Unknown';
    }
  }

  IconData _getVolatilityIcon() {
    switch (marketCondition.volatility) {
      case VolatilityLevel.low: return Icons.waves;
      case VolatilityLevel.medium: return Icons.waves;
      case VolatilityLevel.high: return Icons.waves;
      case VolatilityLevel.unknown: return Icons.help_outline;
    }
  }

  Color _getVolatilityColor() {
    switch (marketCondition.volatility) {
      case VolatilityLevel.low: return Colors.blue;
      case VolatilityLevel.medium: return Colors.orange;
      case VolatilityLevel.high: return Colors.red;
      case VolatilityLevel.unknown: return Colors.grey;
    }
  }

  String _getLiquidityName() {
    switch (marketCondition.liquidity) {
      case LiquidityLevel.low: return 'Low';
      case LiquidityLevel.medium: return 'Medium';
      case LiquidityLevel.high: return 'High';
      case LiquidityLevel.unknown: return 'Unknown';
    }
  }

  IconData _getLiquidityIcon() {
    switch (marketCondition.liquidity) {
      case LiquidityLevel.low: return Icons.water_drop_outlined;
      case LiquidityLevel.medium: return Icons.water_drop;
      case LiquidityLevel.high: return Icons.water;
      case LiquidityLevel.unknown: return Icons.help_outline;
    }
  }

  Color _getLiquidityColor() {
    switch (marketCondition.liquidity) {
      case LiquidityLevel.low: return Colors.red;
      case LiquidityLevel.medium: return Colors.orange;
      case LiquidityLevel.high: return Colors.blue;
      case LiquidityLevel.unknown: return Colors.grey;
    }
  }

  List<String> _getGenericStrategies() {
    switch (marketCondition.trend) {
      case TrendType.bullish:
        return [
          'EMA Crossover with trend',
          'Breakouts with volume confirmation',
          'Support/Resistance bounces',
        ];
      case TrendType.bearish:
        return [
          'Trend continuation setups',
          'Resistance breakdowns',
          'Break and retest patterns',
        ];
      case TrendType.ranging:
        return [
          'Range boundary trades',
          'Fading extreme moves',
          'Bollinger Band mean reversion',
        ];
      case TrendType.choppy:
        return [
          'Reduce position size',
          'Wait for clearer conditions',
          'Focus on longer timeframes',
        ];
      case TrendType.unknown:
        return [
          'Wait for clearer market conditions',
          'Analyze higher timeframes',
          'Monitor key levels for breakouts',
        ];
    }
  }
}
