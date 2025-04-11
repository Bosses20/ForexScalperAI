import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logging/logging.dart';
import '../models/bot_server.dart';
import '../utils/logger.dart';

enum ConnectionStatus {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error
}

class WebSocketService {
  WebSocketChannel? _channel;
  final _secureStorage = const FlutterSecureStorage();
  final Logger _logger = Logger('WebSocketService');
  String? _wsUrl;
  String? _token;
  Timer? _pingTimer;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  final int _maxReconnectAttempts = 5;
  final Duration _reconnectDelay = const Duration(seconds: 3);
  final Duration _pingInterval = const Duration(seconds: 30);
  
  // Active server
  BotServer? _activeServer;

  // Stream controllers for different message types
  final _connectionStatusController = StreamController<ConnectionStatus>.broadcast();
  final _botStatusController = StreamController<Map<String, dynamic>>.broadcast();
  final _tradeUpdateController = StreamController<Map<String, dynamic>>.broadcast();
  final _marketUpdateController = StreamController<Map<String, dynamic>>.broadcast();
  final _errorMessageController = StreamController<String>.broadcast();
  final _rawMessageController = StreamController<Map<String, dynamic>>.broadcast();

  // Streams that components can listen to
  Stream<ConnectionStatus> get connectionStatus => _connectionStatusController.stream;
  Stream<Map<String, dynamic>> get botStatus => _botStatusController.stream;
  Stream<Map<String, dynamic>> get tradeUpdates => _tradeUpdateController.stream;
  Stream<Map<String, dynamic>> get marketUpdates => _marketUpdateController.stream;
  Stream<String> get errorMessages => _errorMessageController.stream;
  Stream<Map<String, dynamic>> get rawMessages => _rawMessageController.stream;

  // Singleton pattern
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal() {
    _loadSavedToken();
  }

  Future<void> _loadSavedToken() async {
    try {
      _token = await _secureStorage.read(key: 'auth_token');
      _logger.fine('Loaded saved token: ${_token != null ? 'Available' : 'Not found'}');
    } catch (e) {
      _logger.severe('Failed to load saved token: $e');
    }
  }

  /// Connects to the WebSocket server using a BotServer instance
  Future<bool> connect(BotServer server) async {
    _activeServer = server;
    return await connectToUrl(server.getWsUrl());
  }

  /// Connects to the WebSocket server using a URL string
  Future<bool> connectToUrl(String url) async {
    if (_channel != null) {
      await disconnect();
    }

    try {
      // Store the WebSocket URL
      _wsUrl = url;
      _logger.info('Connecting to WebSocket: $_wsUrl');
      _connectionStatusController.add(ConnectionStatus.connecting);

      // Connect to WebSocket with JWT token if available
      Uri uri;
      if (_token != null && _token!.isNotEmpty) {
        uri = Uri.parse('$_wsUrl?token=$_token');
      } else {
        uri = Uri.parse(_wsUrl!);
      }
      
      _channel = WebSocketChannel.connect(uri);

      // Set up listeners
      _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _onDone,
        cancelOnError: false,
      );

      // Send initial authentication
      if (_token != null && _token!.isNotEmpty) {
        _sendMessage({
          'type': 'authenticate',
          'token': _token,
        });
      }

      // Start ping timer to keep connection alive
      _startPingTimer();
      
      _connectionStatusController.add(ConnectionStatus.connected);
      _logger.info('Connected to WebSocket server');
      _reconnectAttempts = 0;
      return true;
    } catch (e) {
      _logger.severe('WebSocket connection failed: $e');
      _connectionStatusController.add(ConnectionStatus.error);
      _errorMessageController.add('Failed to connect: $e');
      return false;
    }
  }
  
  /// Get the currently active server
  BotServer? getActiveServer() {
    return _activeServer;
  }

  /// Disconnects from the WebSocket server
  Future<void> disconnect() async {
    _cancelReconnect();
    _stopPingTimer();
    
    if (_channel != null) {
      _logger.info('Disconnecting from WebSocket server');
      await _channel!.sink.close(status.normalClosure, 'Disconnected by client');
      _channel = null;
    }
    
    _connectionStatusController.add(ConnectionStatus.disconnected);
  }

  /// Set authentication token for websocket connections
  void setToken(String token) {
    _token = token;
    // If already connected, reconnect with the new token
    if (_channel != null && _wsUrl != null) {
      connectToUrl(_wsUrl!);
    }
  }

  /// Clears the authentication token
  void clearToken() {
    _token = null;
  }

  /// Handles received WebSocket messages
  void _onMessage(dynamic message) {
    try {
      final Map<String, dynamic> data = jsonDecode(message);
      
      // Forward the raw message to listeners
      _rawMessageController.add(data);
      
      _logger.fine('Message received: ${data['type']}');
      
      // Process different message types
      switch (data['type']) {
        case 'bot_status':
          _botStatusController.add(data['data']);
          break;
        
        case 'trade_update':
          _tradeUpdateController.add(data['data']);
          break;
        
        case 'market_update':
          _marketUpdateController.add(data['data']);
          break;
        
        case 'error':
          _errorMessageController.add(data['message']);
          _logger.severe('WebSocket error message: ${data['message']}');
          break;
          
        case 'ping':
          _sendMessage({'type': 'pong'});
          break;
          
        case 'pong':
          // Ping response received, connection is alive
          break;
          
        case 'auth_result':
          if (data['success'] == true) {
            _logger.info('WebSocket authentication successful');
          } else {
            _logger.warning('WebSocket authentication failed: ${data['message']}');
            _errorMessageController.add('Authentication failed: ${data['message']}');
            _connectionStatusController.add(ConnectionStatus.error);
          }
          break;
          
        default:
          _logger.fine('Unhandled message type: ${data['type']}');
      }
    } catch (e) {
      _logger.severe('Error processing WebSocket message: $e');
    }
  }

  /// Handles WebSocket errors
  void _onError(dynamic error) {
    _logger.severe('WebSocket error: $error');
    _errorMessageController.add('WebSocket error: $error');
    _connectionStatusController.add(ConnectionStatus.error);
    _scheduleReconnect();
  }

  /// Handles WebSocket connection closure
  void _onDone() {
    _logger.warning('WebSocket connection closed');
    _connectionStatusController.add(ConnectionStatus.disconnected);
    _scheduleReconnect();
  }

  /// Sends a message to the WebSocket server
  void _sendMessage(Map<String, dynamic> message) {
    if (_channel != null && (_channel!.sink as dynamic).closeCode == null) {
      try {
        final String jsonMessage = jsonEncode(message);
        _channel!.sink.add(jsonMessage);
        _logger.fine('Sent message: ${message['type']}');
      } catch (e) {
        _logger.severe('Error sending message: $e');
      }
    } else {
      _logger.warning('Cannot send message - WebSocket is not connected');
    }
  }

  /// Sends a ping message to keep the connection alive
  void _startPingTimer() {
    _stopPingTimer();
    _pingTimer = Timer.periodic(_pingInterval, (timer) {
      _sendMessage({'type': 'ping'});
    });
  }

  /// Stops the ping timer
  void _stopPingTimer() {
    if (_pingTimer != null) {
      _pingTimer!.cancel();
      _pingTimer = null;
    }
  }

  /// Schedules a reconnection attempt with exponential backoff
  void _scheduleReconnect() {
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      _logger.warning('Max reconnect attempts reached');
      _connectionStatusController.add(ConnectionStatus.error);
      _errorMessageController.add('Failed to connect after multiple attempts');
      return;
    }

    _reconnectAttempts++;
    _connectionStatusController.add(ConnectionStatus.reconnecting);
    _logger.fine('Scheduling reconnection attempt $_reconnectAttempts in ${_reconnectDelay.inSeconds * _reconnectAttempts} seconds');

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(_reconnectDelay * _reconnectAttempts, () {
      _reconnectTimer = null;
      if (_wsUrl != null) {
        connectToUrl(_wsUrl!);
      }
    });
  }

  /// Cancels any pending reconnection attempts
  void _cancelReconnect() {
    if (_reconnectTimer != null) {
      _reconnectTimer!.cancel();
      _reconnectTimer = null;
    }
  }

  /// Disposes of the service and closes all streams
  void dispose() {
    disconnect();
    _connectionStatusController.close();
    _botStatusController.close();
    _tradeUpdateController.close();
    _marketUpdateController.close();
    _errorMessageController.close();
    _rawMessageController.close();
  }
}
