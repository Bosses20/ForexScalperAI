import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logging/logging.dart';
import '../models/settings/bot_settings.dart';
import 'api_service.dart';

/// Service for managing bot settings
class SettingsService {
  final _logger = Logger('SettingsService');
  final FlutterSecureStorage _secureStorage;
  final ApiService _apiService;
  
  // Storage key
  static const String _settingsKey = 'bot_settings';
  
  // Current settings
  BotSettings? _cachedSettings;
  
  // Stream controller for settings changes
  final _settingsController = StreamController<BotSettings>.broadcast();
  
  /// Stream of settings changes
  Stream<BotSettings> get settingsStream => _settingsController.stream;
  
  SettingsService({
    required ApiService apiService,
    FlutterSecureStorage? secureStorage,
  }) : _apiService = apiService,
       _secureStorage = secureStorage ?? const FlutterSecureStorage();
       
  /// Initialize the settings service
  Future<void> initialize() async {
    try {
      // Try to load settings from local storage first
      await _loadLocalSettings();
      
      // Try to get the latest settings from the server
      await refreshSettings();
    } catch (e) {
      _logger.severe('Error initializing settings: $e');
      // If we can't load settings, create default ones
      if (_cachedSettings == null) {
        _cachedSettings = BotSettings.defaults();
        _settingsController.add(_cachedSettings!);
      }
    }
  }
  
  /// Get the current settings
  BotSettings getSettings() {
    if (_cachedSettings == null) {
      _cachedSettings = BotSettings.defaults();
    }
    return _cachedSettings!;
  }
  
  /// Update settings
  Future<bool> updateSettings(BotSettings settings) async {
    try {
      // Update settings on the server
      final success = await _apiService.updateSettings(settings.toJson());
      
      if (success) {
        // Update local cache
        _cachedSettings = settings;
        _settingsController.add(_cachedSettings!);
        
        // Save to secure storage
        await _saveLocalSettings();
        
        _logger.info('Settings updated successfully');
        return true;
      } else {
        _logger.warning('Failed to update settings on server');
        return false;
      }
    } catch (e) {
      _logger.severe('Error updating settings: $e');
      return false;
    }
  }
  
  /// Refresh settings from the server
  Future<bool> refreshSettings() async {
    try {
      _logger.info('Refreshing settings from server');
      
      // Get settings from server
      final settingsJson = await _apiService.getSettings();
      
      if (settingsJson != null) {
        // Update cached settings
        _cachedSettings = BotSettings.fromJson(settingsJson);
        _settingsController.add(_cachedSettings!);
        
        // Save to local storage
        await _saveLocalSettings();
        
        _logger.info('Settings refreshed successfully');
        return true;
      } else {
        _logger.warning('Failed to get settings from server');
        return false;
      }
    } catch (e) {
      _logger.severe('Error refreshing settings: $e');
      return false;
    }
  }
  
  /// Reset settings to defaults
  Future<bool> resetSettings() async {
    try {
      // Create default settings
      final defaultSettings = BotSettings.defaults();
      
      // Try to update on server
      final success = await _apiService.updateSettings(defaultSettings.toJson());
      
      if (success) {
        // Update local cache
        _cachedSettings = defaultSettings;
        _settingsController.add(_cachedSettings!);
        
        // Save to secure storage
        await _saveLocalSettings();
        
        _logger.info('Settings reset to defaults');
        return true;
      } else {
        _logger.warning('Failed to reset settings on server');
        return false;
      }
    } catch (e) {
      _logger.severe('Error resetting settings: $e');
      return false;
    }
  }
  
  /// Load settings from local storage
  Future<void> _loadLocalSettings() async {
    try {
      final settingsJson = await _secureStorage.read(key: _settingsKey);
      
      if (settingsJson != null) {
        _cachedSettings = BotSettings.deserialize(settingsJson);
        _settingsController.add(_cachedSettings!);
        _logger.info('Settings loaded from local storage');
      } else {
        _logger.info('No settings found in local storage');
        _cachedSettings = BotSettings.defaults();
        _settingsController.add(_cachedSettings!);
      }
    } catch (e) {
      _logger.severe('Error loading settings from local storage: $e');
      _cachedSettings = BotSettings.defaults();
      _settingsController.add(_cachedSettings!);
    }
  }
  
  /// Save settings to local storage
  Future<void> _saveLocalSettings() async {
    try {
      if (_cachedSettings != null) {
        await _secureStorage.write(
          key: _settingsKey,
          value: _cachedSettings!.serialize(),
        );
        _logger.info('Settings saved to local storage');
      }
    } catch (e) {
      _logger.severe('Error saving settings to local storage: $e');
    }
  }
  
  /// Update specific MT5 connection settings
  Future<bool> updateMT5ConnectionSettings(MT5ConnectionSettings settings) async {
    if (_cachedSettings == null) {
      await _loadLocalSettings();
    }
    
    final updatedSettings = _cachedSettings!.copyWith(
      mt5Connection: settings,
    );
    
    return await updateSettings(updatedSettings);
  }
  
  /// Update trading settings
  Future<bool> updateTradingSettings(TradingSettings settings) async {
    if (_cachedSettings == null) {
      await _loadLocalSettings();
    }
    
    final updatedSettings = _cachedSettings!.copyWith(
      trading: settings,
    );
    
    return await updateSettings(updatedSettings);
  }
  
  /// Update risk management settings
  Future<bool> updateRiskManagementSettings(RiskManagementSettings settings) async {
    if (_cachedSettings == null) {
      await _loadLocalSettings();
    }
    
    final updatedSettings = _cachedSettings!.copyWith(
      riskManagement: settings,
    );
    
    return await updateSettings(updatedSettings);
  }
  
  /// Update strategy settings
  Future<bool> updateStrategySettings(StrategySettings settings) async {
    if (_cachedSettings == null) {
      await _loadLocalSettings();
    }
    
    final updatedSettings = _cachedSettings!.copyWith(
      strategies: settings,
    );
    
    return await updateSettings(updatedSettings);
  }
  
  /// Dispose resources
  void dispose() {
    _settingsController.close();
  }
}
