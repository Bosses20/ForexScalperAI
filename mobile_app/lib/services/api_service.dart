import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/bot_server.dart';
import '../models/market/market_condition.dart';
import '../models/trading/trading_instrument.dart';
import '../models/auth/auth_model.dart';
import '../utils/logger.dart';

class ApiService {
  final Dio _dio = Dio();
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final Logger _logger = Logger('ApiService');
  
  static const String _tokenKey = 'auth_token';
  static const String _serversKey = 'cached_servers';
  static const String _activeServerKey = 'active_server';
  
  // Current active server
  BotServer? _activeServer;
  
  // Singleton pattern
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal() {
    _initializeDio();
    _loadActiveServer();
  }
  
  void _initializeDio() async {
    _dio.options = BaseOptions(
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      validateStatus: (status) => status != null && status < 500,
    );
    
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        // Add JWT token to every request if available
        final token = await getToken();
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (DioException e, handler) async {
        // Handle token refresh if we get a 401
        if (e.response?.statusCode == 401) {
          // Try to refresh token
          final refreshed = await _refreshToken();
          if (refreshed) {
            // Retry the request with the new token
            return handler.resolve(await _dio.fetch(e.requestOptions));
          }
        }
        return handler.next(e);
      },
    ));
  }
  
  /// Load the active server from secure storage
  Future<void> _loadActiveServer() async {
    try {
      final serverJson = await _secureStorage.read(key: _activeServerKey);
      if (serverJson != null) {
        _activeServer = BotServer.fromJson(serverJson);
        _logger.i('Loaded active server: ${_activeServer?.name}');
      }
    } catch (e) {
      _logger.e('Error loading active server: $e');
    }
  }
  
  /// Get information about a server
  Future<Map<String, dynamic>?> getServerInfo(BotServer server) async {
    try {
      _logger.i('Getting server info from ${server.baseUrl}/api/info');
      
      final response = await _dio.get(
        '${server.baseUrl}/api/info',
        options: Options(
          // Short timeout for server info check
          sendTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
        ),
      );
      
      if (response.statusCode == 200 && response.data != null) {
        if (response.data is Map) {
          return response.data;
        } else if (response.data is String) {
          // Try to parse JSON string
          try {
            return jsonDecode(response.data);
          } catch (e) {
            _logger.e('Failed to parse server info response: $e');
          }
        }
      }
      
      _logger.w('Invalid server info response: ${response.statusCode}');
      return null;
    } on DioException catch (e) {
      _logger.e('Failed to connect to server: ${e.message}');
      return null;
    } catch (e) {
      _logger.e('Error fetching server info: $e');
      return null;
    }
  }
  
  /// Set the active server for API requests
  Future<void> setActiveServer(BotServer server) async {
    _activeServer = server;
    _logger.i('Set active server to ${server.name} (${server.host}:${server.port})');
    
    // Update base URL for Dio
    _dio.options.baseUrl = server.baseUrl;
    
    // Save active server to secure storage
    try {
      await _secureStorage.write(
        key: _activeServerKey,
        value: server.toJson(),
      );
    } catch (e) {
      _logger.e('Error saving active server: $e');
    }
  }
  
  /// Get the currently active server
  BotServer? getActiveServer() {
    return _activeServer;
  }
  
  /// Check if we have an active server configured
  bool hasActiveServer() {
    return _activeServer != null;
  }
  
  // Base URL and token management
  void setBaseUrl(String url) {
    _dio.options.baseUrl = url;
    _logger.d('API base URL set to: $url');
  }
  
  Future<String?> getToken() async {
    return await _secureStorage.read(key: _tokenKey);
  }
  
  void setToken(String token) {
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }
  
  void clearToken() {
    _dio.options.headers.remove('Authorization');
  }
  
  Future<bool> _refreshToken() async {
    try {
      // Get current server
      if (_activeServer == null) return false;
      
      // Try to refresh the token using refresh token if available
      final refreshToken = await _secureStorage.read(key: 'refresh_token');
      if (refreshToken == null) return false;
      
      final response = await _dio.post(
        '${_activeServer!.baseUrl}/auth/refresh',
        data: {
          'refresh_token': refreshToken,
        },
        options: Options(
          headers: {
            'Content-Type': 'application/json',
          },
        ),
      );
      
      if (response.statusCode == 200 && response.data != null) {
        final token = AuthToken.fromJson(response.data);
        
        // Save the new access token
        await _secureStorage.write(key: _tokenKey, value: token.accessToken);
        
        // Update the headers
        setToken(token.accessToken);
        
        _logger.i('Successfully refreshed token');
        return true;
      }
      
      _logger.w('Failed to refresh token: ${response.statusCode}');
      return false;
    } catch (e) {
      _logger.e('Error refreshing token: $e');
      return false;
    }
  }
  
  /// Attempt to refresh the authentication token
  Future<AuthToken?> refreshToken() async {
    try {
      if (_activeServer == null) {
        throw Exception('No active server');
      }

      final currentToken = await _secureStorage.read(key: _tokenKey);
      if (currentToken == null || currentToken.isEmpty) {
        _logger.w('No token to refresh');
        return null;
      }

      _logger.i('Refreshing token');
      
      final response = await _dio.post(
        '${_activeServer!.baseUrl}/auth/refresh',
        options: Options(
          headers: {
            'Authorization': 'Bearer $currentToken',
          },
        ),
      );
      
      if (response.statusCode == 200 && response.data != null) {
        final authToken = AuthToken.fromJson(response.data);
        
        // Save the refreshed token
        await _secureStorage.write(key: _tokenKey, value: authToken.accessToken);
        
        // Set the refreshed token for future requests
        setToken(authToken.accessToken);
        
        _logger.i('Token refreshed successfully');
        
        return authToken;
      } else {
        _logger.w('Token refresh failed: ${response.statusCode} ${response.statusMessage}');
        return null;
      }
    } on DioException catch (e) {
      _logger.e('Token refresh error: ${e.response?.data ?? e.message}');
      return null;
    } catch (e) {
      _logger.e('Token refresh error: $e');
      return null;
    }
  }
  
  // Authentication
  Future<Map<String, dynamic>> login({
    required String account,
    required String password,
  }) async {
    try {
      if (_activeServer == null) {
        throw Exception('No active server');
      }
      
      _logger.i('Logging in to ${_activeServer!.name} with MT5 account: $account');
      
      final response = await _dio.post(
        '${_activeServer!.baseUrl}/auth/token',
        data: jsonEncode({
          'login': account,           // Using 'login' instead of 'username' for MT5
          'password': password,
          'server': _activeServer!.name,
        }),
        options: Options(
          contentType: 'application/json',
          headers: {
            'Content-Type': 'application/json',
          },
        ),
      );
      
      if (response.statusCode == 200 && response.data != null) {
        final authToken = AuthToken.fromJson(response.data);
        
        // Save the token to secure storage
        await _secureStorage.write(key: _tokenKey, value: authToken.accessToken);
        
        // Set the token for future requests
        setToken(authToken.accessToken);
        
        // Get user info now that we're authenticated
        final userInfo = await getUserInfo();
        
        _logger.i('Login successful for MT5 account: $account');
        
        return {
          'token': authToken.accessToken,
          'account_id': account,
          'username': userInfo['name'] ?? 'MT5 Trader',
          'balance': userInfo['balance'],
          'equity': userInfo['equity'],
          'server': _activeServer!.name,
          'expires_in': authToken.expiresIn,
        };
      } else {
        _logger.w('Login failed: ${response.statusCode} ${response.statusMessage}');
        throw Exception('Login failed: ${response.statusMessage}');
      }
    } on DioException catch (e) {
      _logger.e('Login error: ${e.response?.data ?? e.message}');
      throw Exception('Login failed: ${e.response?.data?['detail'] ?? e.message}');
    } catch (e) {
      _logger.e('Login error: $e');
      throw Exception('Login failed: ${e.toString()}');
    }
  }
  
  Future<Map<String, dynamic>> getUserInfo() async {
    try {
      final response = await _dio.get('/auth/user');
      return response.data;
    } catch (e) {
      _logger.e('Failed to get user info: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/auth/user'),
        error: 'Failed to get user info: ${e.toString()}',
      );
    }
  }
  
  // Server discovery and connection
  Future<bool> ping() async {
    try {
      final response = await _dio.get('/ping', 
        options: Options(
          // Short timeout for ping
          sendTimeout: const Duration(seconds: 2),
          receiveTimeout: const Duration(seconds: 2),
        ),
      );
      return response.statusCode == 200;
    } catch (e) {
      _logger.d('Ping failed: $e');
      return false;
    }
  }
  
  Future<List<BotServer>> discoverServers() async {
    _logger.i('Discovering servers on local network');
    final List<BotServer> servers = [];
    
    try {
      // First, get cached servers
      final cachedServers = await getCachedServers();
      servers.addAll(cachedServers);
      
      // Use network discovery service to find more servers
      // This will be implemented in the NetworkDiscoveryService
      // For now, we'll return the cached servers
      return servers;
    } catch (e) {
      _logger.e('Error discovering servers: $e');
      return servers;
    }
  }
  
  Future<List<BotServer>> getCachedServers() async {
    try {
      final serversJson = await _secureStorage.read(key: _serversKey);
      if (serversJson == null || serversJson.isEmpty) {
        return [];
      }
      
      final List<dynamic> serversList = jsonDecode(serversJson);
      return serversList
          .map((serverMap) => BotServer.fromJson(serverMap))
          .toList();
    } catch (e) {
      _logger.e('Error getting cached servers: $e');
      return [];
    }
  }
  
  Future<void> cacheServer(BotServer server) async {
    try {
      // Get existing cached servers
      final servers = await getCachedServers();
      
      // Check if server already exists in cache
      final index = servers.indexWhere((s) => s.host == server.host && s.port == server.port);
      
      if (index >= 0) {
        // Update existing server
        servers[index] = server;
      } else {
        // Add new server
        servers.add(server);
      }
      
      // Save updated list
      final serversJson = jsonEncode(servers.map((s) => s.toJson()).toList());
      await _secureStorage.write(key: _serversKey, value: serversJson);
      _logger.d('Server cached: ${server.name}');
    } catch (e) {
      _logger.e('Error caching server: $e');
    }
  }
  
  Future<void> removeServerFromCache(BotServer server) async {
    try {
      // Get existing cached servers
      final servers = await getCachedServers();
      
      // Remove server if it exists
      servers.removeWhere((s) => s.host == server.host && s.port == server.port);
      
      // Save updated list
      final serversJson = jsonEncode(servers.map((s) => s.toJson()).toList());
      await _secureStorage.write(key: _serversKey, value: serversJson);
      _logger.d('Server removed from cache: ${server.name}');
    } catch (e) {
      _logger.e('Error removing server from cache: $e');
    }
  }
  
  // Bot Control
  Future<Map<String, dynamic>> getBotStatus() async {
    try {
      final response = await _dio.get('/bot/status');
      return response.data;
    } catch (e) {
      _logger.e('Failed to get bot status: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/bot/status'),
        error: 'Failed to get bot status: ${e.toString()}',
      );
    }
  }
  
  Future<Map<String, dynamic>> startBot() async {
    try {
      final response = await _dio.post('/bot/start');
      return response.data;
    } catch (e) {
      _logger.e('Failed to start bot: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/bot/start'),
        error: 'Failed to start bot: ${e.toString()}',
      );
    }
  }
  
  Future<Map<String, dynamic>> stopBot() async {
    try {
      final response = await _dio.post('/bot/stop');
      return response.data;
    } catch (e) {
      _logger.e('Failed to stop bot: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/bot/stop'),
        error: 'Failed to stop bot: ${e.toString()}',
      );
    }
  }
  
  // Market data and trading
  Future<MarketCondition> getCurrentMarketCondition() async {
    try {
      final response = await _dio.get('/market/conditions');
      return MarketCondition.fromJson(response.data);
    } catch (e) {
      _logger.e('Failed to get market conditions: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/market/conditions'),
        error: 'Failed to get market conditions: ${e.toString()}',
      );
    }
  }
  
  Future<List<TradingInstrument>> getActiveInstruments() async {
    try {
      final response = await _dio.get('/trading/instruments');
      final List<dynamic> data = response.data;
      return data.map((item) => TradingInstrument.fromJson(item)).toList();
    } catch (e) {
      _logger.e('Failed to get active instruments: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/trading/instruments'),
        error: 'Failed to get active instruments: ${e.toString()}',
      );
    }
  }
  
  Future<Map<String, dynamic>> toggleInstrumentActive(String symbol, bool active) async {
    try {
      final response = await _dio.post('/trading/instruments/$symbol', data: {
        'active': active,
      });
      return response.data;
    } catch (e) {
      _logger.e('Failed to toggle instrument status: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/trading/instruments/$symbol'),
        error: 'Failed to toggle instrument status: ${e.toString()}',
      );
    }
  }
  
  Future<List<dynamic>> getOpenPositions() async {
    try {
      final response = await _dio.get('/trading/positions');
      return response.data as List<dynamic>;
    } catch (e) {
      _logger.e('Failed to get open positions: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/trading/positions'),
        error: 'Failed to get open positions: ${e.toString()}',
      );
    }
  }
  
  Future<List<dynamic>> getTradeHistory({
    int limit = 50,
    String timeframe = 'day'
  }) async {
    try {
      final response = await _dio.get('/trading/history', queryParameters: {
        'limit': limit,
        'timeframe': timeframe,
      });
      return response.data as List<dynamic>;
    } catch (e) {
      _logger.e('Failed to get trade history: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/trading/history'),
        error: 'Failed to get trade history: ${e.toString()}',
      );
    }
  }
  
  Future<Map<String, dynamic>> getPerformanceMetrics() async {
    try {
      final response = await _dio.get('/analytics/performance');
      return response.data;
    } catch (e) {
      _logger.e('Failed to get performance metrics: $e');
      throw DioException(
        requestOptions: RequestOptions(path: '/analytics/performance'),
        error: 'Failed to get performance metrics: ${e.toString()}',
      );
    }
  }
  
  // Settings Management
  Future<Map<String, dynamic>?> getSettings() async {
    try {
      final response = await _dio.get('/settings');
      if (response.statusCode == 200) {
        return response.data;
      }
      _logger.w('Failed to get settings: ${response.statusCode}');
      return null;
    } catch (e) {
      _logger.e('Failed to get settings: $e');
      return null;
    }
  }
  
  Future<bool> updateSettings(Map<String, dynamic> settings) async {
    try {
      final response = await _dio.put('/settings', data: settings);
      return response.statusCode == 200;
    } catch (e) {
      _logger.e('Failed to update settings: $e');
      return false;
    }
  }
  
  Future<bool> resetSettings() async {
    try {
      final response = await _dio.post('/settings/reset');
      return response.statusCode == 200;
    } catch (e) {
      _logger.e('Failed to reset settings: $e');
      return false;
    }
  }
}
