import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'blocs/auth/auth_bloc.dart';
import 'blocs/trading/trading_bloc.dart';
import 'blocs/network_discovery/network_discovery_bloc.dart';
import 'screens/auth/login_screen.dart';
import 'screens/dashboard/dashboard_screen.dart';
import 'services/api_service.dart';
import 'services/network_discovery_service.dart';
import 'services/session_service.dart';
import 'services/websocket_service.dart';
import 'theme/app_theme.dart';
import 'package:logging/logging.dart';

void main() {
  // Configure logging
  Logger.root.level = Level.ALL;
  Logger.root.onRecord.listen((record) {
    // ignore: avoid_print
    print('${record.level.name}: ${record.time}: ${record.message}');
  });
  
  // Set up error handling
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    Logger('FlutterError').severe('Flutter error: ${details.exception}', details.exception, details.stack);
  };

  runApp(const ForexTradingApp());
}

class ForexTradingApp extends StatefulWidget {
  const ForexTradingApp({Key? key}) : super(key: key);

  @override
  State<ForexTradingApp> createState() => _ForexTradingAppState();
}

class _ForexTradingAppState extends State<ForexTradingApp> {
  // Services
  final _apiService = ApiService();
  final _websocketService = WebSocketService();
  final _secureStorage = const FlutterSecureStorage();
  final _networkDiscoveryService = NetworkDiscoveryService();
  late final SessionService _sessionService;
  
  // Blocs
  late final AuthBloc _authBloc;
  late final TradingBloc _tradingBloc;
  late final NetworkDiscoveryBloc _networkDiscoveryBloc;

  @override
  void initState() {
    super.initState();
    
    // Initialize services
    _sessionService = SessionService(
      apiService: _apiService,
      secureStorage: _secureStorage,
    );
    
    // Initialize blocs
    _authBloc = AuthBloc(
      apiService: _apiService,
      wsService: _websocketService,
      sessionService: _sessionService,
      secureStorage: _secureStorage,
    );
    
    _tradingBloc = TradingBloc(
      apiService: _apiService,
      wsService: _websocketService,
    );
    
    _networkDiscoveryBloc = NetworkDiscoveryBloc(
      discoveryService: _networkDiscoveryService,
    );
    
    // Start the app authentication flow
    _authBloc.add(AppStartedEvent());
    
    // Load cached servers when app starts
    _networkDiscoveryBloc.add(LoadCachedServersEvent());
  }

  @override
  void dispose() {
    // Close blocs
    _authBloc.close();
    _tradingBloc.close();
    _networkDiscoveryBloc.close();
    
    // Dispose services
    _sessionService.dispose();
    
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        BlocProvider<AuthBloc>.value(value: _authBloc),
        BlocProvider<TradingBloc>.value(value: _tradingBloc),
        BlocProvider<NetworkDiscoveryBloc>.value(value: _networkDiscoveryBloc),
      ],
      child: MaterialApp(
        title: 'Forex Trading Bot',
        theme: AppTheme.lightTheme,
        darkTheme: AppTheme.darkTheme,
        themeMode: ThemeMode.system,
        debugShowCheckedModeBanner: false,
        home: BlocBuilder<AuthBloc, AuthState>(
          builder: (context, state) {
            if (state is AuthLoadingState) {
              return _buildLoadingScreen();
            } else if (state is AuthenticatedState) {
              return const DashboardScreen();
            } else if (state is ServerConnectedState) {
              return const LoginScreen();
            } else {
              return const LoginScreen();
            }
          },
        ),
      ),
    );
  }

  Widget _buildLoadingScreen() {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading...'),
          ],
        ),
      ),
    );
  }
}
