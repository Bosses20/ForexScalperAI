import 'package:flutter/material.dart';
import '../../models/market_model.dart';

class VolatilityMeter extends StatelessWidget {
  final VolatilityLevel level;
  final double width;
  final double height;

  const VolatilityMeter({
    Key? key,
    required this.level,
    this.width = 60.0,
    this.height = 16.0,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final int filledBars = _getFilledBarsCount();
    final Color barColor = _getVolatilityColor();
    
    return SizedBox(
      width: width,
      height: height,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(3, (index) {
          final bool isFilled = index < filledBars;
          final double barHeight = height * _getHeightMultiplier(index);
          final double verticalPadding = (height - barHeight) / 2;
          
          return Expanded(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 1.5, vertical: verticalPadding),
              child: Container(
                height: barHeight,
                decoration: BoxDecoration(
                  color: isFilled ? barColor : Colors.grey.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(2.0),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }

  int _getFilledBarsCount() {
    switch (level) {
      case VolatilityLevel.low:
        return 1;
      case VolatilityLevel.medium:
        return 2;
      case VolatilityLevel.high:
        return 3;
      case VolatilityLevel.unknown:
        return 0;
    }
  }

  Color _getVolatilityColor() {
    switch (level) {
      case VolatilityLevel.low:
        return const Color(0xFF4CAF50); // Green
      case VolatilityLevel.medium:
        return const Color(0xFFFFC107); // Amber
      case VolatilityLevel.high:
        return const Color(0xFFF44336); // Red
      case VolatilityLevel.unknown:
        return Colors.grey;
    }
  }

  double _getHeightMultiplier(int barIndex) {
    // First bar is shortest, last bar is tallest
    switch (barIndex) {
      case 0:
        return 0.6;
      case 1:
        return 0.8;
      case 2:
        return 1.0;
      default:
        return 0.6;
    }
  }
}
