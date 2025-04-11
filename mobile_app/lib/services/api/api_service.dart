import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:mobile_app/models/market/market_condition.dart';
import 'package:mobile_app/models/trading/trading_instrument.dart';

class ApiService {
  final Dio _dio = Dio();
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  
  static const String _baseUrlKey = 'api_base_url';
  static const String _tokenKey = 'api_token';
  static const String _defaultBaseUrl = 'http://localhost:8000'; // Default localhost FastAPI URL
  
  // Singleton pattern
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal() {
    _initializeDio();
  }
  
  void _initializeDio() async {
    final baseUrl = await getBaseUrl();
    
    _dio.options = BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      validateStatus: (status) => status != null && status < 500,
    );
    
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        // Add JWT token to every request
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
  
  Future<String> getBaseUrl() async {
    final storedUrl = await _secureStorage.read(key: _baseUrlKey);
    return storedUrl ?? _defaultBaseUrl;
  }
  
  Future<void> setBaseUrl(String url) async {
    await _secureStorage.write(key: _baseUrlKey, value: url);
    _dio.options.baseUrl = url;
  }
  
  Future<String?> getToken() async {
    return await _secureStorage.read(key: _tokenKey);
  }
  
  Future<void> setToken(String token) async {
    await _secureStorage.write(key: _tokenKey, value: token);
  }
  
  Future<void> clearToken() async {
    await _secureStorage.delete(key: _tokenKey);
  }
  
  Future<bool> _refreshToken() async {
    try {
      final response = await _dio.post('/refresh-token');
      if (response.statusCode == 200) {
        final newToken = response.data['access_token'];
        await setToken(newToken);
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }
  
  // Authentication
  Future<Map<String, dynamic>> login(String username, String password, String broker) async {
    try {
      final response = await _dio.post('/login', data: {
        'username': username,
        'password': password,
        'broker': broker
      });
      
      if (response.statusCode == 200) {
        final token = response.data['access_token'];
        await setToken(token);
        return response.data;
      } else {
        throw DioException(
          requestOptions: RequestOptions(path: '/login'),
          error: response.data['detail'] ?? 'Authentication failed',
          response: response,
        );
      }
    } catch (e) {
      if (e is DioException) {
        rethrow;
      }
      throw DioException(
        requestOptions: RequestOptions(path: '/login'),
        error: 'Connection error: ${e.toString()}',
      );
    }
  }
  
  // Bot Control
  Future<Map<String, dynamic>> getBotStatus() async {
    try {
      final response = await _dio.get('/status');
      return response.data;
    } catch (e) {
      throw DioException(
        requestOptions: RequestOptions(path: '/status'),
        error: 'Failed to get bot status: ${e.toString()}',
      );
    }
  }
  
  Future<Map<String, dynamic>> startBot() async {
    try {
      final response = await _dio.post('/start');
      return response.data;
    } catch (e) {
      throw DioException(
        requestOptions: RequestOptions(path: '/start'),
        error: 'Failed to start bot: ${e.toString()}',
      );
    }
  }
  
  Future<Map<String, dynamic>> stopBot() async {
    try {
      final response = await _dio.post('/stop');
      return response.data;
    } catch (e) {
      throw DioException(
        requestOptions: RequestOptions(path: '/stop'),
        error: 'Failed to stop bot: ${e.toString()}',
      );
    }
  }
  
  // Market Conditions
  Future<MarketCondition> getCurrentMarketCondition() async {
    try {
      final response = await _dio.get('/market-condition');
      return MarketCondition.fromJson(response.data);
    } catch (e) {
      throw DioException(
        requestOptions: RequestOptions(path: '/market-condition'),
        error: 'Failed to get market condition: ${e.toString()}',
      );
    }
  }
  
  // Trading Instruments
  Future<List<TradingInstrument>> getActiveInstruments() async {
    try {
      final response = await _dio.get('/instruments/active');
      return (response.data as List)
          .map((json) => TradingInstrument.fromJson(json))
          .toList();
    } catch (e) {
      throw DioException(
        requestOptions: RequestOptions(path: '/instruments/active'),
        error: 'Failed to get active instruments: ${e.toString()}',
      );
    }
  }
  
  Future<Map<String, dynamic>> toggleInstrumentActive(String symbol, bool active) async {
    try {
      final response = await _dio.post('/instruments/toggle', data: {
        'symbol': symbol,
        'active': active
      });
      return response.data;
    } catch (e) {
      throw DioException(
        requestOptions: RequestOptions(path: '/instruments/toggle'),
        error: 'Failed to toggle instrument: ${e.toString()}',
      );
    }
  }
  
  // Trading Positions
  Future<List<Map<String, dynamic>>> getOpenPositions() async {
    try {
      final response = await _dio.get('/positions/open');
      return List<Map<String, dynamic>>.from(response.data);
    } catch (e) {
      throw DioException(
        requestOptions: RequestOptions(path: '/positions/open'),
        error: 'Failed to get open positions: ${e.toString()}',
      );
    }
  }
  
  Future<List<Map<String, dynamic>>> getTradeHistory({
    int limit = 50,
    String timeframe = 'day'
  }) async {
    try {
      final response = await _dio.get('/trades/history', queryParameters: {
        'limit': limit,
        'timeframe': timeframe
      });
      return List<Map<String, dynamic>>.from(response.data);
    } catch (e) {
      throw DioException(
        requestOptions: RequestOptions(path: '/trades/history'),
        error: 'Failed to get trade history: ${e.toString()}',
      );
    }
  }
  
  // Performance Metrics
  Future<Map<String, dynamic>> getPerformanceMetrics() async {
    try {
      final response = await _dio.get('/performance');
      return response.data;
    } catch (e) {
      throw DioException(
        requestOptions: RequestOptions(path: '/performance'),
        error: 'Failed to get performance metrics: ${e.toString()}',
      );
    }
  }
}
