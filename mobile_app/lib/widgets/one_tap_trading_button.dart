import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/market/market_condition.dart';

class OneTapTradingButton extends StatefulWidget {
  final bool isConnected;
  final bool isTrading;
  final MarketCondition? marketCondition;
  final VoidCallback onTap;
  final VoidCallback? onStop;
  final bool isLoading;

  const OneTapTradingButton({
    Key? key,
    required this.isConnected,
    required this.isTrading,
    this.marketCondition,
    required this.onTap,
    this.onStop,
    this.isLoading = false,
  }) : super(key: key);

  @override
  State<OneTapTradingButton> createState() => _OneTapTradingButtonState();
}

class _OneTapTradingButtonState extends State<OneTapTradingButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
  }

  void _initializeAnimations() {
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    _scaleAnimation = Tween<double>(begin: 0.95, end: 1.0).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: const Interval(0.0, 0.5, curve: Curves.easeInOut),
      ),
    );

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.05).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: const Interval(0.5, 1.0, curve: Curves.easeInOut),
      ),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  bool get _isEnabled =>
      widget.isConnected &&
      !widget.isLoading &&
      (widget.marketCondition?.isFavorableForTrading ?? false);

  Color _getButtonColor() {
    if (!widget.isConnected) {
      return Colors.grey;
    }

    if (widget.isTrading) {
      return Colors.orange;
    }

    if (widget.marketCondition == null) {
      return Colors.blue;
    }

    if (widget.marketCondition!.isFavorableForTrading) {
      return Colors.green;
    } else {
      return Colors.red.shade300;
    }
  }

  String _getButtonText() {
    if (!widget.isConnected) {
      return 'NOT CONNECTED';
    }

    if (widget.isLoading) {
      return 'ANALYZING...';
    }

    if (widget.isTrading) {
      return 'STOP TRADING';
    }

    if (widget.marketCondition == null) {
      return 'START TRADING';
    }

    if (widget.marketCondition!.isFavorableForTrading) {
      return 'START TRADING';
    } else {
      return 'MARKET UNFAVORABLE';
    }
  }

  Future<void> _handleTap() async {
    // Add haptic feedback
    await HapticFeedback.mediumImpact();
    
    if (!_isEnabled && !widget.isTrading) {
      // Show warning or just return if button is disabled and not trading
      return;
    }
    
    if (widget.isTrading) {
      if (widget.onStop != null) {
        widget.onStop!();
      }
    } else {
      widget.onTap();
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animationController,
      builder: (context, child) {
        double scale = widget.isTrading
            ? _pulseAnimation.value
            : (widget.isLoading ? 1.0 : _scaleAnimation.value);

        return GestureDetector(
          onTap: _handleTap,
          child: Transform.scale(
            scale: scale,
            child: Container(
              width: double.infinity,
              height: 60,
              decoration: BoxDecoration(
                color: _getButtonColor(),
                borderRadius: BorderRadius.circular(30),
                boxShadow: [
                  BoxShadow(
                    color: _getButtonColor().withOpacity(0.5),
                    blurRadius: 10,
                    offset: const Offset(0, 5),
                  ),
                ],
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(30),
                  onTap: null, // Handled by GestureDetector
                  child: Center(
                    child: widget.isLoading
                        ? Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 3,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Text(
                                _getButtonText(),
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 18,
                                ),
                              ),
                            ],
                          )
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                widget.isTrading
                                    ? Icons.stop_circle
                                    : Icons.play_circle_fill,
                                color: Colors.white,
                                size: 24,
                              ),
                              const SizedBox(width: 12),
                              Text(
                                _getButtonText(),
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 18,
                                ),
                              ),
                            ],
                          ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class OneTapTradingFeedback extends StatelessWidget {
  final bool isTrading;
  final String feedbackMessage;

  const OneTapTradingFeedback({
    Key? key,
    required this.isTrading,
    required this.feedbackMessage,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
      height: feedbackMessage.isNotEmpty ? 40 : 0,
      width: double.infinity,
      color: isTrading ? Colors.green.withOpacity(0.2) : Colors.transparent,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Center(
        child: Text(
          feedbackMessage,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: isTrading ? Colors.green.shade800 : Colors.grey.shade700,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }
}
