# Flutter Setup Guide for Mobile Trading App

## Prerequisites
- Flutter SDK (latest stable version)
- Android Studio or VS Code with Flutter plugin
- Dart SDK
- Git for version control

## Project Structure
```
mobile_app/
├── android/                  # Android platform-specific code
├── ios/                      # iOS platform-specific code (if needed)
├── lib/
│   ├── main.dart            # App entry point
│   ├── config/
│   │   ├── app_config.dart  # App configuration
│   │   └── theme.dart       # App theme configuration
│   ├── models/              # Data models
│   │   ├── user_model.dart
│   │   ├── trading_model.dart
│   │   ├── market_model.dart
│   │   └── settings_model.dart
│   ├── services/            # API and services
│   │   ├── api_service.dart # REST API service
│   │   ├── websocket_service.dart # WebSocket service
│   │   ├── auth_service.dart # Authentication service
│   │   └── storage_service.dart # Secure storage
│   ├── blocs/               # Business Logic Components
│   │   ├── auth/
│   │   ├── trading/
│   │   ├── market/
│   │   └── settings/
│   ├── screens/             # UI screens
│   │   ├── auth/
│   │   │   ├── login_screen.dart
│   │   │   └── broker_setup_screen.dart
│   │   ├── dashboard/
│   │   │   ├── dashboard_screen.dart
│   │   │   └── widgets/
│   │   ├── trading/
│   │   │   ├── trading_screen.dart
│   │   │   └── widgets/
│   │   ├── market/
│   │   │   ├── market_screen.dart
│   │   │   └── widgets/
│   │   └── settings/
│   │       ├── settings_screen.dart
│   │       └── widgets/
│   ├── utils/               # Utility functions
│   │   ├── formatters.dart
│   │   ├── validators.dart
│   │   └── connectivity.dart
│   └── widgets/             # Reusable widgets
│       ├── charts/
│       ├── cards/
│       └── dialogs/
├── assets/                  # App assets
│   ├── images/
│   ├── fonts/
│   └── icons/
├── test/                    # Unit and widget tests
└── pubspec.yaml             # Dependencies and metadata
```

## Required Packages
Add the following dependencies to your `pubspec.yaml` file:

```yaml
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.5
  
  # State Management
  flutter_bloc: ^8.1.3
  equatable: ^2.0.5
  
  # Networking
  dio: ^5.3.2  # HTTP client
  web_socket_channel: ^2.4.0  # WebSocket support
  connectivity_plus: ^4.0.2  # Network connectivity
  
  # Storage & Security
  flutter_secure_storage: ^9.0.0  # Secure storage for credentials
  hive: ^2.2.3  # Local database
  hive_flutter: ^1.1.0  # Hive for Flutter
  
  # UI Components
  syncfusion_flutter_charts: ^22.2.12  # Advanced charts
  fl_chart: ^0.63.0  # Lightweight charts
  flutter_svg: ^2.0.7  # SVG support
  shimmer: ^3.0.0  # Loading effects
  cached_network_image: ^3.2.3  # Image caching
  
  # Utilities
  intl: ^0.18.1  # Internationalization
  logger: ^2.0.1  # Logging
  path_provider: ^2.1.1  # File system access
  package_info_plus: ^4.1.0  # App info
  device_info_plus: ^9.0.3  # Device info
  permission_handler: ^10.4.3  # Permission handling
  
  # Optional: Push Notifications
  firebase_messaging: ^14.6.7
  flutter_local_notifications: ^15.1.1
  
dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.2
  bloc_test: ^9.1.3
  mocktail: ^1.0.0
  build_runner: ^2.4.6
  hive_generator: ^2.0.1
```

## Initial Setup Steps

1. **Create new Flutter project:**
   ```bash
   flutter create --org com.yourcompany mobile_trading_app
   cd mobile_trading_app
   ```

2. **Update pubspec.yaml with the dependencies listed above:**
   ```bash
   flutter pub get
   ```

3. **Set up secure storage for credentials:**
   - Configure flutter_secure_storage for Android in `android/app/build.gradle`:
   ```gradle
   android {
       defaultConfig {
           ...
           // Enabling multidex support
           multiDexEnabled true
       }
       ...
   }
   ```

4. **Configure Android permissions in `android/app/src/main/AndroidManifest.xml`:**
   ```xml
   <manifest ...>
       <uses-permission android:name="android.permission.INTERNET" />
       <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
       ...
   </manifest>
   ```

## WebSocket Service Implementation

Create a WebSocket service in `lib/services/websocket_service.dart` to handle real-time data:

```dart
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/io.dart';
import 'package:logger/logger.dart';

enum ConnectionStatus {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error
}

class WebSocketService {
  final Logger _logger = Logger();
  WebSocketChannel? _channel;
  StreamController<Map<String, dynamic>> _dataStreamController = 
      StreamController<Map<String, dynamic>>.broadcast();
  StreamController<ConnectionStatus> _connectionStatusController = 
      StreamController<ConnectionStatus>.broadcast();
  
  String _serverUrl;
  String? _authToken;
  ConnectionStatus _status = ConnectionStatus.disconnected;
  Timer? _reconnectTimer;
  Timer? _pingTimer;
  int _reconnectAttempts = 0;
  final int _maxReconnectAttempts = 5;
  final Duration _reconnectDelay = Duration(seconds: 2);
  
  WebSocketService(this._serverUrl);
  
  Stream<Map<String, dynamic>> get dataStream => _dataStreamController.stream;
  Stream<ConnectionStatus> get connectionStatus => _connectionStatusController.stream;
  ConnectionStatus get status => _status;
  
  void setAuthToken(String token) {
    _authToken = token;
  }
  
  Future<void> connect() async {
    if (_status == ConnectionStatus.connected || 
        _status == ConnectionStatus.connecting) {
      return;
    }
    
    _updateStatus(ConnectionStatus.connecting);
    
    try {
      // Create WebSocket URL with auth token
      String wsUrl = _serverUrl;
      if (_authToken != null) {
        wsUrl += "?token=$_authToken";
      }
      
      _channel = IOWebSocketChannel.connect(wsUrl);
      _logger.i('WebSocket connecting to $wsUrl');
      
      _channel!.stream.listen(
        _onData,
        onError: _onError,
        onDone: _onDone,
      );
      
      _updateStatus(ConnectionStatus.connected);
      _reconnectAttempts = 0;
      _startPingTimer();
      
    } catch (e) {
      _logger.e('WebSocket connection error: $e');
      _updateStatus(ConnectionStatus.error);
      _scheduleReconnect();
    }
  }
  
  void _onData(dynamic data) {
    try {
      final jsonData = jsonDecode(data.toString());
      _dataStreamController.add(jsonData);
    } catch (e) {
      _logger.e('Error parsing WebSocket data: $e');
    }
  }
  
  void _onError(dynamic error) {
    _logger.e('WebSocket error: $error');
    _updateStatus(ConnectionStatus.error);
    _scheduleReconnect();
  }
  
  void _onDone() {
    _logger.w('WebSocket connection closed');
    if (_status != ConnectionStatus.disconnected) {
      _updateStatus(ConnectionStatus.disconnected);
      _scheduleReconnect();
    }
  }
  
  void _scheduleReconnect() {
    if (_reconnectTimer?.isActive ?? false) return;
    
    if (_reconnectAttempts < _maxReconnectAttempts) {
      _reconnectAttempts++;
      _updateStatus(ConnectionStatus.reconnecting);
      
      final delay = Duration(
        milliseconds: (_reconnectDelay.inMilliseconds * _reconnectAttempts).clamp(
          _reconnectDelay.inMilliseconds, 
          30000 // Max 30 seconds
        )
      );
      
      _logger.i('Scheduling reconnect attempt $_reconnectAttempts in ${delay.inSeconds}s');
      _reconnectTimer = Timer(delay, () {
        connect();
      });
    } else {
      _logger.e('Max reconnect attempts reached');
      _updateStatus(ConnectionStatus.error);
    }
  }
  
  void _startPingTimer() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(Duration(seconds: 30), (timer) {
      _sendPing();
    });
  }
  
  void _sendPing() {
    try {
      if (_status == ConnectionStatus.connected) {
        _channel?.sink.add(jsonEncode({'type': 'ping'}));
      }
    } catch (e) {
      _logger.e('Error sending ping: $e');
    }
  }
  
  Future<void> sendMessage(Map<String, dynamic> message) async {
    if (_status != ConnectionStatus.connected) {
      await connect();
    }
    
    try {
      _channel?.sink.add(jsonEncode(message));
    } catch (e) {
      _logger.e('Error sending message: $e');
      throw Exception('Failed to send message: $e');
    }
  }
  
  void _updateStatus(ConnectionStatus newStatus) {
    _status = newStatus;
    _connectionStatusController.add(newStatus);
  }
  
  Future<void> disconnect() async {
    _updateStatus(ConnectionStatus.disconnected);
    _pingTimer?.cancel();
    _reconnectTimer?.cancel();
    await _channel?.sink.close();
    _channel = null;
  }
  
  void dispose() {
    disconnect();
    _dataStreamController.close();
    _connectionStatusController.close();
  }
}
```

## Authentication Service

Create an authentication service in `lib/services/auth_service.dart`:

```dart
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logger/logger.dart';

class AuthService {
  final Dio _dio;
  final FlutterSecureStorage _secureStorage;
  final Logger _logger = Logger();
  
  AuthService(this._dio, this._secureStorage);
  
  Future<String?> getToken() async {
    try {
      return await _secureStorage.read(key: 'auth_token');
    } catch (e) {
      _logger.e('Error getting token: $e');
      return null;
    }
  }
  
  Future<void> saveToken(String token) async {
    await _secureStorage.write(key: 'auth_token', value: token);
  }
  
  Future<void> saveMT5Credentials(String account, String password, String server) async {
    await _secureStorage.write(key: 'mt5_account', value: account);
    await _secureStorage.write(key: 'mt5_password', value: password);
    await _secureStorage.write(key: 'mt5_server', value: server);
  }
  
  Future<Map<String, String?>> getMT5Credentials() async {
    return {
      'account': await _secureStorage.read(key: 'mt5_account'),
      'password': await _secureStorage.read(key: 'mt5_password'),
      'server': await _secureStorage.read(key: 'mt5_server'),
    };
  }
  
  Future<bool> login(String account, String password, String server) async {
    try {
      final response = await _dio.post('/login', data: {
        'account': account,
        'password': password,
        'server': server,
      });
      
      if (response.statusCode == 200) {
        final token = response.data['access_token'];
        await saveToken(token);
        await saveMT5Credentials(account, password, server);
        return true;
      }
      
      return false;
    } catch (e) {
      _logger.e('Login error: $e');
      return false;
    }
  }
  
  Future<void> logout() async {
    await _secureStorage.delete(key: 'auth_token');
  }
  
  Future<bool> isLoggedIn() async {
    final token = await getToken();
    return token != null;
  }
}
```

## API Service Implementation

Create an API service in `lib/services/api_service.dart` to interact with your FastAPI backend:

```dart
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import 'auth_service.dart';

class ApiService {
  final Dio _dio;
  final AuthService _authService;
  final Logger _logger = Logger();
  
  ApiService(this._dio, this._authService) {
    _setupInterceptors();
  }
  
  void _setupInterceptors() {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _authService.getToken();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException e, handler) async {
          if (e.response?.statusCode == 401) {
            // Token expired - could implement token refresh here
            _logger.w('Unauthorized request: ${e.requestOptions.path}');
          }
          return handler.next(e);
        },
      ),
    );
  }
  
  // Bot Status
  Future<Map<String, dynamic>> getBotStatus() async {
    try {
      final response = await _dio.get('/status');
      return response.data;
    } catch (e) {
      _logger.e('Error getting bot status: $e');
      throw Exception('Failed to get bot status');
    }
  }
  
  // Start Bot
  Future<bool> startBot(Map<String, dynamic> config) async {
    try {
      final response = await _dio.post('/start', data: config);
      return response.statusCode == 200;
    } catch (e) {
      _logger.e('Error starting bot: $e');
      throw Exception('Failed to start bot');
    }
  }
  
  // Stop Bot
  Future<bool> stopBot() async {
    try {
      final response = await _dio.post('/stop');
      return response.statusCode == 200;
    } catch (e) {
      _logger.e('Error stopping bot: $e');
      throw Exception('Failed to stop bot');
    }
  }
  
  // Get Trading History
  Future<List<dynamic>> getTradingHistory() async {
    try {
      final response = await _dio.get('/history');
      return response.data;
    } catch (e) {
      _logger.e('Error getting trading history: $e');
      throw Exception('Failed to get trading history');
    }
  }
  
  // Get Market Conditions
  Future<Map<String, dynamic>> getMarketConditions() async {
    try {
      final response = await _dio.get('/market_conditions');
      return response.data;
    } catch (e) {
      _logger.e('Error getting market conditions: $e');
      throw Exception('Failed to get market conditions');
    }
  }
  
  // Update Trading Parameters
  Future<bool> updateTradingParameters(Map<String, dynamic> params) async {
    try {
      final response = await _dio.post('/update_parameters', data: params);
      return response.statusCode == 200;
    } catch (e) {
      _logger.e('Error updating trading parameters: $e');
      throw Exception('Failed to update trading parameters');
    }
  }
}
```

## Service Initialization in main.dart

Here's a basic setup for initializing all services in your `main.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logger/logger.dart';
import 'package:mobile_trading_app/services/auth_service.dart';
import 'package:mobile_trading_app/services/api_service.dart';
import 'package:mobile_trading_app/services/websocket_service.dart';
import 'package:mobile_trading_app/screens/auth/login_screen.dart';
import 'package:mobile_trading_app/screens/dashboard/dashboard_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Setup services
  final dio = Dio(BaseOptions(
    baseUrl: 'http://192.168.1.100:8000', // Replace with your FastAPI server URL
    connectTimeout: Duration(seconds: 5),
    receiveTimeout: Duration(seconds: 10),
    contentType: 'application/json',
  ));
  
  final secureStorage = FlutterSecureStorage();
  final logger = Logger();
  
  final authService = AuthService(dio, secureStorage);
  final apiService = ApiService(dio, authService);
  final wsService = WebSocketService('ws://192.168.1.100:8000/ws'); // Replace with your WebSocket URL
  
  // Check if user is already logged in
  final isLoggedIn = await authService.isLoggedIn();
  if (isLoggedIn) {
    final token = await authService.getToken();
    wsService.setAuthToken(token!);
  }
  
  runApp(MyApp(
    authService: authService,
    apiService: apiService,
    wsService: wsService,
    isLoggedIn: isLoggedIn,
  ));
}

class MyApp extends StatelessWidget {
  final AuthService authService;
  final ApiService apiService;
  final WebSocketService wsService;
  final bool isLoggedIn;
  
  const MyApp({
    Key? key,
    required this.authService,
    required this.apiService,
    required this.wsService,
    required this.isLoggedIn,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Forex Trading Bot',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        brightness: Brightness.dark,
        useMaterial3: true,
      ),
      home: isLoggedIn 
          ? DashboardScreen(apiService: apiService, wsService: wsService)
          : LoginScreen(authService: authService),
    );
  }
}
```
