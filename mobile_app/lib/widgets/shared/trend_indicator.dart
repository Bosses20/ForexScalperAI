import 'package:flutter/material.dart';
import '../../models/market_model.dart';

class TrendIndicator extends StatelessWidget {
  final MarketTrend trend;
  final double size;

  const TrendIndicator({
    Key? key,
    required this.trend,
    this.size = 24.0,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final IconData icon;
    final Color color;
    
    switch (trend) {
      case MarketTrend.bullish:
        icon = Icons.trending_up;
        color = const Color(0xFF00C853); // Green
        break;
      case MarketTrend.bearish:
        icon = Icons.trending_down;
        color = const Color(0xFFFF3D00); // Red
        break;
      case MarketTrend.ranging:
        icon = Icons.trending_flat;
        color = const Color(0xFF1565C0); // Blue
        break;
      case MarketTrend.choppy:
        icon = Icons.shuffle;
        color = const Color(0xFFFFD600); // Yellow
        break;
      case MarketTrend.unknown:
      default:
        icon = Icons.help_outline;
        color = const Color(0xFF90A4AE); // Gray
        break;
    }
    
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        shape: BoxShape.circle,
      ),
      child: Icon(
        icon,
        color: color,
        size: size * 0.6,
      ),
    );
  }
}
