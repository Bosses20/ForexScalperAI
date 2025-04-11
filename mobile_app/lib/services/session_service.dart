import 'dart:async';
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logging/logging.dart';
import '../models/auth/auth_model.dart';
import '../models/bot_server.dart';
import 'api_service.dart';

/// Service responsible for managing user sessions, tokens, and authentication state
class SessionService {
  static final _logger = Logger('SessionService');
  final ApiService _apiService;
  final FlutterSecureStorage _secureStorage;
  
  // Keys for secure storage
  static const String _tokenKey = 'auth_token';
  static const String _serverKey = 'last_server';
  static const String _accountKey = 'account';
  static const String _userInfoKey = 'user_info';
  
  // Token refresh timing (refresh when 75% of lifetime has passed)
  static const double _refreshThreshold = 0.75;
  
  // Session management
  AuthToken? _currentToken;
  MT5User? _currentUser;
  BotServer? _currentServer;
  Timer? _refreshTimer;
  
  // Stream controllers for auth state
  final _authStateController = StreamController<bool>.broadcast();
  Stream<bool> get authStateStream => _authStateController.stream;
  
  SessionService({
    required ApiService apiService,
    FlutterSecureStorage? secureStorage,
  }) : _apiService = apiService,
       _secureStorage = secureStorage ?? const FlutterSecureStorage();
  
  /// Initialize the session service and try to restore the session
  Future<bool> initialize() async {
    try {
      // Try to restore session from secure storage
      final tokenJson = await _secureStorage.read(key: _tokenKey);
      final serverJson = await _secureStorage.read(key: _serverKey);
      final userInfoJson = await _secureStorage.read(key: _userInfoKey);
      
      if (tokenJson != null && serverJson != null) {
        // Parse saved data
        final tokenData = jsonDecode(tokenJson);
        final serverData = jsonDecode(serverJson);
        final userInfo = userInfoJson != null ? jsonDecode(userInfoJson) : null;
        
        // Reconstruct objects
        _currentToken = AuthToken.fromJson(tokenData);
        _currentServer = BotServer.fromJson(serverData);
        
        if (userInfo != null) {
          _currentUser = MT5User.fromJson(userInfo);
        }
        
        // Check if token is still valid
        if (!_currentToken!.isExpired) {
          _apiService.setBaseUrl(_currentServer!.getUrl());
          _apiService.setToken(_currentToken!.accessToken);
          
          // Schedule token refresh
          _scheduleTokenRefresh();
          
          _logger.info('Session restored successfully');
          _authStateController.add(true);
          return true;
        } else {
          _logger.info('Saved token is expired, clearing session');
          await clearSession();
        }
      }
      
      _authStateController.add(false);
      return false;
    } catch (e) {
      _logger.warning('Failed to restore session: $e');
      await clearSession();
      _authStateController.add(false);
      return false;
    }
  }
  
  /// Create a new session with the provided token and user info
  Future<void> createSession({
    required AuthToken token,
    required MT5User user,
    required BotServer server,
  }) async {
    try {
      _currentToken = token;
      _currentUser = user;
      _currentServer = server;
      
      // Store session data
      await _secureStorage.write(key: _tokenKey, value: jsonEncode(token.toJson()));
      await _secureStorage.write(key: _serverKey, value: jsonEncode(server.toJson()));
      await _secureStorage.write(key: _userInfoKey, value: jsonEncode(user.toJson()));
      
      // Set API token
      _apiService.setToken(token.accessToken);
      
      // Schedule token refresh
      _scheduleTokenRefresh();
      
      _logger.info('Session created for user ${user.accountId}');
      _authStateController.add(true);
    } catch (e) {
      _logger.severe('Failed to create session: $e');
      throw Exception('Failed to create session: $e');
    }
  }
  
  /// Clear the current session
  Future<void> clearSession() async {
    try {
      _currentToken = null;
      _currentUser = null;
      
      // Clear refresh timer
      _refreshTimer?.cancel();
      _refreshTimer = null;
      
      // Clear secure storage keys related to authentication
      await _secureStorage.delete(key: _tokenKey);
      await _secureStorage.delete(key: _userInfoKey);
      
      // Note: We keep the server info for convenience
      
      // Clear API token
      _apiService.clearToken();
      
      _logger.info('Session cleared');
      _authStateController.add(false);
    } catch (e) {
      _logger.warning('Error clearing session: $e');
      // Still notify we're logged out even if there was an error
      _authStateController.add(false);
    }
  }
  
  /// Get the current user if logged in
  MT5User? get currentUser => _currentUser;
  
  /// Get the current server
  BotServer? get currentServer => _currentServer;
  
  /// Check if user is authenticated
  bool get isAuthenticated => _currentToken != null && !_currentToken!.isExpired;
  
  /// Schedule token refresh before it expires
  void _scheduleTokenRefresh() {
    // Cancel any existing timer
    _refreshTimer?.cancel();
    
    if (_currentToken == null) return;
    
    // Calculate time until refresh (75% of token lifetime)
    final tokenDuration = Duration(seconds: _currentToken!.expiresIn);
    final refreshIn = Duration(milliseconds: (tokenDuration.inMilliseconds * _refreshThreshold).round());
    
    _logger.info('Scheduling token refresh in ${refreshIn.inMinutes} minutes');
    
    // Create a timer to refresh the token
    _refreshTimer = Timer(refreshIn, _refreshToken);
  }
  
  /// Refresh the authentication token
  Future<void> _refreshToken() async {
    try {
      if (_currentToken == null || _currentServer == null) {
        _logger.warning('Cannot refresh token: No current token or server');
        return;
      }
      
      _logger.info('Refreshing authentication token');
      
      // Call API to refresh token
      final refreshedToken = await _apiService.refreshToken();
      
      if (refreshedToken != null) {
        // Update current token
        _currentToken = refreshedToken;
        
        // Update stored token
        await _secureStorage.write(key: _tokenKey, value: jsonEncode(refreshedToken.toJson()));
        
        // Update API token
        _apiService.setToken(refreshedToken.accessToken);
        
        // Schedule next refresh
        _scheduleTokenRefresh();
        
        _logger.info('Token refreshed successfully');
      } else {
        _logger.warning('Failed to refresh token, will clear session');
        await clearSession();
      }
    } catch (e) {
      _logger.warning('Error refreshing token: $e');
      await clearSession();
    }
  }
  
  /// Save user credentials for quick login (if requested by user)
  Future<void> saveCredentials({
    required String account,
    required BotServer server,
    bool rememberPassword = false,
    String? password,
  }) async {
    try {
      await _secureStorage.write(key: _accountKey, value: account);
      await _secureStorage.write(key: _serverKey, value: jsonEncode(server.toJson()));
      
      // Only store password if explicitly requested for convenience (not recommended for security)
      if (rememberPassword && password != null) {
        await _secureStorage.write(key: 'password', value: password);
      } else {
        await _secureStorage.delete(key: 'password');
      }
    } catch (e) {
      _logger.warning('Failed to save credentials: $e');
    }
  }
  
  /// Get saved credentials for quick login
  Future<Map<String, dynamic>> getSavedCredentials() async {
    try {
      final account = await _secureStorage.read(key: _accountKey);
      final serverJson = await _secureStorage.read(key: _serverKey);
      final password = await _secureStorage.read(key: 'password');
      
      BotServer? server;
      if (serverJson != null) {
        try {
          server = BotServer.fromJson(jsonDecode(serverJson));
        } catch (e) {
          _logger.warning('Failed to parse server JSON: $e');
        }
      }
      
      return {
        'account': account,
        'server': server,
        'password': password,
        'hasPassword': password != null,
      };
    } catch (e) {
      _logger.warning('Failed to get saved credentials: $e');
      return {};
    }
  }
  
  /// Dispose resources
  void dispose() {
    _refreshTimer?.cancel();
    _authStateController.close();
  }
}
