import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:multicast_dns/multicast_dns.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/bot_server.dart';
import '../utils/logger.dart';

/// Service responsible for discovering trading bot servers on the local network
class NetworkDiscoveryService {
  static const String _logTag = 'NetworkDiscoveryService';
  static const String _mdnsServiceType = '_forexbot._tcp';
  static const String _cachedServersKey = 'cached_servers';
  static const int _defaultPort = 8000;
  static const int _scanTimeout = 5; // seconds
  static const int _connectionTimeout = 3; // seconds

  final Logger _logger = Logger(_logTag);
  final NetworkInfo _networkInfo = NetworkInfo();
  final Connectivity _connectivity = Connectivity();
  
  // Singleton pattern
  static final NetworkDiscoveryService _instance = NetworkDiscoveryService._internal();
  
  factory NetworkDiscoveryService() {
    return _instance;
  }
  
  NetworkDiscoveryService._internal();

  /// Stream controller for discovered servers
  final StreamController<List<BotServer>> _serversController = 
      StreamController<List<BotServer>>.broadcast();
  
  /// All discovered servers
  List<BotServer> _discoveredServers = [];
  
  /// Stream of discovered servers
  Stream<List<BotServer>> get serversStream => _serversController.stream;
  
  /// Current list of discovered servers
  List<BotServer> get discoveredServers => _discoveredServers;
  
  /// Check if device is connected to WiFi
  Future<bool> isConnectedToWifi() async {
    var connectivityResult = await _connectivity.checkConnectivity();
    return connectivityResult == ConnectivityResult.wifi;
  }
  
  /// Get the device's WiFi IP address
  Future<String?> getWifiIpAddress() async {
    try {
      return await _networkInfo.getWifiIP();
    } catch (e) {
      _logger.e('Failed to get WiFi IP address: $e');
      return null;
    }
  }
  
  /// Scan the local network for trading bot servers using mDNS
  Future<List<BotServer>> scanWithMdns() async {
    _logger.i('Starting mDNS scan for $_mdnsServiceType');
    List<BotServer> servers = [];
    
    try {
      final MDnsClient client = MDnsClient();
      await client.start();
      
      await for (final PtrResourceRecord ptr in client.lookup<PtrResourceRecord>(
        ResourceRecordQuery.serverPointer(_mdnsServiceType),
      ).timeout(Duration(seconds: _scanTimeout))) {
        await for (final SrvResourceRecord srv in client.lookup<SrvResourceRecord>(
          ResourceRecordQuery.service(ptr.domainName),
        ).timeout(Duration(seconds: _scanTimeout))) {
          await for (final TxtResourceRecord txt in client.lookup<TxtResourceRecord>(
            ResourceRecordQuery.text(ptr.domainName),
          ).timeout(Duration(seconds: _scanTimeout))) {
            String? name;
            String? version;
            bool? requiresAuth = true;
            
            for (var item in txt.text.split('\n')) {
              if (item.startsWith('name=')) {
                name = item.substring(5);
              } else if (item.startsWith('version=')) {
                version = item.substring(8);
              } else if (item.startsWith('auth=')) {
                requiresAuth = item.substring(5) == 'true';
              }
            }
            
            final server = BotServer(
              name: name ?? 'Trading Bot Server',
              host: srv.target,
              port: srv.port,
              isDiscovered: true,
              version: version ?? '1.0.0',
              requiresAuth: requiresAuth,
              lastSeen: DateTime.now(),
            );
            
            servers.add(server);
            _logger.i('Found server: ${server.name} at ${server.host}:${server.port}');
          }
        }
      }
      
      await client.stop();
    } catch (e) {
      _logger.e('Error during mDNS scan: $e');
    }
    
    return servers;
  }
  
  /// Scan the local network for trading bot servers by port scanning common IP addresses
  Future<List<BotServer>> scanByIpRange() async {
    _logger.i('Starting IP range scan');
    List<BotServer> servers = [];
    
    try {
      String? wifiIp = await getWifiIpAddress();
      if (wifiIp == null) {
        _logger.w('Cannot scan IP range: WiFi IP not available');
        return servers;
      }
      
      // Parse the current device's IP to determine the subnet
      final ipParts = wifiIp.split('.');
      if (ipParts.length != 4) {
        _logger.w('Invalid IP address format: $wifiIp');
        return servers;
      }
      
      // Build the subnet prefix (first three octets)
      final subnet = '${ipParts[0]}.${ipParts[1]}.${ipParts[2]}';
      
      // Create a list of IP addresses to scan (1-254 in the subnet)
      final ips = List.generate(254, (i) => '$subnet.${i + 1}');
      
      // Concurrent connections pool
      final pool = <Future<BotServer?>>[];
      
      for (var ip in ips) {
        // Skip our own IP
        if (ip == wifiIp) continue;
        
        pool.add(_checkServerAvailability(ip, _defaultPort));
        
        // Process in batches of 10 to prevent overwhelming the network
        if (pool.length >= 10) {
          final results = await Future.wait(pool);
          servers.addAll(results.where((s) => s != null).cast<BotServer>());
          pool.clear();
        }
      }
      
      // Process any remaining IPs
      if (pool.isNotEmpty) {
        final results = await Future.wait(pool);
        servers.addAll(results.where((s) => s != null).cast<BotServer>());
      }
    } catch (e) {
      _logger.e('Error during IP range scan: $e');
    }
    
    return servers;
  }
  
  /// Check if a trading bot server is available at the given IP and port
  Future<BotServer?> _checkServerAvailability(String ip, int port) async {
    try {
      final socket = await Socket.connect(
        ip, 
        port,
        timeout: Duration(seconds: _connectionTimeout),
      );
      
      // If we can connect, try to get server info
      // In a real implementation, you'd send a specific message and parse the response
      socket.write('GET /api/info HTTP/1.1\r\nHost: $ip:$port\r\n\r\n');
      
      final completer = Completer<String>();
      final buffer = StringBuffer();
      
      socket.listen(
        (data) {
          buffer.write(utf8.decode(data));
        },
        onDone: () {
          completer.complete(buffer.toString());
        },
        onError: (e) {
          completer.completeError(e);
        },
        cancelOnError: true,
      );
      
      final response = await completer.future.timeout(
        Duration(seconds: _connectionTimeout),
        onTimeout: () {
          socket.destroy();
          return '';
        },
      );
      
      socket.destroy();
      
      if (response.contains('Forex Trading Bot')) {
        return BotServer(
          name: 'Trading Bot Server',
          host: ip,
          port: port,
          isDiscovered: true,
          version: '1.0.0', // This would be parsed from the response
          requiresAuth: true,
          lastSeen: DateTime.now(),
        );
      }
    } catch (e) {
      // Silently ignore connection errors as most IPs won't have a server running
    }
    return null;
  }
  
  /// Scan the network using available methods and update discovered servers
  Future<List<BotServer>> scanNetwork() async {
    if (!await isConnectedToWifi()) {
      _logger.w('Cannot scan: Not connected to WiFi');
      return [];
    }
    
    _logger.i('Starting network scan');
    
    // Try to discover servers using mDNS first (faster and more reliable)
    List<BotServer> servers = await scanWithMdns();
    
    // If no servers found with mDNS, try IP scanning as fallback
    if (servers.isEmpty) {
      servers = await scanByIpRange();
    }
    
    // Update discovered servers
    if (servers.isNotEmpty) {
      // Merge with existing servers to maintain state
      _updateDiscoveredServers(servers);
      
      // Cache the servers for future use
      _cacheServers(_discoveredServers);
      
      // Notify listeners
      _serversController.add(_discoveredServers);
    }
    
    return _discoveredServers;
  }
  
  /// Update the discovered servers list, merging with existing entries
  void _updateDiscoveredServers(List<BotServer> newServers) {
    // Create a map of existing servers by host:port for quick lookup
    final existingMap = {
      for (var server in _discoveredServers) 
        '${server.host}:${server.port}': server
    };
    
    // Update existing servers and add new ones
    for (var newServer in newServers) {
      final key = '${newServer.host}:${newServer.port}';
      if (existingMap.containsKey(key)) {
        // Update existing server
        final existing = existingMap[key]!;
        existingMap[key] = existing.copyWith(
          name: newServer.name,
          version: newServer.version,
          isDiscovered: true,
          lastSeen: DateTime.now(),
        );
      } else {
        // Add new server
        existingMap[key] = newServer;
      }
    }
    
    // Update the list with merged results
    _discoveredServers = existingMap.values.toList();
    
    // Sort by last seen (most recent first)
    _discoveredServers.sort((a, b) => b.lastSeen.compareTo(a.lastSeen));
  }
  
  /// Add a manually configured server
  Future<void> addManualServer(BotServer server) async {
    // Add to discovered servers
    final existingIndex = _discoveredServers.indexWhere(
      (s) => s.host == server.host && s.port == server.port
    );
    
    if (existingIndex >= 0) {
      _discoveredServers[existingIndex] = server;
    } else {
      _discoveredServers.add(server);
    }
    
    // Cache the updated list
    await _cacheServers(_discoveredServers);
    
    // Notify listeners
    _serversController.add(_discoveredServers);
  }
  
  /// Remove a server from the list
  Future<void> removeServer(BotServer server) async {
    _discoveredServers.removeWhere(
      (s) => s.host == server.host && s.port == server.port
    );
    
    // Cache the updated list
    await _cacheServers(_discoveredServers);
    
    // Notify listeners
    _serversController.add(_discoveredServers);
  }
  
  /// Parse a QR code to extract server connection details
  BotServer? parseQrCode(String qrData) {
    try {
      _logger.i('Parsing QR code: $qrData');
      
      // Expected format: forexbot://{host}:{port}?name={name}&version={version}&auth={requiresAuth}
      if (!qrData.startsWith('forexbot://')) {
        return null;
      }
      
      final uri = Uri.parse(qrData);
      final host = uri.host;
      final port = uri.port > 0 ? uri.port : _defaultPort;
      
      final name = uri.queryParameters['name'] ?? 'Trading Bot Server';
      final version = uri.queryParameters['version'] ?? '1.0.0';
      final requiresAuth = uri.queryParameters['auth'] != 'false'; // Default to true
      
      return BotServer(
        name: name,
        host: host,
        port: port,
        isDiscovered: false, // Manual entry via QR
        version: version,
        requiresAuth: requiresAuth,
        lastSeen: DateTime.now(),
      );
    } catch (e) {
      _logger.e('Error parsing QR code: $e');
      return null;
    }
  }
  
  /// Load cached servers from shared preferences
  Future<List<BotServer>> loadCachedServers() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final serversJson = prefs.getStringList(_cachedServersKey) ?? [];
      
      List<BotServer> servers = [];
      for (var json in serversJson) {
        try {
          final map = jsonDecode(json) as Map<String, dynamic>;
          servers.add(BotServer.fromJson(map));
        } catch (e) {
          _logger.e('Error parsing cached server: $e');
        }
      }
      
      // Update discovered servers
      _discoveredServers = servers;
      
      // Notify listeners
      _serversController.add(_discoveredServers);
      
      return servers;
    } catch (e) {
      _logger.e('Error loading cached servers: $e');
      return [];
    }
  }
  
  /// Cache servers to shared preferences
  Future<void> _cacheServers(List<BotServer> servers) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final serversJson = servers.map((server) => 
        jsonEncode(server.toJson())
      ).toList();
      
      await prefs.setStringList(_cachedServersKey, serversJson);
    } catch (e) {
      _logger.e('Error caching servers: $e');
    }
  }
  
  /// Dispose resources
  void dispose() {
    _serversController.close();
  }
}
