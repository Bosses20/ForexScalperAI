import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../models/bot_server.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import '../services/preferences_service.dart';

class ConnectionManager {
  final ApiService apiService;
  final WebSocketService webSocketService;
  final PreferencesService preferencesService;
  
  BotServer? _activeServer;
  Timer? _reconnectionTimer;
  StreamSubscription? _connectivitySubscription;
  final Duration _reconnectInterval = const Duration(seconds: 5);
  int _reconnectAttempts = 0;
  final int _maxReconnectAttempts = 5;
  
  bool _isReconnecting = false;
  final _connectionStatusController = StreamController<ConnectionStatus>.broadcast();
  
  Stream<ConnectionStatus> get connectionStatus => _connectionStatusController.stream;
  BotServer? get activeServer => _activeServer;
  bool get isConnected => _activeServer != null && webSocketService.isConnected;
  
  ConnectionManager({
    required this.apiService,
    required this.webSocketService,
    required this.preferencesService,
  }) {
    // Initialize connectivity monitoring
    _connectivitySubscription = Connectivity().onConnectivityChanged.listen(_handleConnectivityChange);
    
    // Check for last active server on initialization
    _loadLastActiveServer();
  }
  
  Future<void> _loadLastActiveServer() async {
    try {
      final lastServer = await preferencesService.getLastActiveServer();
      if (lastServer != null) {
        // Don't connect automatically here, this will be handled by the NetworkDiscoveryBloc
        _activeServer = lastServer;
        _connectionStatusController.add(
          ConnectionStatus(
            state: ConnectionState.disconnected,
            server: lastServer,
            message: 'Last server loaded from storage',
          ),
        );
      }
    } catch (e) {
      debugPrint('Error loading last active server: $e');
    }
  }
  
  Future<bool> connectToServer(BotServer server) async {
    try {
      // Stop any ongoing reconnection attempts
      _stopReconnectionTimer();
      
      // First try to connect via API to verify server is reachable
      final isReachable = await apiService.checkServerReachable(server);
      if (!isReachable) {
        _connectionStatusController.add(
          ConnectionStatus(
            state: ConnectionState.error,
            server: server,
            message: 'Server unreachable',
          ),
        );
        return false;
      }
      
      // Configure API service with the server
      apiService.setServer(server);
      
      // Then connect WebSocket
      final wsConnected = await webSocketService.connect(server);
      if (!wsConnected) {
        _connectionStatusController.add(
          ConnectionStatus(
            state: ConnectionState.error,
            server: server,
            message: 'WebSocket connection failed',
          ),
        );
        return false;
      }
      
      // Update active server and save to preferences
      _activeServer = server;
      await preferencesService.saveLastActiveServer(server);
      
      // Reset reconnect attempts
      _reconnectAttempts = 0;
      
      _connectionStatusController.add(
        ConnectionStatus(
          state: ConnectionState.connected,
          server: server,
          message: 'Connected successfully',
        ),
      );
      
      return true;
    } catch (e) {
      _connectionStatusController.add(
        ConnectionStatus(
          state: ConnectionState.error,
          server: server,
          message: 'Connection error: $e',
        ),
      );
      return false;
    }
  }
  
  Future<void> disconnectFromServer() async {
    try {
      _stopReconnectionTimer();
      
      if (_activeServer != null) {
        await webSocketService.disconnect();
        
        _connectionStatusController.add(
          ConnectionStatus(
            state: ConnectionState.disconnected,
            server: _activeServer,
            message: 'Disconnected',
          ),
        );
        
        // Keep the active server in memory for possible reconnection,
        // but mark it as disconnected
      }
    } catch (e) {
      debugPrint('Error disconnecting: $e');
    }
  }
  
  Future<void> reconnectToLastServer() async {
    if (_activeServer == null) {
      await _loadLastActiveServer();
    }
    
    if (_activeServer != null) {
      _startReconnectionProcess(_activeServer!);
    } else {
      _connectionStatusController.add(
        const ConnectionStatus(
          state: ConnectionState.disconnected,
          server: null,
          message: 'No last server to reconnect to',
        ),
      );
    }
  }
  
  void _handleConnectivityChange(ConnectivityResult result) {
    // If we get back online and we have an active server that was disconnected,
    // try to reconnect
    if (result != ConnectivityResult.none && 
        _activeServer != null && 
        !webSocketService.isConnected) {
      _startReconnectionProcess(_activeServer!);
    }
  }
  
  void _startReconnectionProcess(BotServer server) {
    if (_isReconnecting) return;
    
    _isReconnecting = true;
    _reconnectAttempts = 0;
    
    _connectionStatusController.add(
      ConnectionStatus(
        state: ConnectionState.reconnecting,
        server: server,
        message: 'Attempting to reconnect...',
      ),
    );
    
    _reconnectionTimer = Timer.periodic(_reconnectInterval, (timer) async {
      if (_reconnectAttempts >= _maxReconnectAttempts) {
        _stopReconnectionTimer();
        _connectionStatusController.add(
          ConnectionStatus(
            state: ConnectionState.error,
            server: server,
            message: 'Failed to reconnect after maximum attempts',
          ),
        );
        return;
      }
      
      _reconnectAttempts++;
      debugPrint('Reconnection attempt $_reconnectAttempts of $_maxReconnectAttempts');
      
      final success = await connectToServer(server);
      if (success) {
        _stopReconnectionTimer();
      }
    });
  }
  
  void _stopReconnectionTimer() {
    _reconnectionTimer?.cancel();
    _reconnectionTimer = null;
    _isReconnecting = false;
  }
  
  Future<void> checkServerStatus(BotServer server) async {
    try {
      final isReachable = await apiService.checkServerReachable(server);
      _connectionStatusController.add(
        ConnectionStatus(
          state: isReachable ? ConnectionState.available : ConnectionState.unavailable,
          server: server,
          message: isReachable ? 'Server is reachable' : 'Server is unreachable',
        ),
      );
    } catch (e) {
      _connectionStatusController.add(
        ConnectionStatus(
          state: ConnectionState.error,
          server: server,
          message: 'Error checking server status: $e',
        ),
      );
    }
  }
  
  void dispose() {
    _stopReconnectionTimer();
    _connectivitySubscription?.cancel();
    _connectionStatusController.close();
  }
}

enum ConnectionState {
  connected,
  connecting,
  reconnecting,
  disconnected,
  available,
  unavailable,
  error,
}

class ConnectionStatus {
  final ConnectionState state;
  final BotServer? server;
  final String message;
  final dynamic error;
  
  const ConnectionStatus({
    required this.state,
    this.server,
    required this.message,
    this.error,
  });
  
  bool get isConnected => state == ConnectionState.connected;
  bool get isConnecting => 
      state == ConnectionState.connecting || 
      state == ConnectionState.reconnecting;
  bool get hasError => state == ConnectionState.error;
}
