import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:logger/logger.dart';
import 'package:connectivity_plus/connectivity_plus.dart';

class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  
  final Logger _logger = Logger();
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  
  static const String _wsUrlKey = 'ws_base_url';
  static const String _tokenKey = 'api_token';
  static const String _defaultWsUrl = 'ws://localhost:8000/ws'; // Default WebSocket URL
  
  WebSocketChannel? _channel;
  StreamController<Map<String, dynamic>> _messageController = StreamController<Map<String, dynamic>>.broadcast();
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  bool _intentionallyClosed = false;
  
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;
  bool get isConnected => _channel != null;
  
  WebSocketService._internal() {
    // Listen for connectivity changes to reconnect when network is available
    Connectivity().onConnectivityChanged.listen((ConnectivityResult result) {
      if (result != ConnectivityResult.none && !_intentionallyClosed && _channel == null) {
        reconnect();
      }
    });
  }
  
  Future<String> getWsUrl() async {
    final storedUrl = await _secureStorage.read(key: _wsUrlKey);
    return storedUrl ?? _defaultWsUrl;
  }
  
  Future<void> setWsUrl(String url) async {
    await _secureStorage.write(key: _wsUrlKey, value: url);
    // Reconnect with new URL if we were connected
    if (_channel != null) {
      disconnect();
      connect();
    }
  }
  
  Future<void> connect() async {
    if (_channel != null) {
      _logger.info('WebSocket already connected');
      return;
    }
    
    _intentionallyClosed = false;
    final wsUrl = await getWsUrl();
    final token = await _secureStorage.read(key: _tokenKey);
    
    try {
      final uri = Uri.parse('$wsUrl${token != null ? "?token=$token" : ""}');
      _channel = WebSocketChannel.connect(uri);
      
      _channel!.stream.listen(
        (dynamic message) {
          _handleMessage(message);
        },
        onError: (error) {
          _logger.error('WebSocket error: $error');
          _cleanupConnection();
          _scheduleReconnect();
        },
        onDone: () {
          _logger.info('WebSocket connection closed');
          _cleanupConnection();
          if (!_intentionallyClosed) {
            _scheduleReconnect();
          }
        },
      );
      
      // Start heartbeat to keep connection alive
      _startHeartbeat();
      
      _logger.info('WebSocket connected to $wsUrl');
    } catch (e) {
      _logger.error('Failed to connect to WebSocket: $e');
      _cleanupConnection();
      _scheduleReconnect();
    }
  }
  
  void disconnect() {
    _intentionallyClosed = true;
    _cleanupConnection();
    _logger.info('WebSocket disconnected');
  }
  
  void reconnect() {
    _cleanupConnection();
    connect();
  }
  
  void _handleMessage(dynamic message) {
    try {
      if (message is String) {
        final data = jsonDecode(message);
        if (data is Map<String, dynamic>) {
          // Handle heartbeat response separately
          if (data['type'] == 'heartbeat') {
            return;
          }
          _messageController.add(data);
        }
      }
    } catch (e) {
      _logger.error('Error parsing WebSocket message: $e');
    }
  }
  
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      sendMessage({'type': 'heartbeat'});
    });
  }
  
  void _scheduleReconnect() {
    if (_intentionallyClosed) return;
    
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 5), () {
      connect();
    });
  }
  
  void _cleanupConnection() {
    _channel?.sink.close();
    _channel = null;
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }
  
  void sendMessage(Map<String, dynamic> message) {
    if (_channel != null) {
      try {
        _channel!.sink.add(jsonEncode(message));
      } catch (e) {
        _logger.error('Error sending WebSocket message: $e');
      }
    } else {
      _logger.warning('Cannot send message, WebSocket not connected');
      // Auto reconnect if trying to send message while disconnected
      reconnect();
    }
  }
  
  void dispose() {
    _intentionallyClosed = true;
    _cleanupConnection();
    _reconnectTimer?.cancel();
    _messageController.close();
  }
}
