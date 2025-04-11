import 'package:intl/intl.dart';

enum NotificationType {
  trade,
  alert,
  error,
  system,
}

class TradingNotification {
  final String id;
  final String title;
  final String message;
  final int timestamp;
  final NotificationType type;
  final Map<String, dynamic>? data;
  
  TradingNotification({
    required this.id,
    required this.title,
    required this.message,
    required this.timestamp,
    required this.type,
    this.data,
  });
  
  factory TradingNotification.fromJson(Map<String, dynamic> json) {
    return TradingNotification(
      id: json['id'] as String,
      title: json['title'] as String,
      message: json['message'] as String,
      timestamp: json['timestamp'] as int,
      type: _parseNotificationType(json['type'] as String),
      data: json['data'] != null ? Map<String, dynamic>.from(json['data']) : null,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'message': message,
      'timestamp': timestamp,
      'type': type.toString().split('.').last,
      'data': data,
    };
  }
  
  String get formattedTime {
    final dateTime = DateTime.fromMillisecondsSinceEpoch(timestamp);
    return DateFormat('MMM dd, yyyy - HH:mm').format(dateTime);
  }
  
  String get timeAgo {
    final now = DateTime.now();
    final difference = now.difference(
      DateTime.fromMillisecondsSinceEpoch(timestamp)
    );
    
    if (difference.inSeconds < 60) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return DateFormat('MMM dd').format(
        DateTime.fromMillisecondsSinceEpoch(timestamp)
      );
    }
  }
  
  bool get isRecent {
    final now = DateTime.now();
    final difference = now.difference(
      DateTime.fromMillisecondsSinceEpoch(timestamp)
    );
    
    return difference.inHours < 2; // Consider notifications from last 2 hours as recent
  }
  
  static NotificationType _parseNotificationType(String typeStr) {
    switch (typeStr.toLowerCase()) {
      case 'trade':
        return NotificationType.trade;
      case 'alert':
        return NotificationType.alert;
      case 'error':
        return NotificationType.error;
      case 'system':
        return NotificationType.system;
      default:
        return NotificationType.system;
    }
  }
}
