import 'package:flutter/material.dart';
import 'dart:math' as math;

class MiniSparkline extends StatelessWidget {
  final List<double> data;
  final Color lineColor;
  final Color fillColor;
  final double strokeWidth;
  final bool showLastPoint;

  const MiniSparkline({
    Key? key,
    required this.data,
    this.lineColor = Colors.blue,
    this.fillColor = const Color(0x202196F3),
    this.strokeWidth = 1.5,
    this.showLastPoint = true,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: Size.infinite,
      painter: _SparklinePainter(
        data: data,
        lineColor: lineColor,
        fillColor: fillColor,
        strokeWidth: strokeWidth,
        showLastPoint: showLastPoint,
      ),
    );
  }
}

class _SparklinePainter extends CustomPainter {
  final List<double> data;
  final Color lineColor;
  final Color fillColor;
  final double strokeWidth;
  final bool showLastPoint;

  _SparklinePainter({
    required this.data,
    required this.lineColor,
    required this.fillColor,
    required this.strokeWidth,
    required this.showLastPoint,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (data.isEmpty) return;

    final Paint linePaint = Paint()
      ..color = lineColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final Paint fillPaint = Paint()
      ..color = fillColor
      ..style = PaintingStyle.fill;

    final Paint pointPaint = Paint()
      ..color = lineColor
      ..style = PaintingStyle.fill;

    // Find min and max for scaling
    double minValue = data.reduce(math.min);
    double maxValue = data.reduce(math.max);
    
    if (minValue == maxValue) {
      // If all values are the same, artificially create a range to avoid division by zero
      minValue -= 0.5;
      maxValue += 0.5;
    }

    // Calculate the step between points
    final double xStep = size.width / (data.length - 1);

    // Prepare path for the line
    final Path linePath = Path();
    
    // Prepare path for the fill (needs to be closed at the bottom)
    final Path fillPath = Path();
    fillPath.moveTo(0, size.height); // Start at bottom left
    
    for (int i = 0; i < data.length; i++) {
      final double x = i * xStep;
      // Normalize value to the range [0, 1] and then scale to the canvas height
      // Invert y since canvas coordinates increase downward but our graph increases upward
      final double normalizedValue = (data[i] - minValue) / (maxValue - minValue);
      final double y = size.height - (normalizedValue * size.height);
      
      if (i == 0) {
        linePath.moveTo(x, y);
        fillPath.lineTo(x, y);
      } else {
        linePath.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
      
      // Draw the last point
      if (showLastPoint && i == data.length - 1) {
        canvas.drawCircle(Offset(x, y), strokeWidth * 1.5, pointPaint);
      }
    }
    
    // Close the fill path
    fillPath.lineTo(size.width, size.height); // Bottom right
    fillPath.close(); // Back to bottom left

    // Draw the fill first (so it's under the line)
    canvas.drawPath(fillPath, fillPaint);
    
    // Draw the line
    canvas.drawPath(linePath, linePaint);
  }

  @override
  bool shouldRepaint(_SparklinePainter oldDelegate) => 
      data != oldDelegate.data ||
      lineColor != oldDelegate.lineColor ||
      fillColor != oldDelegate.fillColor ||
      strokeWidth != oldDelegate.strokeWidth ||
      showLastPoint != oldDelegate.showLastPoint;
}
