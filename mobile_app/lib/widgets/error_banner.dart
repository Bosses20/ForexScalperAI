import 'package:flutter/material.dart';

class ErrorBanner extends StatelessWidget {
  final String message;
  final VoidCallback? onDismiss;
  final VoidCallback? onRetry;

  const ErrorBanner({
    Key? key,
    required this.message,
    this.onDismiss,
    this.onRetry,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: Colors.red.shade100,
      child: Material(
        color: Colors.transparent,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
          child: Row(
            children: [
              const Icon(
                Icons.error_outline,
                color: Colors.red,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  message,
                  style: const TextStyle(
                    color: Colors.red,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              if (onRetry != null)
                TextButton(
                  onPressed: onRetry,
                  child: const Text('RETRY'),
                  style: TextButton.styleFrom(
                    foregroundColor: Colors.red,
                    backgroundColor: Colors.white.withOpacity(0.3),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
              if (onDismiss != null) ...[
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.red),
                  onPressed: onDismiss,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(
                    minWidth: 36,
                    minHeight: 36,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class ConnectionErrorBanner extends StatelessWidget {
  final String serverName;
  final VoidCallback onReconnect;
  final VoidCallback? onDismiss;

  const ConnectionErrorBanner({
    Key? key,
    required this.serverName,
    required this.onReconnect,
    this.onDismiss,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ErrorBanner(
      message: 'Connection lost to server: $serverName',
      onRetry: onReconnect,
      onDismiss: onDismiss,
    );
  }
}

class MarketDataErrorBanner extends StatelessWidget {
  final VoidCallback onRefresh;
  final VoidCallback? onDismiss;

  const MarketDataErrorBanner({
    Key? key,
    required this.onRefresh,
    this.onDismiss,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ErrorBanner(
      message: 'Failed to load market data. Check your connection.',
      onRetry: onRefresh,
      onDismiss: onDismiss,
    );
  }
}

class BotErrorBanner extends StatelessWidget {
  final String errorMessage;
  final VoidCallback? onDismiss;

  const BotErrorBanner({
    Key? key,
    required this.errorMessage,
    this.onDismiss,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ErrorBanner(
      message: 'Trading bot error: $errorMessage',
      onDismiss: onDismiss,
    );
  }
}
