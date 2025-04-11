import 'dart:developer' as developer;

/// Simple logger utility for consistent application logging
class Logger {
  final String tag;
  
  /// Creates a new logger with the specified tag
  Logger(this.tag);
  
  /// Log informational message
  void i(String message) {
    developer.log(message, name: tag, level: 800);
  }
  
  /// Log debug message
  void d(String message) {
    developer.log(message, name: tag, level: 500);
  }
  
  /// Log warning message
  void w(String message) {
    developer.log(message, name: tag, level: 900);
  }
  
  /// Log error message
  void e(String message, [Object? error, StackTrace? stackTrace]) {
    developer.log(
      message,
      name: tag,
      level: 1000,
      error: error,
      stackTrace: stackTrace,
    );
  }
}
