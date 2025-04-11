import 'dart:async';
import 'dart:io';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'package:flutter/foundation.dart';

import 'logger.dart';

/// Utility class for network-related operations
class NetworkUtils {
  static const String _logTag = 'NetworkUtils';
  static final Logger _logger = Logger(_logTag);
  static final NetworkInfo _networkInfo = NetworkInfo();
  static final Connectivity _connectivity = Connectivity();
  
  /// Get the device's current Wi-Fi IP address
  static Future<String?> getLocalIpAddress() async {
    try {
      // Try to get the Wi-Fi IP address first
      final wifiIp = await _networkInfo.getWifiIP();
      if (wifiIp != null && wifiIp.isNotEmpty) {
        return wifiIp;
      }
      
      // Fallback to network interfaces if Wi-Fi IP isn't available
      final interfaces = await NetworkInterface.list(
        includeLinkLocal: false,
        type: InternetAddressType.IPv4,
      );
      
      if (interfaces.isEmpty) {
        _logger.w('No network interfaces found');
        return null;
      }
      
      // Find the first non-loopback IPv4 address
      for (var interface in interfaces) {
        for (var addr in interface.addresses) {
          if (!addr.isLoopback && addr.type == InternetAddressType.IPv4) {
            return addr.address;
          }
        }
      }
      
      return null;
    } catch (e) {
      _logger.e('Error getting local IP address: $e');
      return null;
    }
  }
  
  /// Get the subnet mask for the current network
  static Future<String?> getSubnetMask() async {
    try {
      final interfaces = await NetworkInterface.list(
        includeLinkLocal: false,
        type: InternetAddressType.IPv4,
      );
      
      for (var interface in interfaces) {
        for (var addr in interface.addresses) {
          if (!addr.isLoopback && addr.type == InternetAddressType.IPv4) {
            // Convert prefix length to subnet mask
            final mask = _prefixLengthToSubnetMask(addr.prefixLength);
            return mask;
          }
        }
      }
      
      return null;
    } catch (e) {
      _logger.e('Error getting subnet mask: $e');
      return null;
    }
  }
  
  /// Convert CIDR prefix length to subnet mask
  static String _prefixLengthToSubnetMask(int prefixLength) {
    if (prefixLength < 0 || prefixLength > 32) {
      return '255.255.255.0'; // Default to common class C subnet
    }
    
    final mask = ~((1 << (32 - prefixLength)) - 1);
    final octet1 = (mask >> 24) & 0xFF;
    final octet2 = (mask >> 16) & 0xFF;
    final octet3 = (mask >> 8) & 0xFF;
    final octet4 = mask & 0xFF;
    
    return '$octet1.$octet2.$octet3.$octet4';
  }
  
  /// Get the network address for the current IP and subnet mask
  static Future<String?> getNetworkAddress() async {
    try {
      final ip = await getLocalIpAddress();
      final mask = await getSubnetMask();
      
      if (ip == null || mask == null) {
        return null;
      }
      
      final ipParts = ip.split('.').map(int.parse).toList();
      final maskParts = mask.split('.').map(int.parse).toList();
      
      final networkParts = List<int>.filled(4, 0);
      for (var i = 0; i < 4; i++) {
        networkParts[i] = ipParts[i] & maskParts[i];
      }
      
      return networkParts.join('.');
    } catch (e) {
      _logger.e('Error getting network address: $e');
      return null;
    }
  }
  
  /// Check if the device is connected to a WiFi network
  static Future<bool> isConnectedToWiFi() async {
    try {
      final connectivityResult = await _connectivity.checkConnectivity();
      return connectivityResult == ConnectivityResult.wifi;
    } catch (e) {
      _logger.e('Error checking WiFi connectivity: $e');
      return false;
    }
  }
  
  /// Check if a host is reachable by pinging it
  static Future<bool> isHostReachable(String host, {int timeout = 5}) async {
    try {
      final result = await InternetAddress.lookup(host)
          .timeout(Duration(seconds: timeout));
      return result.isNotEmpty && result[0].rawAddress.isNotEmpty;
    } on SocketException catch (_) {
      return false;
    } on TimeoutException catch (_) {
      return false;
    } catch (e) {
      _logger.e('Error checking if host is reachable: $e');
      return false;
    }
  }
  
  /// Check if a specific port is open on a host
  static Future<bool> isPortOpen(String host, int port, {int timeout = 3}) async {
    try {
      final socket = await Socket.connect(
        host, 
        port, 
        timeout: Duration(seconds: timeout),
      );
      await socket.close();
      return true;
    } catch (e) {
      return false;
    }
  }
  
  /// Get a list of all available network interfaces
  static Future<List<NetworkInterface>> getNetworkInterfaces() async {
    try {
      return await NetworkInterface.list(
        includeLinkLocal: false,
        type: InternetAddressType.IPv4,
      );
    } catch (e) {
      _logger.e('Error getting network interfaces: $e');
      return [];
    }
  }
  
  /// Check if the network has an active internet connection
  static Future<bool> hasInternetConnection() async {
    try {
      final result = await InternetAddress.lookup('google.com');
      return result.isNotEmpty && result[0].rawAddress.isNotEmpty;
    } on SocketException catch (_) {
      return false;
    } catch (e) {
      _logger.e('Error checking internet connection: $e');
      return false;
    }
  }

  /// Generate a list of IP addresses for the current subnet
  static Future<List<String>> getSubnetIpAddresses() async {
    try {
      final networkAddress = await getNetworkAddress();
      if (networkAddress == null) {
        return [];
      }
      
      final baseIp = networkAddress.substring(0, networkAddress.lastIndexOf('.') + 1);
      
      // Generate 254 IPs (1-254)
      return List.generate(254, (i) => '$baseIp${i + 1}');
    } catch (e) {
      _logger.e('Error generating subnet IP addresses: $e');
      return [];
    }
  }
  
  /// Stream of connectivity changes
  static Stream<ConnectivityResult> get connectivityChanges {
    return _connectivity.onConnectivityChanged;
  }
  
  /// Format an IP address and port as a URL
  static String formatAsUrl(String ip, int port, {bool secure = false}) {
    final protocol = secure ? 'https' : 'http';
    return '$protocol://$ip:$port';
  }
  
  /// Format an IP address and port as a WebSocket URL
  static String formatAsWsUrl(String ip, int port, {bool secure = false}) {
    final protocol = secure ? 'wss' : 'ws';
    return '$protocol://$ip:$port/ws';
  }
}
