import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/bot_server.dart';
import '../models/trading_preferences.dart';

class PreferencesService {
  static const String _lastServerKey = 'last_active_server';
  static const String _favoriteServersKey = 'favorite_servers';
  static const String _tradingPreferencesKey = 'trading_preferences';
  static const String _autoReconnectKey = 'auto_reconnect';
  static const String _autoStartTradingKey = 'auto_start_trading';

  // Private constructor for singleton pattern
  PreferencesService._();
  static final PreferencesService _instance = PreferencesService._();

  // Factory constructor to return the singleton instance
  factory PreferencesService() => _instance;

  SharedPreferences? _preferences;

  Future<void> init() async {
    _preferences = await SharedPreferences.getInstance();
  }

  /// Saves the last active server to preferences
  Future<bool> saveLastActiveServer(BotServer server) async {
    if (_preferences == null) await init();
    
    try {
      final serverJson = jsonEncode(server.toJson());
      return await _preferences!.setString(_lastServerKey, serverJson);
    } catch (e) {
      debugPrint('Error saving last active server: $e');
      return false;
    }
  }

  /// Retrieves the last active server from preferences
  Future<BotServer?> getLastActiveServer() async {
    if (_preferences == null) await init();
    
    try {
      final serverJson = _preferences!.getString(_lastServerKey);
      if (serverJson == null) return null;
      
      final serverMap = jsonDecode(serverJson) as Map<String, dynamic>;
      return BotServer.fromJson(serverMap);
    } catch (e) {
      debugPrint('Error retrieving last active server: $e');
      return null;
    }
  }

  /// Saves a list of favorite servers
  Future<bool> saveFavoriteServers(List<BotServer> servers) async {
    if (_preferences == null) await init();
    
    try {
      final serversJson = jsonEncode(
        servers.map((server) => server.toJson()).toList(),
      );
      return await _preferences!.setString(_favoriteServersKey, serversJson);
    } catch (e) {
      debugPrint('Error saving favorite servers: $e');
      return false;
    }
  }

  /// Retrieves the list of favorite servers
  Future<List<BotServer>> getFavoriteServers() async {
    if (_preferences == null) await init();
    
    try {
      final serversJson = _preferences!.getString(_favoriteServersKey);
      if (serversJson == null) return [];
      
      final serversList = jsonDecode(serversJson) as List;
      return serversList
          .map((serverMap) => BotServer.fromJson(serverMap))
          .toList();
    } catch (e) {
      debugPrint('Error retrieving favorite servers: $e');
      return [];
    }
  }

  /// Adds a server to favorites
  Future<bool> addServerToFavorites(BotServer server) async {
    final favorites = await getFavoriteServers();
    
    // Check if server already exists in favorites
    if (favorites.any((s) => s.id == server.id)) {
      return true; // Already a favorite
    }
    
    favorites.add(server);
    return await saveFavoriteServers(favorites);
  }

  /// Removes a server from favorites
  Future<bool> removeServerFromFavorites(String serverId) async {
    final favorites = await getFavoriteServers();
    favorites.removeWhere((server) => server.id == serverId);
    return await saveFavoriteServers(favorites);
  }

  /// Saves trading preferences
  Future<bool> saveTradingPreferences(TradingPreferences preferences) async {
    if (_preferences == null) await init();
    
    try {
      final preferencesJson = jsonEncode(preferences.toJson());
      return await _preferences!.setString(_tradingPreferencesKey, preferencesJson);
    } catch (e) {
      debugPrint('Error saving trading preferences: $e');
      return false;
    }
  }

  /// Retrieves trading preferences
  Future<TradingPreferences> getTradingPreferences() async {
    if (_preferences == null) await init();
    
    try {
      final preferencesJson = _preferences!.getString(_tradingPreferencesKey);
      if (preferencesJson == null) {
        // Return default preferences if none are saved
        return TradingPreferences();
      }
      
      final preferencesMap = jsonDecode(preferencesJson) as Map<String, dynamic>;
      return TradingPreferences.fromJson(preferencesMap);
    } catch (e) {
      debugPrint('Error retrieving trading preferences: $e');
      return TradingPreferences(); // Return default preferences
    }
  }

  /// Get auto-reconnect setting
  Future<bool> getAutoReconnect() async {
    if (_preferences == null) await init();
    return _preferences!.getBool(_autoReconnectKey) ?? true;
  }

  /// Set auto-reconnect setting
  Future<bool> setAutoReconnect(bool value) async {
    if (_preferences == null) await init();
    return await _preferences!.setBool(_autoReconnectKey, value);
  }

  /// Get auto-start trading setting
  Future<bool> getAutoStartTrading() async {
    if (_preferences == null) await init();
    return _preferences!.getBool(_autoStartTradingKey) ?? false;
  }

  /// Set auto-start trading setting
  Future<bool> setAutoStartTrading(bool value) async {
    if (_preferences == null) await init();
    return await _preferences!.setBool(_autoStartTradingKey, value);
  }
}
