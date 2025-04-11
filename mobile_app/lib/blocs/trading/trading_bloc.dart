import 'dart:async';
import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import '../../models/trading_model.dart';
import '../../services/api_service.dart';
import '../../services/websocket_service.dart';
import '../../utils/logger.dart';

// Events
abstract class TradingEvent extends Equatable {
  const TradingEvent();

  @override
  List<Object?> get props => [];
}

class LoadTradingDataEvent extends TradingEvent {}

class BotStatusUpdatedEvent extends TradingEvent {
  final BotStatus botStatus;

  const BotStatusUpdatedEvent(this.botStatus);

  @override
  List<Object?> get props => [botStatus];
}

class StartBotEvent extends TradingEvent {
  final List<String>? instruments;
  final int? riskLevel;
  final String? tradingMode;

  const StartBotEvent({
    this.instruments,
    this.riskLevel,
    this.tradingMode,
  });

  @override
  List<Object?> get props => [instruments, riskLevel, tradingMode];
}

class StopBotEvent extends TradingEvent {}

class LoadOpenPositionsEvent extends TradingEvent {}

class LoadTradeHistoryEvent extends TradingEvent {
  final int limit;
  final DateTime? startDate;
  final DateTime? endDate;

  const LoadTradeHistoryEvent({
    this.limit = 20,
    this.startDate,
    this.endDate,
  });

  @override
  List<Object?> get props => [limit, startDate, endDate];
}

class TradeUpdatedEvent extends TradingEvent {
  final TradePosition trade;

  const TradeUpdatedEvent(this.trade);

  @override
  List<Object?> get props => [trade];
}

class ToggleInstrumentEvent extends TradingEvent {
  final String instrument;
  final bool active;

  const ToggleInstrumentEvent(this.instrument, this.active);

  @override
  List<Object?> get props => [instrument, active];
}

class UpdateTradingEnabledEvent extends TradingEvent {
  final bool enabled;

  const UpdateTradingEnabledEvent(this.enabled);

  @override
  List<Object?> get props => [enabled];
}

class LoadPerformanceEvent extends TradingEvent {}

// States
abstract class TradingState extends Equatable {
  const TradingState();
  
  @override
  List<Object?> get props => [];
}

class TradingInitialState extends TradingState {}

class TradingLoadingState extends TradingState {}

class TradingLoadedState extends TradingState {
  final BotStatus botStatus;
  final List<TradePosition> openPositions;
  final List<TradePosition> recentTrades;
  final TradingPerformance performance;

  const TradingLoadedState({
    required this.botStatus,
    this.openPositions = const [],
    this.recentTrades = const [],
    required this.performance,
  });

  @override
  List<Object?> get props => [botStatus, openPositions, recentTrades, performance];
  
  TradingLoadedState copyWith({
    BotStatus? botStatus,
    List<TradePosition>? openPositions,
    List<TradePosition>? recentTrades,
    TradingPerformance? performance,
  }) {
    return TradingLoadedState(
      botStatus: botStatus ?? this.botStatus,
      openPositions: openPositions ?? this.openPositions,
      recentTrades: recentTrades ?? this.recentTrades,
      performance: performance ?? this.performance,
    );
  }
}

class TradingErrorState extends TradingState {
  final String message;

  const TradingErrorState(this.message);

  @override
  List<Object?> get props => [message];
}

// Bloc
class TradingBloc extends Bloc<TradingEvent, TradingState> {
  final ApiService apiService;
  final WebSocketService wsService;
  final Logger _logger = Logger('TradingBloc');
  StreamSubscription? _botStatusSubscription;
  StreamSubscription? _tradeUpdateSubscription;

  TradingBloc({
    required this.apiService,
    required this.wsService,
  }) : super(TradingInitialState()) {
    on<LoadTradingDataEvent>(_onLoadTradingData);
    on<BotStatusUpdatedEvent>(_onBotStatusUpdated);
    on<StartBotEvent>(_onStartBot);
    on<StopBotEvent>(_onStopBot);
    on<LoadOpenPositionsEvent>(_onLoadOpenPositions);
    on<LoadTradeHistoryEvent>(_onLoadTradeHistory);
    on<TradeUpdatedEvent>(_onTradeUpdated);
    on<ToggleInstrumentEvent>(_onToggleInstrument);
    on<UpdateTradingEnabledEvent>(_onUpdateTradingEnabled);
    on<LoadPerformanceEvent>(_onLoadPerformance);

    // Listen for real-time updates from WebSocket
    _subscribeToWebSocketUpdates();
  }

  Future<void> _onLoadTradingData(
    LoadTradingDataEvent event,
    Emitter<TradingState> emit,
  ) async {
    emit(TradingLoadingState());
    try {
      // Load bot status, open positions, recent trades, and performance
      final botStatus = await apiService.getBotStatus();
      final openPositions = await apiService.getOpenPositions();
      final recentTrades = await apiService.getTradeHistory(limit: 5);
      final performance = await apiService.getPerformance();
      
      emit(TradingLoadedState(
        botStatus: botStatus,
        openPositions: openPositions,
        recentTrades: recentTrades,
        performance: performance,
      ));
      
      _logger.i('Trading data loaded successfully');
    } catch (e) {
      _logger.e('Failed to load trading data: $e');
      emit(TradingErrorState('Failed to load trading data: $e'));
    }
    
    // Also request real-time updates via WebSocket
    wsService.requestBotStatusUpdate();
  }
  
  void _onBotStatusUpdated(
    BotStatusUpdatedEvent event,
    Emitter<TradingState> emit,
  ) {
    if (state is TradingLoadedState) {
      emit((state as TradingLoadedState).copyWith(
        botStatus: event.botStatus,
      ));
      _logger.i('Bot status updated via WebSocket');
    }
  }
  
  Future<void> _onStartBot(
    StartBotEvent event,
    Emitter<TradingState> emit,
  ) async {
    try {
      final success = await apiService.startBot(
        instruments: event.instruments,
        riskLevel: event.riskLevel,
        tradingMode: event.tradingMode,
      );
      
      if (success) {
        // Reload bot status after starting
        add(LoadTradingDataEvent());
        _logger.i('Bot started successfully');
      } else {
        _logger.w('Failed to start bot');
        if (state is TradingLoadedState) {
          // Keep current state but show error
          emit(TradingErrorState('Failed to start the trading bot'));
          emit(state);
        }
      }
    } catch (e) {
      _logger.e('Error starting bot: $e');
      if (state is TradingLoadedState) {
        // Keep current state but show error
        emit(TradingErrorState('Error starting the trading bot: $e'));
        emit(state);
      } else {
        emit(TradingErrorState('Error starting the trading bot: $e'));
      }
    }
  }
  
  Future<void> _onStopBot(
    StopBotEvent event,
    Emitter<TradingState> emit,
  ) async {
    try {
      final success = await apiService.stopBot();
      
      if (success) {
        // Reload bot status after stopping
        add(LoadTradingDataEvent());
        _logger.i('Bot stopped successfully');
      } else {
        _logger.w('Failed to stop bot');
        if (state is TradingLoadedState) {
          // Keep current state but show error
          emit(TradingErrorState('Failed to stop the trading bot'));
          emit(state);
        }
      }
    } catch (e) {
      _logger.e('Error stopping bot: $e');
      if (state is TradingLoadedState) {
        // Keep current state but show error
        emit(TradingErrorState('Error stopping the trading bot: $e'));
        emit(state);
      } else {
        emit(TradingErrorState('Error stopping the trading bot: $e'));
      }
    }
  }
  
  Future<void> _onLoadOpenPositions(
    LoadOpenPositionsEvent event,
    Emitter<TradingState> emit,
  ) async {
    if (state is! TradingLoadedState) {
      // Need to load full trading data first
      add(LoadTradingDataEvent());
      return;
    }
    
    try {
      final openPositions = await apiService.getOpenPositions();
      emit((state as TradingLoadedState).copyWith(
        openPositions: openPositions,
      ));
      _logger.i('Open positions loaded, count: ${openPositions.length}');
    } catch (e) {
      _logger.e('Failed to load open positions: $e');
      // Keep current state but log error
    }
  }
  
  Future<void> _onLoadTradeHistory(
    LoadTradeHistoryEvent event,
    Emitter<TradingState> emit,
  ) async {
    if (state is! TradingLoadedState) {
      // Need to load full trading data first
      add(LoadTradingDataEvent());
      return;
    }
    
    try {
      final trades = await apiService.getTradeHistory(
        limit: event.limit,
        startDate: event.startDate,
        endDate: event.endDate,
      );
      
      emit((state as TradingLoadedState).copyWith(
        recentTrades: trades,
      ));
      _logger.i('Trade history loaded, count: ${trades.length}');
    } catch (e) {
      _logger.e('Failed to load trade history: $e');
      // Keep current state but log error
    }
  }
  
  void _onTradeUpdated(
    TradeUpdatedEvent event,
    Emitter<TradingState> emit,
  ) {
    if (state is! TradingLoadedState) return;
    
    final loadedState = state as TradingLoadedState;
    final trade = event.trade;
    
    // Update open positions or recent trades based on trade status
    if (trade.isOpen) {
      // Update or add to open positions
      final existingIndex = loadedState.openPositions.indexWhere((p) => p.id == trade.id);
      final updatedPositions = List<TradePosition>.from(loadedState.openPositions);
      
      if (existingIndex >= 0) {
        updatedPositions[existingIndex] = trade;
      } else {
        updatedPositions.add(trade);
      }
      
      emit(loadedState.copyWith(openPositions: updatedPositions));
    } else {
      // Closed trade - remove from open positions if present and add to recent trades
      final updatedPositions = loadedState.openPositions.where((p) => p.id != trade.id).toList();
      
      // Add to recent trades if not already present
      final existingTradeIndex = loadedState.recentTrades.indexWhere((t) => t.id == trade.id);
      final updatedTrades = List<TradePosition>.from(loadedState.recentTrades);
      
      if (existingTradeIndex >= 0) {
        updatedTrades[existingTradeIndex] = trade;
      } else {
        // Add to beginning of list and limit to 5 recent trades
        updatedTrades.insert(0, trade);
        if (updatedTrades.length > 5) {
          updatedTrades.removeLast();
        }
      }
      
      emit(loadedState.copyWith(
        openPositions: updatedPositions, 
        recentTrades: updatedTrades
      ));
    }
    
    _logger.i('Trade updated: ${trade.id}, symbol: ${trade.symbol}, isOpen: ${trade.isOpen}');
  }
  
  Future<void> _onToggleInstrument(
    ToggleInstrumentEvent event,
    Emitter<TradingState> emit,
  ) async {
    if (state is! TradingLoadedState) return;
    
    try {
      final success = await apiService.toggleInstrument(event.instrument, event.active);
      
      if (success) {
        // Update the active instruments list in the bot status
        if (state is TradingLoadedState) {
          final loadedState = state as TradingLoadedState;
          final currentInstruments = List<TradingInstrument>.from(loadedState.botStatus.activeInstruments);
          
          // Find and update the instrument in the list
          final index = currentInstruments.indexWhere((i) => i.symbol == event.instrument);
          if (index >= 0) {
            currentInstruments[index] = currentInstruments[index].copyWith(isActive: event.active);
            
            // Update bot status with modified instruments list
            final updatedStatus = loadedState.botStatus.copyWith(
              activeInstruments: currentInstruments,
            );
            
            emit(loadedState.copyWith(botStatus: updatedStatus));
          }
        }
        
        _logger.i('Instrument ${event.instrument} toggled to ${event.active}');
      }
    } catch (e) {
      _logger.e('Failed to toggle instrument: $e');
      // Keep current state but show error
      emit(TradingErrorState('Failed to toggle instrument: $e'));
      emit(state);
    }
  }
  
  Future<void> _onUpdateTradingEnabled(
    UpdateTradingEnabledEvent event,
    Emitter<TradingState> emit,
  ) async {
    if (state is! TradingLoadedState) return;
    
    try {
      final success = await apiService.setTradingEnabled(event.enabled);
      
      if (success) {
        // Update the trading enabled status in the bot status
        if (state is TradingLoadedState) {
          final loadedState = state as TradingLoadedState;
          final updatedStatus = loadedState.botStatus.copyWith(
            isTradingEnabled: event.enabled,
          );
          
          emit(loadedState.copyWith(botStatus: updatedStatus));
        }
        
        _logger.i('Trading enabled set to ${event.enabled}');
      }
    } catch (e) {
      _logger.e('Failed to update trading enabled: $e');
      // Keep current state but show error
      emit(TradingErrorState('Failed to update trading enabled: $e'));
      emit(state);
    }
  }
  
  Future<void> _onLoadPerformance(
    LoadPerformanceEvent event,
    Emitter<TradingState> emit,
  ) async {
    if (state is! TradingLoadedState) {
      // Need to load full trading data first
      add(LoadTradingDataEvent());
      return;
    }
    
    try {
      final performance = await apiService.getPerformance();
      emit((state as TradingLoadedState).copyWith(
        performance: performance,
      ));
      _logger.i('Performance metrics loaded');
    } catch (e) {
      _logger.e('Failed to load performance metrics: $e');
      // Keep current state but log error
    }
  }
  
  void _subscribeToWebSocketUpdates() {
    // Subscribe to bot status updates
    _botStatusSubscription = wsService.tradingStatus.listen(
      (status) {
        add(BotStatusUpdatedEvent(status));
      },
      onError: (error) {
        _logger.e('Error in bot status WebSocket stream: $error');
      },
    );
    
    // Subscribe to trade updates
    _tradeUpdateSubscription = wsService.tradeUpdates.listen(
      (trade) {
        add(TradeUpdatedEvent(trade));
      },
      onError: (error) {
        _logger.e('Error in trade updates WebSocket stream: $error');
      },
    );
  }
  
  @override
  Future<void> close() {
    _botStatusSubscription?.cancel();
    _tradeUpdateSubscription?.cancel();
    return super.close();
  }
}
