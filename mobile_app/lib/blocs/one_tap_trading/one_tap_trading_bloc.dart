import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';

import '../../models/market/market_condition.dart';
import '../../models/bot_server.dart';
import '../../models/bot_status.dart';
import '../../services/connection_manager.dart';
import '../../services/trading_bot_service.dart';
import '../../services/market_data_service.dart';

// Events
abstract class OneTapTradingEvent extends Equatable {
  const OneTapTradingEvent();

  @override
  List<Object?> get props => [];
}

class OneTapTradingStarted extends OneTapTradingEvent {
  final BotServer server;

  const OneTapTradingStarted(this.server);

  @override
  List<Object?> get props => [server];
}

class OneTapTradingStopped extends OneTapTradingEvent {}

class OneTapTradingMarketAnalysisRequested extends OneTapTradingEvent {
  final String symbol;

  const OneTapTradingMarketAnalysisRequested(this.symbol);

  @override
  List<Object?> get props => [symbol];
}

class OneTapTradingConnectionChanged extends OneTapTradingEvent {
  final ConnectionStatus connectionStatus;

  const OneTapTradingConnectionChanged(this.connectionStatus);

  @override
  List<Object?> get props => [connectionStatus];
}

class OneTapTradingBotStatusChanged extends OneTapTradingEvent {
  final BotStatus status;

  const OneTapTradingBotStatusChanged(this.status);

  @override
  List<Object?> get props => [status];
}

class OneTapTradingMarketConditionChanged extends OneTapTradingEvent {
  final MarketCondition condition;

  const OneTapTradingMarketConditionChanged(this.condition);

  @override
  List<Object?> get props => [condition];
}

class OneTapTradingRetryConnection extends OneTapTradingEvent {
  final BotServer server;

  const OneTapTradingRetryConnection(this.server);

  @override
  List<Object?> get props => [server];
}

class OneTapTradingClearError extends OneTapTradingEvent {}

// States
enum OneTapTradingStatus {
  initial,
  connecting,
  connected,
  analyzing,
  readyToTrade,
  trading,
  stopping,
  stopped,
  error,
}

class OneTapTradingState extends Equatable {
  final OneTapTradingStatus status;
  final BotServer? server;
  final MarketCondition? marketCondition;
  final BotStatus? botStatus;
  final ConnectionStatus? connectionStatus;
  final String? errorMessage;
  final bool hasConnectionError;
  final bool hasMarketError;
  final bool hasBotError;

  const OneTapTradingState({
    this.status = OneTapTradingStatus.initial,
    this.server,
    this.marketCondition,
    this.botStatus,
    this.connectionStatus,
    this.errorMessage,
    this.hasConnectionError = false,
    this.hasMarketError = false,
    this.hasBotError = false,
  });

  bool get isConnected => 
      connectionStatus?.isConnected ?? false;

  bool get isTrading => 
      status == OneTapTradingStatus.trading;

  bool get isAnalyzing => 
      status == OneTapTradingStatus.analyzing;

  bool get isFavorableForTrading => 
      marketCondition?.isFavorableForTrading ?? false;

  bool get hasError => 
      hasConnectionError || hasMarketError || hasBotError;

  OneTapTradingState copyWith({
    OneTapTradingStatus? status,
    BotServer? server,
    MarketCondition? marketCondition,
    BotStatus? botStatus,
    ConnectionStatus? connectionStatus,
    String? errorMessage,
    bool? hasConnectionError,
    bool? hasMarketError,
    bool? hasBotError,
  }) {
    return OneTapTradingState(
      status: status ?? this.status,
      server: server ?? this.server,
      marketCondition: marketCondition ?? this.marketCondition,
      botStatus: botStatus ?? this.botStatus,
      connectionStatus: connectionStatus ?? this.connectionStatus,
      errorMessage: errorMessage ?? this.errorMessage,
      hasConnectionError: hasConnectionError ?? this.hasConnectionError,
      hasMarketError: hasMarketError ?? this.hasMarketError,
      hasBotError: hasBotError ?? this.hasBotError,
    );
  }

  @override
  List<Object?> get props => [
        status,
        server,
        marketCondition,
        botStatus,
        connectionStatus,
        errorMessage,
        hasConnectionError,
        hasMarketError,
        hasBotError,
      ];
}

class OneTapTradingBloc extends Bloc<OneTapTradingEvent, OneTapTradingState> {
  final ConnectionManager connectionManager;
  final TradingBotService tradingBotService;
  final MarketDataService marketDataService;
  
  late StreamSubscription<ConnectionStatus> _connectionSubscription;
  late StreamSubscription<BotStatus> _botStatusSubscription;
  
  OneTapTradingBloc({
    required this.connectionManager,
    required this.tradingBotService,
    required this.marketDataService,
  }) : super(const OneTapTradingState()) {
    on<OneTapTradingStarted>(_onStarted);
    on<OneTapTradingStopped>(_onStopped);
    on<OneTapTradingMarketAnalysisRequested>(_onMarketAnalysisRequested);
    on<OneTapTradingConnectionChanged>(_onConnectionChanged);
    on<OneTapTradingBotStatusChanged>(_onBotStatusChanged);
    on<OneTapTradingMarketConditionChanged>(_onMarketConditionChanged);
    on<OneTapTradingRetryConnection>(_onRetryConnection);
    on<OneTapTradingClearError>(_onClearError);
    
    _connectionSubscription = connectionManager.connectionStatus.listen((status) {
      add(OneTapTradingConnectionChanged(status));
    });
    
    _botStatusSubscription = tradingBotService.botStatus.listen((status) {
      add(OneTapTradingBotStatusChanged(status));
    });
  }

  Future<void> _onStarted(
    OneTapTradingStarted event,
    Emitter<OneTapTradingState> emit,
  ) async {
    try {
      // Step 1: Update state to connecting
      emit(state.copyWith(
        status: OneTapTradingStatus.connecting,
        server: event.server,
        hasConnectionError: false,
        hasMarketError: false,
        hasBotError: false,
        errorMessage: null,
      ));
      
      // Step 2: Connect to the server if needed
      if (!connectionManager.isConnected || 
          connectionManager.activeServer?.id != event.server.id) {
        final connected = await connectionManager.connectToServer(event.server);
        if (!connected) {
          emit(state.copyWith(
            status: OneTapTradingStatus.error,
            hasConnectionError: true,
            errorMessage: 'Failed to connect to server: ${event.server.name}',
          ));
          return;
        }
      }
      
      // Step 3: Analyze market conditions
      emit(state.copyWith(
        status: OneTapTradingStatus.analyzing,
      ));
      
      // Request market analysis for default symbols
      // This will trigger an OneTapTradingMarketAnalysisRequested event
      // which will be handled separately
      add(const OneTapTradingMarketAnalysisRequested('EURUSD'));
      
    } catch (e) {
      debugPrint('Error starting one-tap trading: $e');
      emit(state.copyWith(
        status: OneTapTradingStatus.error,
        errorMessage: 'Error starting trading: $e',
      ));
    }
  }

  Future<void> _onStopped(
    OneTapTradingStopped event,
    Emitter<OneTapTradingState> emit,
  ) async {
    try {
      if (state.isTrading) {
        emit(state.copyWith(
          status: OneTapTradingStatus.stopping,
        ));
        
        await tradingBotService.stopTrading();
        
        emit(state.copyWith(
          status: OneTapTradingStatus.stopped,
        ));
      }
    } catch (e) {
      debugPrint('Error stopping one-tap trading: $e');
      emit(state.copyWith(
        status: OneTapTradingStatus.error,
        errorMessage: 'Error stopping trading: $e',
        hasBotError: true,
      ));
    }
  }

  Future<void> _onMarketAnalysisRequested(
    OneTapTradingMarketAnalysisRequested event,
    Emitter<OneTapTradingState> emit,
  ) async {
    try {
      final currentCondition = await marketDataService.getMarketCondition(event.symbol);
      
      add(OneTapTradingMarketConditionChanged(currentCondition));
      
    } catch (e) {
      debugPrint('Error analyzing market: $e');
      emit(state.copyWith(
        status: OneTapTradingStatus.error,
        errorMessage: 'Error analyzing market conditions: $e',
        hasMarketError: true,
      ));
    }
  }

  void _onConnectionChanged(
    OneTapTradingConnectionChanged event,
    Emitter<OneTapTradingState> emit,
  ) {
    final connectionStatus = event.connectionStatus;
    
    switch (connectionStatus.state) {
      case ConnectionState.connected:
        emit(state.copyWith(
          connectionStatus: connectionStatus,
          hasConnectionError: false,
          status: state.status == OneTapTradingStatus.connecting ? 
              OneTapTradingStatus.analyzing : state.status,
        ));
        break;
        
      case ConnectionState.connecting:
      case ConnectionState.reconnecting:
        emit(state.copyWith(
          connectionStatus: connectionStatus,
          status: OneTapTradingStatus.connecting,
        ));
        break;
        
      case ConnectionState.error:
        emit(state.copyWith(
          connectionStatus: connectionStatus,
          hasConnectionError: true,
          errorMessage: connectionStatus.message,
          status: OneTapTradingStatus.error,
        ));
        break;
        
      case ConnectionState.disconnected:
        if (state.isTrading) {
          // If we were trading, stop the bot
          add(OneTapTradingStopped());
        }
        
        emit(state.copyWith(
          connectionStatus: connectionStatus,
          status: OneTapTradingStatus.stopped,
        ));
        break;
        
      default:
        emit(state.copyWith(
          connectionStatus: connectionStatus,
        ));
        break;
    }
  }

  void _onBotStatusChanged(
    OneTapTradingBotStatusChanged event,
    Emitter<OneTapTradingState> emit,
  ) {
    final botStatus = event.status;
    
    switch (botStatus.state) {
      case BotState.trading:
        emit(state.copyWith(
          botStatus: botStatus,
          status: OneTapTradingStatus.trading,
          hasBotError: false,
        ));
        break;
        
      case BotState.stopping:
        emit(state.copyWith(
          botStatus: botStatus,
          status: OneTapTradingStatus.stopping,
        ));
        break;
        
      case BotState.stopped:
        emit(state.copyWith(
          botStatus: botStatus,
          status: OneTapTradingStatus.stopped,
        ));
        break;
        
      case BotState.error:
        emit(state.copyWith(
          botStatus: botStatus,
          hasBotError: true,
          errorMessage: botStatus.message,
          status: OneTapTradingStatus.error,
        ));
        break;
        
      default:
        emit(state.copyWith(
          botStatus: botStatus,
        ));
        break;
    }
  }

  void _onMarketConditionChanged(
    OneTapTradingMarketConditionChanged event,
    Emitter<OneTapTradingState> emit,
  ) async {
    final marketCondition = event.condition;
    
    // Update the state with new market condition
    emit(state.copyWith(
      marketCondition: marketCondition,
      status: OneTapTradingStatus.readyToTrade,
      hasMarketError: false,
    ));
    
    // If the bot was already trading and market conditions become unfavorable,
    // we might want to stop trading
    if (state.isTrading && !marketCondition.isFavorableForTrading) {
      // This could be controlled by a user preference
      // For now, we'll just log a warning
      debugPrint('WARNING: Market conditions have become unfavorable while trading');
    }
    
    // If auto-trading is enabled (could be a user preference),
    // start trading immediately if conditions are favorable
    if (state.isConnected && 
        !state.isTrading && 
        marketCondition.isFavorableForTrading &&
        state.status == OneTapTradingStatus.readyToTrade) {
      
      try {
        // Start trading with the current server and market conditions
        final success = await tradingBotService.startTrading(
          server: state.server!,
          marketCondition: marketCondition,
        );
        
        if (!success) {
          emit(state.copyWith(
            status: OneTapTradingStatus.error,
            hasBotError: true,
            errorMessage: 'Failed to start trading bot',
          ));
        }
      } catch (e) {
        debugPrint('Error auto-starting trading: $e');
        emit(state.copyWith(
          status: OneTapTradingStatus.error,
          hasBotError: true,
          errorMessage: 'Error auto-starting trading: $e',
        ));
      }
    }
  }

  Future<void> _onRetryConnection(
    OneTapTradingRetryConnection event,
    Emitter<OneTapTradingState> emit,
  ) async {
    emit(state.copyWith(
      status: OneTapTradingStatus.connecting,
      hasConnectionError: false,
      errorMessage: null,
    ));
    
    try {
      final connected = await connectionManager.connectToServer(event.server);
      if (!connected) {
        emit(state.copyWith(
          status: OneTapTradingStatus.error,
          hasConnectionError: true,
          errorMessage: 'Failed to connect to server: ${event.server.name}',
        ));
      }
    } catch (e) {
      debugPrint('Error retrying connection: $e');
      emit(state.copyWith(
        status: OneTapTradingStatus.error,
        hasConnectionError: true,
        errorMessage: 'Error retrying connection: $e',
      ));
    }
  }

  void _onClearError(
    OneTapTradingClearError event,
    Emitter<OneTapTradingState> emit,
  ) {
    emit(state.copyWith(
      hasConnectionError: false,
      hasMarketError: false,
      hasBotError: false,
      errorMessage: null,
      status: state.isConnected ? OneTapTradingStatus.readyToTrade : OneTapTradingStatus.initial,
    ));
  }

  @override
  Future<void> close() {
    _connectionSubscription.cancel();
    _botStatusSubscription.cancel();
    return super.close();
  }
}
