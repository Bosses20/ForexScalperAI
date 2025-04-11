import 'dart:async';
import 'dart:io';

import 'package:flutter_upnp/flutter_upnp.dart';
import '../utils/logger.dart';

/// Service for handling UPnP port forwarding to make the bot accessible
/// across different networks
class UpnpService {
  static const String _logTag = 'UpnpService';
  static const String _serviceDescription = 'Forex Trading Bot';
  static const int _leaseDuration = 0; // 0 means indefinite

  final Logger _logger = Logger(_logTag);
  final FlutterUpnp _upnp = FlutterUpnp();
  
  // Singleton pattern
  static final UpnpService _instance = UpnpService._internal();
  
  factory UpnpService() {
    return _instance;
  }
  
  UpnpService._internal();
  
  // Track opened ports for cleanup
  final Map<int, String> _forwardedPorts = {};
  
  /// Initialize the UPnP service
  Future<bool> initialize() async {
    try {
      final result = await _upnp.initialize();
      if (result) {
        _logger.i('UPnP service initialized successfully');
      } else {
        _logger.w('Failed to initialize UPnP service');
      }
      return result;
    } catch (e) {
      _logger.e('Error initializing UPnP service: $e');
      return false;
    }
  }

  /// Check if UPnP is available on the network
  Future<bool> isAvailable() async {
    try {
      return await _upnp.isAvailable();
    } catch (e) {
      _logger.e('Error checking UPnP availability: $e');
      return false;
    }
  }

  /// Get the external IP address of the router
  Future<String?> getExternalIpAddress() async {
    try {
      return await _upnp.getExternalIpAddress();
    } catch (e) {
      _logger.e('Error getting external IP address: $e');
      return null;
    }
  }

  /// Set up port forwarding to make internal services accessible externally
  Future<bool> addPortMapping({
    required int externalPort, 
    required int internalPort,
    required String protocol, // 'TCP' or 'UDP'
    String? description,
  }) async {
    try {
      if (!await isAvailable()) {
        _logger.w('UPnP is not available on this network');
        return false;
      }

      // Get local IP address
      final interfaces = await NetworkInterface.list(
        includeLinkLocal: false,
        type: InternetAddressType.IPv4,
      );
      
      if (interfaces.isEmpty) {
        _logger.e('No network interfaces found');
        return false;
      }
      
      // Find the first non-loopback IPv4 address
      final localIp = interfaces
          .expand((interface) => interface.addresses)
          .firstWhere(
            (addr) => !addr.isLoopback,
            orElse: () => interfaces.first.addresses.first,
          )
          .address;
      
      _logger.i('Adding port mapping: $externalPort -> $localIp:$internalPort ($protocol)');
      
      final result = await _upnp.addPortMapping(
        externalPort: externalPort,
        internalPort: internalPort,
        internalClient: localIp,
        protocol: protocol,
        description: description ?? '$_serviceDescription - $protocol Port $externalPort',
        leaseDuration: _leaseDuration,
      );
      
      if (result) {
        _forwardedPorts[externalPort] = protocol;
        _logger.i('Port mapping added successfully');
      } else {
        _logger.w('Failed to add port mapping');
      }
      
      return result;
    } catch (e) {
      _logger.e('Error adding port mapping: $e');
      return false;
    }
  }

  /// Remove a previously set up port forwarding
  Future<bool> removePortMapping({
    required int externalPort,
    required String protocol, // 'TCP' or 'UDP'
  }) async {
    try {
      if (!await isAvailable()) {
        return false;
      }
      
      final result = await _upnp.deletePortMapping(
        externalPort: externalPort,
        protocol: protocol,
      );
      
      if (result) {
        _forwardedPorts.remove(externalPort);
        _logger.i('Port mapping removed successfully: $externalPort ($protocol)');
      } else {
        _logger.w('Failed to remove port mapping: $externalPort ($protocol)');
      }
      
      return result;
    } catch (e) {
      _logger.e('Error removing port mapping: $e');
      return false;
    }
  }

  /// Remove all port mappings created by this application
  Future<void> removeAllPortMappings() async {
    final ports = Map<int, String>.from(_forwardedPorts);
    
    for (final entry in ports.entries) {
      await removePortMapping(
        externalPort: entry.key,
        protocol: entry.value,
      );
    }
    
    _logger.i('All port mappings removed');
  }

  /// Set up standard port mappings for the Forex Trading Bot
  Future<bool> setupTradingBotPorts({
    required int httpPort,
    required int wsPort,
  }) async {
    try {
      final httpResult = await addPortMapping(
        externalPort: httpPort,
        internalPort: httpPort,
        protocol: 'TCP',
        description: '$_serviceDescription - HTTP API',
      );
      
      final wsResult = await addPortMapping(
        externalPort: wsPort,
        internalPort: wsPort,
        protocol: 'TCP',
        description: '$_serviceDescription - WebSocket',
      );
      
      return httpResult && wsResult;
    } catch (e) {
      _logger.e('Error setting up trading bot ports: $e');
      return false;
    }
  }

  /// Get a list of all UPnP devices on the network
  Future<List<Map<String, dynamic>>> getDevices() async {
    try {
      final devices = await _upnp.getDevices();
      return devices.map((device) => Map<String, dynamic>.from(device)).toList();
    } catch (e) {
      _logger.e('Error getting UPnP devices: $e');
      return [];
    }
  }

  /// Clean up resources when no longer needed
  Future<void> dispose() async {
    try {
      await removeAllPortMappings();
      await _upnp.dispose();
      _logger.i('UPnP service disposed');
    } catch (e) {
      _logger.e('Error disposing UPnP service: $e');
    }
  }
}
