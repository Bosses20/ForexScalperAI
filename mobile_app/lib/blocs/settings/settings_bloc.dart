import 'package:flutter_bloc/flutter_bloc.dart';
import '../../models/settings/bot_settings.dart';
import '../../services/settings_service.dart';
import 'settings_event.dart';
import 'settings_state.dart';

class SettingsBloc extends Bloc<SettingsEvent, SettingsState> {
  final SettingsService _settingsService;
  
  SettingsBloc({required SettingsService settingsService})
      : _settingsService = settingsService,
        super(const SettingsState()) {
    on<LoadSettings>(_onLoadSettings);
    on<SaveSettings>(_onSaveSettings);
    on<UpdateMT5ConnectionSettings>(_onUpdateMT5ConnectionSettings);
    on<UpdateTradingSettings>(_onUpdateTradingSettings);
    on<UpdateRiskManagementSettings>(_onUpdateRiskManagementSettings);
    on<UpdateStrategySettings>(_onUpdateStrategySettings);
    on<ResetSettings>(_onResetSettings);
    
    // Load settings when bloc is created
    add(const LoadSettings());
  }
  
  Future<void> _onLoadSettings(
    LoadSettings event,
    Emitter<SettingsState> emit,
  ) async {
    emit(state.copyWith(status: SettingsStatus.loading));
    
    try {
      // Try to refresh settings from server first
      final success = await _settingsService.refreshSettings();
      
      if (success) {
        emit(state.copyWith(
          status: SettingsStatus.loaded,
          settings: _settingsService.getSettings(),
        ));
      } else {
        // If server refresh failed, just use cached settings
        emit(state.copyWith(
          status: SettingsStatus.loaded,
          settings: _settingsService.getSettings(),
        ));
      }
    } catch (e) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'Failed to load settings: $e',
      ));
    }
  }
  
  Future<void> _onSaveSettings(
    SaveSettings event,
    Emitter<SettingsState> emit,
  ) async {
    emit(state.copyWith(status: SettingsStatus.saving));
    
    try {
      final success = await _settingsService.updateSettings(event.settings);
      
      if (success) {
        emit(state.copyWith(
          status: SettingsStatus.saved,
          settings: event.settings,
        ));
      } else {
        emit(state.copyWith(
          status: SettingsStatus.error,
          errorMessage: 'Failed to save settings',
        ));
      }
    } catch (e) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'Error saving settings: $e',
      ));
    }
  }
  
  Future<void> _onUpdateMT5ConnectionSettings(
    UpdateMT5ConnectionSettings event,
    Emitter<SettingsState> emit,
  ) async {
    if (state.settings == null) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'No settings loaded',
      ));
      return;
    }
    
    emit(state.copyWith(status: SettingsStatus.saving));
    
    try {
      final updatedSettings = state.settings!.copyWith(
        mt5Connection: event.settings,
      );
      
      final success = await _settingsService.updateSettings(updatedSettings);
      
      if (success) {
        emit(state.copyWith(
          status: SettingsStatus.saved,
          settings: updatedSettings,
        ));
      } else {
        emit(state.copyWith(
          status: SettingsStatus.error,
          errorMessage: 'Failed to update MT5 connection settings',
        ));
      }
    } catch (e) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'Error updating MT5 connection settings: $e',
      ));
    }
  }
  
  Future<void> _onUpdateTradingSettings(
    UpdateTradingSettings event,
    Emitter<SettingsState> emit,
  ) async {
    if (state.settings == null) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'No settings loaded',
      ));
      return;
    }
    
    emit(state.copyWith(status: SettingsStatus.saving));
    
    try {
      final updatedSettings = state.settings!.copyWith(
        trading: event.settings,
      );
      
      final success = await _settingsService.updateSettings(updatedSettings);
      
      if (success) {
        emit(state.copyWith(
          status: SettingsStatus.saved,
          settings: updatedSettings,
        ));
      } else {
        emit(state.copyWith(
          status: SettingsStatus.error,
          errorMessage: 'Failed to update trading settings',
        ));
      }
    } catch (e) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'Error updating trading settings: $e',
      ));
    }
  }
  
  Future<void> _onUpdateRiskManagementSettings(
    UpdateRiskManagementSettings event,
    Emitter<SettingsState> emit,
  ) async {
    if (state.settings == null) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'No settings loaded',
      ));
      return;
    }
    
    emit(state.copyWith(status: SettingsStatus.saving));
    
    try {
      final updatedSettings = state.settings!.copyWith(
        riskManagement: event.settings,
      );
      
      final success = await _settingsService.updateSettings(updatedSettings);
      
      if (success) {
        emit(state.copyWith(
          status: SettingsStatus.saved,
          settings: updatedSettings,
        ));
      } else {
        emit(state.copyWith(
          status: SettingsStatus.error,
          errorMessage: 'Failed to update risk management settings',
        ));
      }
    } catch (e) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'Error updating risk management settings: $e',
      ));
    }
  }
  
  Future<void> _onUpdateStrategySettings(
    UpdateStrategySettings event,
    Emitter<SettingsState> emit,
  ) async {
    if (state.settings == null) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'No settings loaded',
      ));
      return;
    }
    
    emit(state.copyWith(status: SettingsStatus.saving));
    
    try {
      final updatedSettings = state.settings!.copyWith(
        strategies: event.settings,
      );
      
      final success = await _settingsService.updateSettings(updatedSettings);
      
      if (success) {
        emit(state.copyWith(
          status: SettingsStatus.saved,
          settings: updatedSettings,
        ));
      } else {
        emit(state.copyWith(
          status: SettingsStatus.error,
          errorMessage: 'Failed to update strategy settings',
        ));
      }
    } catch (e) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'Error updating strategy settings: $e',
      ));
    }
  }
  
  Future<void> _onResetSettings(
    ResetSettings event,
    Emitter<SettingsState> emit,
  ) async {
    emit(state.copyWith(status: SettingsStatus.loading));
    
    try {
      final success = await _settingsService.resetSettings();
      
      if (success) {
        emit(state.copyWith(
          status: SettingsStatus.loaded,
          settings: _settingsService.getSettings(),
        ));
      } else {
        emit(state.copyWith(
          status: SettingsStatus.error,
          errorMessage: 'Failed to reset settings',
        ));
      }
    } catch (e) {
      emit(state.copyWith(
        status: SettingsStatus.error,
        errorMessage: 'Error resetting settings: $e',
      ));
    }
  }
}
