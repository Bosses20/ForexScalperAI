import 'dart:async';

import 'package:flutter_bloc/flutter_bloc.dart';

import '../../models/bot_server.dart';
import '../../services/api_service.dart';
import '../../services/network_discovery_service.dart';
import '../../services/websocket_service.dart';
import '../../utils/logger.dart';
import 'network_discovery_event.dart';
import 'network_discovery_state.dart';

/// BLoC for managing network discovery and server connections
class NetworkDiscoveryBloc extends Bloc<NetworkDiscoveryEvent, NetworkDiscoveryState> {
  static const String _logTag = 'NetworkDiscoveryBloc';
  final Logger _logger = Logger(_logTag);
  
  final NetworkDiscoveryService _discoveryService;
  final ApiService _apiService;
  final WebSocketService _webSocketService;
  StreamSubscription? _serversSubscription;
  
  NetworkDiscoveryBloc({
    NetworkDiscoveryService? discoveryService,
    ApiService? apiService,
    WebSocketService? webSocketService,
  }) : _discoveryService = discoveryService ?? NetworkDiscoveryService(),
       _apiService = apiService ?? ApiService(),
       _webSocketService = webSocketService ?? WebSocketService(),
       super(const NetworkDiscoveryInitial()) {
    on<LoadCachedServersEvent>(_onLoadCachedServers);
    on<StartNetworkScanEvent>(_onStartNetworkScan);
    on<AddManualServerEvent>(_onAddManualServer);
    on<RemoveServerEvent>(_onRemoveServer);
    on<ToggleServerFavoriteEvent>(_onToggleServerFavorite);
    on<ConnectToServerEvent>(_onConnectToServer);
    on<ScanQrCodeEvent>(_onScanQrCode);
    
    // Subscribe to server discovery updates
    _serversSubscription = _discoveryService.serversStream.listen(_onServersUpdated);
  }
  
  void _onServersUpdated(List<BotServer> servers) {
    if (state is ServersLoadedState) {
      final currentState = state as ServersLoadedState;
      emit(currentState.copyWith(servers: servers));
    }
  }
  
  Future<void> _onLoadCachedServers(
    LoadCachedServersEvent event, 
    Emitter<NetworkDiscoveryState> emit
  ) async {
    _logger.i('Loading cached servers');
    
    emit(const LoadingCachedServersState());
    
    try {
      final servers = await _discoveryService.loadCachedServers();
      emit(ServersLoadedState(servers: servers));
    } catch (e) {
      _logger.e('Error loading cached servers: $e');
      emit(NetworkDiscoveryErrorState(
        message: 'Failed to load cached servers: $e',
        servers: [],
      ));
    }
  }
  
  Future<void> _onStartNetworkScan(
    StartNetworkScanEvent event, 
    Emitter<NetworkDiscoveryState> emit
  ) async {
    _logger.i('Starting network scan');
    
    // Check if connected to WiFi
    if (!await _discoveryService.isConnectedToWifi()) {
      if (state is ServersLoadedState) {
        final currentState = state as ServersLoadedState;
        emit(currentState.copyWith(
          error: 'WiFi connection required for network scanning',
        ));
      } else {
        emit(const NetworkDiscoveryErrorState(
          message: 'WiFi connection required for network scanning',
        ));
      }
      return;
    }
    
    emit(const ScanningNetworkState());
    
    try {
      final servers = await _discoveryService.scanNetwork();
      emit(ServersLoadedState(servers: servers));
    } catch (e) {
      _logger.e('Error scanning network: $e');
      
      // Return to loaded state if possible, with error message
      if (state is ServersLoadedState) {
        final currentState = state as ServersLoadedState;
        emit(currentState.copyWith(
          error: 'Network scan failed: $e',
        ));
      } else {
        emit(NetworkDiscoveryErrorState(
          message: 'Network scan failed: $e',
        ));
      }
    }
  }
  
  Future<void> _onAddManualServer(
    AddManualServerEvent event, 
    Emitter<NetworkDiscoveryState> emit
  ) async {
    _logger.i('Adding manual server: ${event.server}');
    
    try {
      await _discoveryService.addManualServer(event.server);
      
      if (state is ServersLoadedState) {
        // The state will be updated via serversStream
      } else {
        emit(ServersLoadedState(servers: _discoveryService.discoveredServers));
      }
    } catch (e) {
      _logger.e('Error adding manual server: $e');
      
      if (state is ServersLoadedState) {
        final currentState = state as ServersLoadedState;
        emit(currentState.copyWith(
          error: 'Failed to add server: $e',
        ));
      } else {
        emit(NetworkDiscoveryErrorState(
          message: 'Failed to add server: $e',
          servers: _discoveryService.discoveredServers,
        ));
      }
    }
  }
  
  Future<void> _onRemoveServer(
    RemoveServerEvent event, 
    Emitter<NetworkDiscoveryState> emit
  ) async {
    _logger.i('Removing server: ${event.server}');
    
    try {
      await _discoveryService.removeServer(event.server);
      
      // State will be updated via serversStream
    } catch (e) {
      _logger.e('Error removing server: $e');
      
      if (state is ServersLoadedState) {
        final currentState = state as ServersLoadedState;
        emit(currentState.copyWith(
          error: 'Failed to remove server: $e',
        ));
      }
    }
  }
  
  Future<void> _onToggleServerFavorite(
    ToggleServerFavoriteEvent event, 
    Emitter<NetworkDiscoveryState> emit
  ) async {
    _logger.i('Toggling server favorite: ${event.server}');
    
    try {
      // Toggle favorite status
      final updatedServer = event.server.copyWith(
        isFavorite: !event.server.isFavorite,
      );
      
      // Update server in discovery service
      await _discoveryService.addManualServer(updatedServer);
      
      // State will be updated via serversStream
    } catch (e) {
      _logger.e('Error toggling server favorite: $e');
      
      if (state is ServersLoadedState) {
        final currentState = state as ServersLoadedState;
        emit(currentState.copyWith(
          error: 'Failed to update server: $e',
        ));
      }
    }
  }
  
  Future<void> _onConnectToServer(
    ConnectToServerEvent event, 
    Emitter<NetworkDiscoveryState> emit
  ) async {
    _logger.i('Connecting to server: ${event.server}');
    
    emit(ConnectingToServerState(event.server));
    
    try {
      // 1. Try to connect to server and verify it's reachable
      final serverInfo = await _apiService.getServerInfo(event.server);
      if (serverInfo == null) {
        throw Exception('Server not responding or invalid response');
      }
      
      // 2. Set the server as the current active server for API and WebSocket services
      _apiService.setActiveServer(event.server);
      
      // 3. Initialize WebSocket connection if needed
      if (serverInfo['websocket_enabled'] == true) {
        final wsConnected = await _webSocketService.connect(event.server);
        if (!wsConnected) {
          _logger.w('WebSocket connection failed, but HTTP connection succeeded');
          // Continue anyway, as WebSocket might not be essential
        }
      }
      
      // 4. Update the server with last connected timestamp
      final updatedServer = event.server.copyWith(
        lastConnected: DateTime.now(),
        version: serverInfo['version'] ?? event.server.version,
        requiresAuth: serverInfo['requires_auth'] ?? event.server.requiresAuth,
      );
      
      // 5. Update server in discovery service
      await _discoveryService.addManualServer(updatedServer);
      
      // 6. Emit success state
      if (state is ConnectingToServerState) {
        emit(ServersLoadedState(
          servers: _discoveryService.discoveredServers,
          isConnected: true,
          connectedServer: updatedServer,
        ));
      }
    } catch (e) {
      _logger.e('Error connecting to server: $e');
      
      emit(ServersLoadedState(
        servers: _discoveryService.discoveredServers,
        error: 'Failed to connect to server: $e',
      ));
    }
  }
  
  Future<void> _onScanQrCode(
    ScanQrCodeEvent event, 
    Emitter<NetworkDiscoveryState> emit
  ) async {
    _logger.i('Processing QR code');
    
    try {
      final server = _discoveryService.parseQrCode(event.qrData);
      
      if (server == null) {
        _logger.w('Invalid QR code format');
        
        if (state is ServersLoadedState) {
          final currentState = state as ServersLoadedState;
          emit(currentState.copyWith(
            error: 'Invalid QR code format. Expected format: forexbot://{host}:{port}',
          ));
        } else {
          emit(NetworkDiscoveryErrorState(
            message: 'Invalid QR code format. Expected format: forexbot://{host}:{port}',
            servers: _discoveryService.discoveredServers,
          ));
        }
        return;
      }
      
      // Add the server from QR code
      await _discoveryService.addManualServer(server);
      
      // Attempt to connect to the server
      add(ConnectToServerEvent(server: server));
    } catch (e) {
      _logger.e('Error processing QR code: $e');
      
      if (state is ServersLoadedState) {
        final currentState = state as ServersLoadedState;
        emit(currentState.copyWith(
          error: 'Failed to process QR code: $e',
        ));
      } else {
        emit(NetworkDiscoveryErrorState(
          message: 'Failed to process QR code: $e',
          servers: _discoveryService.discoveredServers,
        ));
      }
    }
  }
  
  @override
  Future<void> close() {
    _serversSubscription?.cancel();
    return super.close();
  }
}
