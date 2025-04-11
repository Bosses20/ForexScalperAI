import 'package:flutter/material.dart';
import '../../models/market_model.dart';
import '../shared/confidence_meter.dart';
import '../shared/trend_indicator.dart';
import '../shared/volatility_meter.dart';

class MarketConditionCard extends StatelessWidget {
  final MarketCondition marketCondition;
  final Function(bool) onToggleTradingEnabled;

  const MarketConditionCard({
    Key? key,
    required this.marketCondition,
    required this.onToggleTradingEnabled,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12.0),
      ),
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
                  style: theme.textTheme.titleLarge,
                ),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: () {
                    // Request market condition update
                    // This would typically be handled by the bloc
                  },
                ),
              ],
            ),
            const Divider(),
            const SizedBox(height: 8),
            
            // Market trend section
            _buildDetailRow(
              context,
              'Trend',
              _getTrendName(marketCondition.trend),
              leading: TrendIndicator(trend: marketCondition.trend),
              color: _getTrendColor(marketCondition.trend),
            ),
            
            const SizedBox(height: 16),
            
            // Volatility and liquidity section
            Row(
              children: [
                Expanded(
                  child: _buildDetailRow(
                    context,
                    'Volatility',
                    _getVolatilityName(marketCondition.volatility),
                    leading: VolatilityMeter(level: marketCondition.volatility),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildDetailRow(
                    context,
                    'Liquidity',
                    _getLiquidityName(marketCondition.liquidity),
                    color: _getLiquidityColor(marketCondition.liquidity),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Trading favorability section
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Trading Favorability',
                        style: theme.textTheme.bodySmall!.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${(marketCondition.tradingFavorability * 100).toStringAsFixed(0)}%',
                        style: theme.textTheme.headlineSmall!.copyWith(
                          color: _getFavorabilityColor(marketCondition.tradingFavorability),
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Confidence',
                        style: theme.textTheme.bodySmall!.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      const SizedBox(height: 4),
                      ConfidenceMeter(
                        value: marketCondition.confidenceScore,
                        size: 60,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Trading enabled toggle
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Trading Enabled',
                  style: theme.textTheme.titleMedium,
                ),
                Switch(
                  value: marketCondition.isFavorableForTrading,
                  onChanged: onToggleTradingEnabled,
                  activeColor: theme.colorScheme.primary,
                ),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // Recommended strategies
            if (marketCondition.recommendedStrategies.isNotEmpty) ...[
              Text(
                'Recommended Strategies',
                style: theme.textTheme.bodySmall!.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.6),
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: marketCondition.recommendedStrategies
                    .map((strategy) => Chip(
                          label: Text(strategy),
                          backgroundColor: theme.colorScheme.primaryContainer,
                          labelStyle: TextStyle(
                            color: theme.colorScheme.onPrimaryContainer,
                          ),
                        ))
                    .toList(),
              ),
            ],
            
            const SizedBox(height: 8),
            
            // Timestamp
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                'Updated: ${_formatTimestamp(marketCondition.timestamp)}',
                style: theme.textTheme.bodySmall!.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.4),
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(
    BuildContext context,
    String label,
    String value, {
    Widget? leading,
    Color? color,
  }) {
    final theme = Theme.of(context);
    
    return Row(
      children: [
        if (leading != null) ...[
          leading,
          const SizedBox(width: 8),
        ],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: theme.textTheme.bodySmall!.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.6),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                value,
                style: theme.textTheme.titleMedium!.copyWith(
                  color: color,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _getTrendName(MarketTrend trend) {
    switch (trend) {
      case MarketTrend.bullish:
        return 'Bullish';
      case MarketTrend.bearish:
        return 'Bearish';
      case MarketTrend.ranging:
        return 'Ranging';
      case MarketTrend.choppy:
        return 'Choppy';
      case MarketTrend.unknown:
        return 'Unknown';
    }
  }

  Color _getTrendColor(MarketTrend trend) {
    switch (trend) {
      case MarketTrend.bullish:
        return const Color(0xFF00C853); // Green
      case MarketTrend.bearish:
        return const Color(0xFFFF3D00); // Red
      case MarketTrend.ranging:
        return const Color(0xFF1565C0); // Blue
      case MarketTrend.choppy:
        return const Color(0xFFFFD600); // Yellow
      case MarketTrend.unknown:
        return const Color(0xFF90A4AE); // Gray
    }
  }

  String _getVolatilityName(VolatilityLevel level) {
    switch (level) {
      case VolatilityLevel.low:
        return 'Low';
      case VolatilityLevel.medium:
        return 'Medium';
      case VolatilityLevel.high:
        return 'High';
      case VolatilityLevel.unknown:
        return 'Unknown';
    }
  }

  String _getLiquidityName(LiquidityLevel level) {
    switch (level) {
      case LiquidityLevel.low:
        return 'Low';
      case LiquidityLevel.normal:
        return 'Normal';
      case LiquidityLevel.high:
        return 'High';
      case LiquidityLevel.unknown:
        return 'Unknown';
    }
  }

  Color _getLiquidityColor(LiquidityLevel level) {
    switch (level) {
      case LiquidityLevel.low:
        return const Color(0xFFFFB74D); // Orange
      case LiquidityLevel.normal:
        return const Color(0xFF4CAF50); // Green
      case LiquidityLevel.high:
        return const Color(0xFF2196F3); // Blue
      case LiquidityLevel.unknown:
        return const Color(0xFF90A4AE); // Gray
    }
  }

  Color _getFavorabilityColor(double favorability) {
    if (favorability > 0.7) {
      return const Color(0xFF00C853); // Green
    } else if (favorability > 0.4) {
      return const Color(0xFFFFD600); // Yellow
    } else {
      return const Color(0xFFFF3D00); // Red
    }
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);
    
    if (difference.inSeconds < 60) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else {
      return '${difference.inDays}d ago';
    }
  }
}

class MarketConditionCardSkeleton extends StatelessWidget {
  const MarketConditionCardSkeleton({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12.0),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildSkeletonBox(120, 24),
                const Icon(Icons.refresh, color: Colors.grey),
              ],
            ),
            const Divider(),
            const SizedBox(height: 8),
            
            // Market trend skeleton
            Row(
              children: [
                _buildSkeletonCircle(24),
                const SizedBox(width: 8),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSkeletonBox(80, 16),
                    const SizedBox(height: 4),
                    _buildSkeletonBox(100, 20),
                  ],
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Volatility and liquidity skeleton
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(80, 16),
                      const SizedBox(height: 4),
                      _buildSkeletonBox(70, 20),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(80, 16),
                      const SizedBox(height: 4),
                      _buildSkeletonBox(70, 20),
                    ],
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Trading favorability skeleton
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(120, 16),
                      const SizedBox(height: 4),
                      _buildSkeletonBox(60, 24),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(80, 16),
                      const SizedBox(height: 4),
                      _buildSkeletonCircle(60),
                    ],
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // Toggle skeleton
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildSkeletonBox(100, 20),
                Container(
                  width: 40,
                  height: 20,
                  decoration: BoxDecoration(
                    color: Colors.grey[300],
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // Strategies skeleton
            _buildSkeletonBox(150, 16),
            const SizedBox(height: 8),
            Row(
              children: [
                _buildSkeletonChip(),
                const SizedBox(width: 8),
                _buildSkeletonChip(),
              ],
            ),
            
            const SizedBox(height: 8),
            
            // Timestamp skeleton
            Align(
              alignment: Alignment.centerRight,
              child: _buildSkeletonBox(100, 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSkeletonBox(double width, double height) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: Colors.grey[300],
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }

  Widget _buildSkeletonCircle(double size) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: Colors.grey[300],
        shape: BoxShape.circle,
      ),
    );
  }

  Widget _buildSkeletonChip() {
    return Container(
      width: 80,
      height: 32,
      decoration: BoxDecoration(
        color: Colors.grey[300],
        borderRadius: BorderRadius.circular(16),
      ),
    );
  }
}
