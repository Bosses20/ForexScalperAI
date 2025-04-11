import 'dart:convert';

import '../models/bot_server.dart';
import '../utils/logger.dart';
import '../utils/network_utils.dart';

/// Service for generating and parsing QR codes for server connections
class QrCodeService {
  static const String _logTag = 'QrCodeService';
  static const String _qrProtocol = 'forexbot://';
  
  final Logger _logger = Logger(_logTag);
  
  // Singleton pattern
  static final QrCodeService _instance = QrCodeService._internal();
  
  factory QrCodeService() {
    return _instance;
  }
  
  QrCodeService._internal();
  
  /// Generate QR code data for a server
  String generateQrCodeData(BotServer server) {
    try {
      final queryParams = {
        'name': server.name,
        'version': server.version,
        'auth': server.requiresAuth.toString(),
      };
      
      // Build query string
      final queryString = queryParams.entries
          .map((e) => '${e.key}=${Uri.encodeComponent(e.value)}')
          .join('&');
      
      // Construct the URI
      final uri = '$_qrProtocol${server.host}:${server.port}?$queryString';
      
      _logger.i('Generated QR code data: $uri');
      return uri;
    } catch (e) {
      _logger.e('Error generating QR code data: $e');
      throw Exception('Failed to generate QR code data: $e');
    }
  }
  
  /// Parse QR code data to extract server information
  BotServer? parseQrCodeData(String qrData) {
    try {
      _logger.i('Parsing QR code data: $qrData');
      
      // Check if this is a valid Forex bot QR code
      if (!qrData.startsWith(_qrProtocol)) {
        _logger.w('Invalid QR code protocol: $qrData');
        return null;
      }
      
      // Parse the URI
      final uri = Uri.parse(qrData);
      final host = uri.host;
      final port = uri.port;
      
      if (host.isEmpty) {
        _logger.w('Invalid host in QR code: $qrData');
        return null;
      }
      
      if (port <= 0) {
        _logger.w('Invalid port in QR code: $qrData');
        return null;
      }
      
      // Extract query parameters
      final name = uri.queryParameters['name'] ?? 'Trading Bot Server';
      final version = uri.queryParameters['version'] ?? '1.0.0';
      final requiresAuth = uri.queryParameters['auth'] != 'false'; // Default to true
      
      return BotServer(
        name: name,
        host: host,
        port: port,
        isDiscovered: false, // Added manually via QR code
        version: version,
        requiresAuth: requiresAuth,
        lastSeen: DateTime.now(),
      );
    } catch (e) {
      _logger.e('Error parsing QR code data: $e');
      return null;
    }
  }
  
  /// Generate connection URL for direct linking
  String generateConnectionLink(BotServer server) {
    try {
      final data = {
        'server': {
          'name': server.name,
          'host': server.host,
          'port': server.port,
          'version': server.version,
          'requiresAuth': server.requiresAuth,
        }
      };
      
      final encodedData = base64Encode(utf8.encode(jsonEncode(data)));
      return 'forexbot://connect?data=$encodedData';
    } catch (e) {
      _logger.e('Error generating connection link: $e');
      throw Exception('Failed to generate connection link: $e');
    }
  }
  
  /// Parse a connection link
  BotServer? parseConnectionLink(String link) {
    try {
      if (!link.startsWith('forexbot://connect?data=')) {
        return null;
      }
      
      final uri = Uri.parse(link);
      final encodedData = uri.queryParameters['data'];
      
      if (encodedData == null) {
        return null;
      }
      
      final jsonData = utf8.decode(base64Decode(encodedData));
      final data = jsonDecode(jsonData) as Map<String, dynamic>;
      final serverData = data['server'] as Map<String, dynamic>;
      
      return BotServer(
        name: serverData['name'] as String,
        host: serverData['host'] as String,
        port: serverData['port'] as int,
        isDiscovered: false,
        version: serverData['version'] as String,
        requiresAuth: serverData['requiresAuth'] as bool,
        lastSeen: DateTime.now(),
      );
    } catch (e) {
      _logger.e('Error parsing connection link: $e');
      return null;
    }
  }
}
