import 'dart:async';
import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import '../../models/market_model.dart';
import '../../services/api_service.dart';
import '../../services/websocket_service.dart';
import '../../utils/logger.dart';

// Events
abstract class MarketEvent extends Equatable {
  const MarketEvent();

  @override
  List<Object> get props => [];
}

class LoadMarketConditionsEvent extends MarketEvent {}

class MarketConditionsUpdatedEvent extends MarketEvent {
  final MarketCondition marketCondition;

  const MarketConditionsUpdatedEvent(this.marketCondition);

  @override
  List<Object> get props => [marketCondition];
}

class LoadCorrelationMatrixEvent extends MarketEvent {}

class CorrelationMatrixUpdatedEvent extends MarketEvent {
  final MarketCorrelation correlation;

  const CorrelationMatrixUpdatedEvent(this.correlation);

  @override
  List<Object> get props => [correlation];
}

// States
abstract class MarketState extends Equatable {
  const MarketState();
  
  @override
  List<Object?> get props => [];
}

class MarketInitialState extends MarketState {}

class MarketLoadingState extends MarketState {}

class MarketLoadedState extends MarketState {
  final MarketCondition marketCondition;
  final MarketCorrelation? correlationMatrix;

  const MarketLoadedState({
    required this.marketCondition,
    this.correlationMatrix,
  });

  @override
  List<Object?> get props => [marketCondition, correlationMatrix];
  
  MarketLoadedState copyWith({
    MarketCondition? marketCondition,
    MarketCorrelation? correlationMatrix,
  }) {
    return MarketLoadedState(
      marketCondition: marketCondition ?? this.marketCondition,
      correlationMatrix: correlationMatrix ?? this.correlationMatrix,
    );
  }
}

class MarketErrorState extends MarketState {
  final String message;

  const MarketErrorState(this.message);

  @override
  List<Object> get props => [message];
}

// Bloc
class MarketBloc extends Bloc<MarketEvent, MarketState> {
  final ApiService apiService;
  final WebSocketService wsService;
  final Logger _logger = Logger('MarketBloc');
  StreamSubscription? _marketConditionSubscription;

  MarketBloc({
    required this.apiService,
    required this.wsService,
  }) : super(MarketInitialState()) {
    on<LoadMarketConditionsEvent>(_onLoadMarketConditions);
    on<MarketConditionsUpdatedEvent>(_onMarketConditionsUpdated);
    on<LoadCorrelationMatrixEvent>(_onLoadCorrelationMatrix);
    on<CorrelationMatrixUpdatedEvent>(_onCorrelationMatrixUpdated);

    // Listen for real-time market condition updates from WebSocket
    _subscribeToMarketUpdates();
  }

  Future<void> _onLoadMarketConditions(
    LoadMarketConditionsEvent event,
    Emitter<MarketState> emit,
  ) async {
    emit(MarketLoadingState());
    try {
      final marketCondition = await apiService.getMarketConditions();
      if (state is MarketLoadedState) {
        emit((state as MarketLoadedState).copyWith(
          marketCondition: marketCondition,
        ));
      } else {
        emit(MarketLoadedState(marketCondition: marketCondition));
      }
      _logger.i('Market conditions loaded successfully');
    } catch (e) {
      _logger.e('Failed to load market conditions: $e');
      emit(MarketErrorState('Failed to load market conditions: $e'));
    }
    
    // Also request real-time updates via WebSocket
    wsService.requestMarketConditionUpdate();
  }

  void _onMarketConditionsUpdated(
    MarketConditionsUpdatedEvent event,
    Emitter<MarketState> emit,
  ) {
    if (state is MarketLoadedState) {
      emit((state as MarketLoadedState).copyWith(
        marketCondition: event.marketCondition,
      ));
    } else {
      emit(MarketLoadedState(marketCondition: event.marketCondition));
    }
    _logger.i('Market conditions updated via WebSocket');
  }

  Future<void> _onLoadCorrelationMatrix(
    LoadCorrelationMatrixEvent event,
    Emitter<MarketState> emit,
  ) async {
    try {
      final correlationMatrix = await apiService.getCorrelationMatrix();
      if (state is MarketLoadedState) {
        emit((state as MarketLoadedState).copyWith(
          correlationMatrix: correlationMatrix,
        ));
      } else {
        // Need market conditions to be loaded first
        final marketCondition = await apiService.getMarketConditions();
        emit(MarketLoadedState(
          marketCondition: marketCondition,
          correlationMatrix: correlationMatrix,
        ));
      }
      _logger.i('Correlation matrix loaded successfully');
    } catch (e) {
      _logger.e('Failed to load correlation matrix: $e');
      // Only set error state if we don't already have market conditions loaded
      if (!(state is MarketLoadedState)) {
        emit(MarketErrorState('Failed to load correlation matrix: $e'));
      }
    }
  }

  void _onCorrelationMatrixUpdated(
    CorrelationMatrixUpdatedEvent event,
    Emitter<MarketState> emit,
  ) {
    if (state is MarketLoadedState) {
      emit((state as MarketLoadedState).copyWith(
        correlationMatrix: event.correlation,
      ));
    }
    _logger.i('Correlation matrix updated');
  }

  void _subscribeToMarketUpdates() {
    _marketConditionSubscription = wsService.marketConditions.listen(
      (marketCondition) {
        add(MarketConditionsUpdatedEvent(marketCondition));
      },
      onError: (error) {
        _logger.e('Error in market condition WebSocket stream: $error');
      },
    );
  }

  @override
  Future<void> close() {
    _marketConditionSubscription?.cancel();
    return super.close();
  }
}
