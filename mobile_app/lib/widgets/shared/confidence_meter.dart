import 'dart:math' as math;
import 'package:flutter/material.dart';

class ConfidenceMeter extends StatelessWidget {
  final double value; // 0.0 to 1.0
  final double size;
  final double strokeWidth;

  const ConfidenceMeter({
    Key? key,
    required this.value,
    this.size = 80.0,
    this.strokeWidth = 8.0,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final Color gaugeColor = _getGaugeColor(value);
    final String displayValue = '${(value * 100).round()}%';
    
    return SizedBox(
      width: size,
      height: size / 2,
      child: Stack(
        children: [
          // Background arc
          CustomPaint(
            size: Size(size, size / 2),
            painter: ConfidenceMeterPainter(
              value: 1.0, // Full arc for background
              color: Colors.grey.withOpacity(0.2),
              strokeWidth: strokeWidth,
            ),
          ),
          
          // Value arc
          CustomPaint(
            size: Size(size, size / 2),
            painter: ConfidenceMeterPainter(
              value: value,
              color: gaugeColor,
              strokeWidth: strokeWidth,
            ),
          ),
          
          // Value text
          Positioned.fill(
            child: Align(
              alignment: Alignment.center,
              child: Padding(
                padding: EdgeInsets.only(top: size * 0.1),
                child: Text(
                  displayValue,
                  style: TextStyle(
                    color: gaugeColor,
                    fontWeight: FontWeight.bold,
                    fontSize: size * 0.2,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _getGaugeColor(double value) {
    if (value >= 0.75) {
      return const Color(0xFF00C853); // Green for high confidence
    } else if (value >= 0.5) {
      return const Color(0xFF2196F3); // Blue for moderate confidence
    } else if (value >= 0.25) {
      return const Color(0xFFFFD600); // Yellow for low confidence
    } else {
      return const Color(0xFFFF3D00); // Red for very low confidence
    }
  }
}

class ConfidenceMeterPainter extends CustomPainter {
  final double value; // 0.0 to 1.0
  final Color color;
  final double strokeWidth;

  ConfidenceMeterPainter({
    required this.value,
    required this.color,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final Rect rect = Rect.fromLTWH(
      strokeWidth / 2,
      strokeWidth / 2,
      size.width - strokeWidth,
      (size.width - strokeWidth) * 2,
    );
    
    // Calculate the sweep angle based on the value (0.0-1.0)
    // A semicircle spans 180 degrees (π radians)
    final double sweepAngle = value * math.pi;
    
    final Paint paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    
    // Draw the arc from the bottom left, counterclockwise
    canvas.drawArc(
      rect,
      math.pi, // Start angle (180 degrees, bottom left)
      sweepAngle, // Sweep angle based on value
      false, // Don't include center
      paint,
    );
  }

  @override
  bool shouldRepaint(ConfidenceMeterPainter oldDelegate) =>
      oldDelegate.value != value ||
      oldDelegate.color != color ||
      oldDelegate.strokeWidth != strokeWidth;
}
