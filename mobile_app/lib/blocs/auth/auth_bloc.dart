import 'dart:async';
import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logging/logging.dart';
import '../../models/auth/auth_model.dart';
import '../../models/bot_server.dart';
import '../../services/api_service.dart';
import '../../services/session_service.dart';
import '../../services/websocket_service.dart';

// Events
abstract class AuthEvent extends Equatable {
  const AuthEvent();

  @override
  List<Object?> get props => [];
}

class AppStartedEvent extends AuthEvent {}

class LoginRequestedEvent extends AuthEvent {
  final String account;
  final String password;
  final BotServer server;
  final bool rememberMe;

  const LoginRequestedEvent({
    required this.account,
    required this.password,
    required this.server,
    this.rememberMe = false,
  });

  @override
  List<Object?> get props => [account, server, rememberMe];
}

class LogoutEvent extends AuthEvent {}

class ConnectToServerEvent extends AuthEvent {
  final BotServer server;

  const ConnectToServerEvent({
    required this.server,
  });

  @override
  List<Object?> get props => [server];
}

class DiscoverServersEvent extends AuthEvent {}

class CheckAuthStatusEvent extends AuthEvent {}

class RegisterRequestedEvent extends AuthEvent {}

// States
abstract class AuthState extends Equatable {
  const AuthState();
  
  @override
  List<Object?> get props => [];
}

class InitialAuthState extends AuthState {}

class AuthLoadingState extends AuthState {}

class AuthenticatedState extends AuthState {
  final String username;
  final String accountId;
  final String token;
  final BotServer server;
  final double? balance;
  final double? equity;

  const AuthenticatedState({
    required this.username,
    required this.accountId,
    required this.token,
    required this.server,
    this.balance,
    this.equity,
  });

  @override
  List<Object?> get props => [username, accountId, token, server, balance, equity];
}

class UnauthenticatedState extends AuthState {}

class ServerConnectedState extends AuthState {
  final BotServer server;

  const ServerConnectedState({
    required this.server,
  });

  @override
  List<Object?> get props => [server];
}

class ServerDiscoveryState extends AuthState {
  final List<BotServer> discoveredServers;
  final bool isDiscovering;

  const ServerDiscoveryState({
    required this.discoveredServers,
    required this.isDiscovering,
  });

  @override
  List<Object?> get props => [discoveredServers, isDiscovering];
}

class AuthErrorState extends AuthState {
  final String message;

  const AuthErrorState(this.message);

  @override
  List<Object?> get props => [message];
}

// Bloc
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final Logger _logger = Logger('AuthBloc');
  final ApiService _apiService;
  final WebSocketService _wsService;
  final SessionService _sessionService;
  final FlutterSecureStorage _secureStorage;
  StreamSubscription? _authStateSubscription;

  AuthBloc({
    required ApiService apiService,
    required WebSocketService wsService,
    required SessionService sessionService,
    FlutterSecureStorage? secureStorage,
  }) : _apiService = apiService,
       _wsService = wsService,
       _sessionService = sessionService,
       _secureStorage = secureStorage ?? const FlutterSecureStorage(),
       super(const InitialAuthState()) {
    on<AppStartedEvent>(_onAppStarted);
    on<CheckAuthStatusEvent>(_onCheckAuthStatus);
    on<LoginRequestedEvent>(_onLogin);
    on<LogoutEvent>(_onLogout);
    on<ConnectToServerEvent>(_onConnectToServer);
    on<DiscoverServersEvent>(_onDiscoverServers);
    on<RegisterRequestedEvent>(_onRegister);
    
    // Listen to session service auth state changes
    _authStateSubscription = _sessionService.authStateStream.listen((isAuthenticated) {
      if (!isAuthenticated && state is AuthenticatedState) {
        add(LogoutEvent());
      }
    });
  }

  @override
  Future<void> close() {
    _authStateSubscription?.cancel();
    return super.close();
  }

  Future<void> _onAppStarted(
    AppStartedEvent event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoadingState());
    
    try {
      _logger.i('App started, initializing session');
      
      // Initialize session service which will attempt to restore session
      final isAuthenticated = await _sessionService.initialize();
      
      if (isAuthenticated) {
        final user = _sessionService.currentUser;
        final server = _sessionService.currentServer;
        
        if (user != null && server != null) {
          emit(AuthenticatedState(
            username: user.name ?? 'MT5 Trader',
            accountId: user.accountId,
            token: 'restored_from_session',
            server: server,
            balance: user.balance,
            equity: user.equity,
          ));
          
          // Connect to WebSocket for real-time updates
          _wsService.connect(server.getUrl());
          
          _logger.i('Session restored for account: ${user.accountId}');
          return;
        }
      }
      
      emit(UnauthenticatedState());
      _logger.i('No valid session found, user needs to login');
    } catch (e) {
      _logger.e('Error during app start: $e');
      emit(UnauthenticatedState());
    }
  }

  Future<void> _onCheckAuthStatus(
    CheckAuthStatusEvent event,
    Emitter<AuthState> emit,
  ) async {
    try {
      if (_sessionService.isAuthenticated) {
        final user = _sessionService.currentUser;
        final server = _sessionService.currentServer;
        
        if (user != null && server != null) {
          emit(AuthenticatedState(
            username: user.name ?? 'MT5 Trader',
            accountId: user.accountId,
            token: 'from_session_check',
            server: server,
            balance: user.balance,
            equity: user.equity,
          ));
          return;
        }
      }
      
      emit(UnauthenticatedState());
    } catch (e) {
      _logger.e('Error checking auth status: $e');
      emit(UnauthenticatedState());
    }
  }

  Future<void> _onLogin(
    LoginRequestedEvent event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoadingState());
    
    try {
      _logger.i('Processing login for MT5 account: ${event.account}');
      
      // Make sure we have a server selected and API service initialized
      _apiService.setBaseUrl(event.server.getUrl());
      
      // Attempt to login
      final response = await _apiService.login(
        account: event.account,
        password: event.password,
      );
      
      // If we get a token, login was successful
      if (response.containsKey('token')) {
        final token = response['token'] as String;
        _apiService.setToken(token);
        
        // Connect to WebSocket
        _wsService.connect(event.server.getUrl());
        
        // Create AuthToken object
        final authToken = AuthToken(
          accessToken: token,
          tokenType: 'bearer',
          expiresIn: response['expires_in'] ?? 1800, // default 30 min
          scopes: ['read', 'write'],
          createdAt: DateTime.now(),
        );
        
        // Create MT5User object
        final mt5User = MT5User(
          accountId: event.account,
          serverName: event.server.name,
          scopes: ['read', 'write'],
          name: response['username'],
          balance: response['balance'] != null ? double.tryParse(response['balance'].toString()) : null,
          equity: response['equity'] != null ? double.tryParse(response['equity'].toString()) : null,
        );
        
        // Create session
        await _sessionService.createSession(
          token: authToken,
          user: mt5User,
          server: event.server,
        );
        
        // Save credentials if remember me is checked
        if (event.rememberMe) {
          await _sessionService.saveCredentials(
            account: event.account,
            server: event.server,
            // Optionally store password - though not recommended for security
            rememberPassword: false,
          );
        }
        
        // Update the server's last connection time
        final updatedServer = event.server.copyWith(
          lastConnected: DateTime.now(),
        );
        
        emit(AuthenticatedState(
          username: response['username'] ?? 'MT5 Trader',
          accountId: event.account,
          token: token,
          server: updatedServer,
          balance: response['balance'] != null ? double.tryParse(response['balance'].toString()) : null,
          equity: response['equity'] != null ? double.tryParse(response['equity'].toString()) : null,
        ));
        
        _logger.i('Login successful for MT5 account: ${event.account}');
      } else {
        emit(AuthErrorState(message: 'Login failed: Invalid MT5 credentials'));
        _logger.w('Login failed: Invalid MT5 credentials');
      }
    } catch (e) {
      _logger.e('MT5 login error: $e');
      emit(AuthErrorState(message: 'Login failed: ${e.toString()}'));
    }
  }

  Future<void> _onLogout(
    LogoutEvent event,
    Emitter<AuthState> emit,
  ) async {
    try {
      _logger.i('Logging out');
      
      // Clear auth token
      await _sessionService.clearSession();
      
      // Disconnect WebSocket
      _wsService.disconnect();
      
      emit(UnauthenticatedState());
      
      _logger.i('Logged out successfully');
    } catch (e) {
      _logger.e('Logout error: $e');
      emit(AuthErrorState(message: 'Logout failed: ${e.toString()}'));
    }
  }

  Future<void> _onConnectToServer(
    ConnectToServerEvent event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoadingState());
    
    try {
      _logger.i('Connecting to server: ${event.server.name}');
      
      // Set the base URL for the API service
      _apiService.setBaseUrl(event.server.getUrl());
      
      // Try to connect and verify the server is available
      final isAvailable = await _apiService.ping();
      
      if (isAvailable) {
        // Store the server for future reference
        await _secureStorage.write(key: 'last_server', value: event.server.toJson());
        
        // Update the server's last connection time
        final updatedServer = event.server.copyWith(
          lastConnected: DateTime.now(),
        );
        
        emit(ServerConnectedState(server: updatedServer));
        _logger.i('Connected to server successfully');
      } else {
        emit(AuthErrorState(message: 'Could not connect to server: ${event.server.name}'));
        _logger.w('Server connection failed: Server not available');
      }
    } catch (e) {
      _logger.e('Server connection error: $e');
      emit(AuthErrorState(message: 'Connection failed: ${e.toString()}'));
    }
  }

  Future<void> _onDiscoverServers(
    DiscoverServersEvent event,
    Emitter<AuthState> emit,
  ) async {
    emit(ServerDiscoveryState(discoveredServers: [], isDiscovering: true));
    try {
      // Discover available servers
      final servers = await _apiService.discoverServers();
      
      if (servers.isNotEmpty) {
        emit(ServerDiscoveryState(
          discoveredServers: servers,
          isDiscovering: false,
        ));
        _logger.i('Discovered ${servers.length} servers');
      } else {
        emit(ServerDiscoveryState(
          discoveredServers: [],
          isDiscovering: false,
        ));
        _logger.w('No servers discovered');
      }
    } catch (e) {
      _logger.e('Server discovery error: $e');
      emit(AuthErrorState(message: 'Server discovery error: ${e.toString()}'));
      emit(ServerDiscoveryState(discoveredServers: [], isDiscovering: false));
    }
  }

  Future<void> _onRegister(
    RegisterRequestedEvent event,
    Emitter<AuthState> emit,
  ) async {
    // TO DO: implement registration logic
  }
}
