import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:mobile_app/models/notification_model.dart';
import 'package:mobile_app/config/app_config.dart';
import 'package:mobile_app/services/api_service.dart';
import 'package:mobile_app/services/storage_service.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  final FlutterLocalNotificationsPlugin _flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();
  final StreamController<TradingNotification> _notificationStreamController = StreamController<TradingNotification>.broadcast();

  Stream<TradingNotification> get notificationStream => _notificationStreamController.stream;
  List<TradingNotification> _notificationHistory = [];
  
  bool isInitialized = false;
  Timer? _pollingTimer;
  int _lastNotificationTimestamp = DateTime.now().millisecondsSinceEpoch;
  final ApiService _apiService = ApiService();
  final StorageService _storageService = StorageService();

  factory NotificationService() {
    return _instance;
  }

  NotificationService._internal();

  List<TradingNotification> get notificationHistory => _notificationHistory;

  Future<void> initialize() async {
    if (isInitialized) return;

    // Initialize local notifications
    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    
    final DarwinInitializationSettings initializationSettingsIOS =
        DarwinInitializationSettings(
      requestSoundPermission: true,
      requestBadgePermission: true,
      requestAlertPermission: true,
      onDidReceiveLocalNotification: (int id, String? title, String? body, String? payload) async {
        // Handle iOS notification received
      },
    );
    
    final InitializationSettings initializationSettings = InitializationSettings(
      android: initializationSettingsAndroid,
      iOS: initializationSettingsIOS,
    );
    
    await _flutterLocalNotificationsPlugin.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: (NotificationResponse response) async {
        // Handle notification tap
        _handleNotificationTap(response.payload);
      },
    );

    // Load notification history from storage
    await _loadNotificationHistory();
    
    // Start polling for notifications if local server is available
    _startPollingForNotifications();
    
    isInitialized = true;
  }

  void _startPollingForNotifications() {
    // Poll the server every 15 seconds for new notifications
    _pollingTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      _pollForNotifications();
    });
  }

  Future<void> _pollForNotifications() async {
    try {
      // Check if we have an active local server
      final serverConfig = await _storageService.getServerConfig();
      if (serverConfig == null || serverConfig.baseUrl.isEmpty) {
        return;
      }

      // Get notifications from server
      final response = await _apiService.get(
        '/notifications',
        queryParams: {'since': _lastNotificationTimestamp.toString()},
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        
        if (data.isNotEmpty) {
          for (var notificationData in data) {
            final notification = TradingNotification.fromJson(notificationData);
            _showNotification(notification);
            _addToHistory(notification);
            _notificationStreamController.add(notification);
            
            // Update the last notification timestamp
            if (notification.timestamp > _lastNotificationTimestamp) {
              _lastNotificationTimestamp = notification.timestamp;
            }
          }
          
          // Save updated history
          _saveNotificationHistory();
        }
      }
    } catch (e) {
      debugPrint('Error polling for notifications: $e');
    }
  }

  Future<void> _showNotification(TradingNotification notification) async {
    AndroidNotificationDetails androidPlatformChannelSpecifics = AndroidNotificationDetails(
      'trading_alerts',
      'Trading Alerts',
      channelDescription: 'Notifications about trading activities and alerts',
      importance: Importance.max,
      priority: Priority.high,
      ticker: 'ticker',
      color: _getNotificationColor(notification.type),
    );
    
    NotificationDetails platformChannelSpecifics = NotificationDetails(
      android: androidPlatformChannelSpecifics,
      iOS: const DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
      ),
    );
    
    await _flutterLocalNotificationsPlugin.show(
      notification.id.hashCode,
      notification.title,
      notification.message,
      platformChannelSpecifics,
      payload: json.encode(notification.toJson()),
    );
  }

  Color _getNotificationColor(NotificationType type) {
    switch (type) {
      case NotificationType.trade:
        return Colors.blue;
      case NotificationType.alert:
        return Colors.orange;
      case NotificationType.error:
        return Colors.red;
      case NotificationType.system:
        return Colors.purple;
      default:
        return Colors.grey;
    }
  }

  void _handleNotificationTap(String? payload) {
    if (payload != null) {
      try {
        final notificationData = json.decode(payload);
        final notification = TradingNotification.fromJson(notificationData);
        _notificationStreamController.add(notification);
      } catch (e) {
        debugPrint('Error parsing notification payload: $e');
      }
    }
  }

  void _addToHistory(TradingNotification notification) {
    _notificationHistory.add(notification);
    
    // Keep only the latest 100 notifications
    if (_notificationHistory.length > 100) {
      _notificationHistory = _notificationHistory.sublist(
        _notificationHistory.length - 100,
      );
    }
  }

  Future<void> _loadNotificationHistory() async {
    try {
      final history = await _storageService.getNotificationHistory();
      if (history != null) {
        _notificationHistory = history;
        
        // Find the most recent notification timestamp
        if (_notificationHistory.isNotEmpty) {
          _lastNotificationTimestamp = _notificationHistory
              .map((n) => n.timestamp)
              .reduce((max, timestamp) => timestamp > max ? timestamp : max);
        }
      }
    } catch (e) {
      debugPrint('Error loading notification history: $e');
    }
  }

  Future<void> _saveNotificationHistory() async {
    try {
      await _storageService.saveNotificationHistory(_notificationHistory);
    } catch (e) {
      debugPrint('Error saving notification history: $e');
    }
  }

  Future<void> clearNotifications() async {
    await _flutterLocalNotificationsPlugin.cancelAll();
  }

  Future<void> clearHistory() async {
    _notificationHistory.clear();
    await _saveNotificationHistory();
  }

  Future<void> sendTestNotification() async {
    final testNotification = TradingNotification(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: 'Test Notification',
      message: 'This is a test notification from your trading bot',
      timestamp: DateTime.now().millisecondsSinceEpoch,
      type: NotificationType.system,
      data: {'test': true},
    );
    
    await _showNotification(testNotification);
    _addToHistory(testNotification);
    _notificationStreamController.add(testNotification);
    await _saveNotificationHistory();
  }

  void dispose() {
    _pollingTimer?.cancel();
    _notificationStreamController.close();
  }
}
