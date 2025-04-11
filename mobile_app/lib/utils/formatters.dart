/// Utility functions for formatting various data types

/// Formats a DateTime to a human-readable "time ago" string
/// e.g. "just now", "5 minutes ago", "2 hours ago", "3 days ago"
String formatTimeAgo(DateTime dateTime) {
  final now = DateTime.now();
  final difference = now.difference(dateTime);
  
  if (difference.inSeconds < 60) {
    return 'just now';
  } else if (difference.inMinutes < 60) {
    final minutes = difference.inMinutes;
    return '$minutes ${minutes == 1 ? 'minute' : 'minutes'} ago';
  } else if (difference.inHours < 24) {
    final hours = difference.inHours;
    return '$hours ${hours == 1 ? 'hour' : 'hours'} ago';
  } else if (difference.inDays < 30) {
    final days = difference.inDays;
    return '$days ${days == 1 ? 'day' : 'days'} ago';
  } else if (difference.inDays < 365) {
    final months = (difference.inDays / 30).round();
    return '$months ${months == 1 ? 'month' : 'months'} ago';
  } else {
    final years = (difference.inDays / 365).round();
    return '$years ${years == 1 ? 'year' : 'years'} ago';
  }
}

/// Formats a double as a percentage with specified decimal places
String formatPercentage(double value, {int decimalPlaces = 2}) {
  return '${(value * 100).toStringAsFixed(decimalPlaces)}%';
}

/// Formats a currency value with appropriate symbol and decimal places
String formatCurrency(double value, {String symbol = '\$', int decimalPlaces = 2}) {
  return '$symbol${value.toStringAsFixed(decimalPlaces)}';
}

/// Formats a number with thousands separators
String formatNumber(num value, {int decimalPlaces = 0}) {
  // Get the string representation with the specified decimal places
  final String valueStr = value.toStringAsFixed(decimalPlaces);
  
  // Split the number into integer and decimal parts
  final parts = valueStr.split('.');
  final integerPart = parts[0];
  final decimalPart = parts.length > 1 ? parts[1] : '';
  
  // Add thousands separators to the integer part
  final formattedIntegerPart = integerPart.replaceAllMapped(
    RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'),
    (Match match) => '${match[1]},',
  );
  
  // Combine the parts back together
  if (decimalPart.isNotEmpty) {
    return '$formattedIntegerPart.$decimalPart';
  } else {
    return formattedIntegerPart;
  }
}

/// Formats a file size from bytes to human-readable format
/// e.g. "1.5 KB", "3.2 MB", "2.1 GB"
String formatFileSize(int bytes) {
  if (bytes < 1024) {
    return '$bytes B';
  } else if (bytes < 1024 * 1024) {
    final kb = bytes / 1024;
    return '${kb.toStringAsFixed(1)} KB';
  } else if (bytes < 1024 * 1024 * 1024) {
    final mb = bytes / (1024 * 1024);
    return '${mb.toStringAsFixed(1)} MB';
  } else {
    final gb = bytes / (1024 * 1024 * 1024);
    return '${gb.toStringAsFixed(1)} GB';
  }
}
