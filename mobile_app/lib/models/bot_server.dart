import 'package:equatable/equatable.dart';
import 'dart:convert';

/// Model representing a bot server discovered on the network
class BotServer extends Equatable {
  /// The name of the server
  final String name;
  
  /// The host or IP address of the server
  final String host;
  
  /// The port number of the server
  final int port;
  
  /// Whether the server was discovered automatically (true) or added manually (false)
  final bool isDiscovered;
  
  /// The software version running on the server
  final String version;
  
  /// Whether the server requires authentication
  final bool requiresAuth;
  
  /// When the server was last seen on the network
  final DateTime lastSeen;
  
  /// When the user last connected to this server
  final DateTime? lastConnected;

  /// Favorite status to allow users to mark preferred servers
  final bool isFavorite;

  /// Base URL for API requests
  String get baseUrl => 'http://$host:$port';
  
  /// WebSocket URL for real-time updates
  String get wsUrl => 'ws://$host:$port/ws';
  
  /// QR code URL to easily connect to the server
  String get qrCodeUrl => '$baseUrl/qr-code';
  
  /// Check if the server is likely reachable (last seen within the past 10 minutes)
  bool get isLikelyReachable {
    final tenMinutesAgo = DateTime.now().subtract(const Duration(minutes: 10));
    return lastSeen.isAfter(tenMinutesAgo);
  }

  const BotServer({
    required this.name,
    required this.host,
    required this.port,
    required this.isDiscovered,
    required this.version,
    required this.requiresAuth,
    required this.lastSeen,
    this.lastConnected,
    this.isFavorite = false,
  });
  
  /// Get the full URL for connecting to the server
  String getUrl() => baseUrl;
  
  /// Check if this server matches the provided URL
  bool matchesUrl(String url) {
    final uri = Uri.parse(url);
    final serverUrl = Uri.parse(baseUrl);
    return uri.host == serverUrl.host && uri.port == serverUrl.port;
  }

  /// Create a copy of this server with modified fields
  BotServer copyWith({
    String? name,
    String? host,
    int? port,
    bool? isDiscovered,
    String? version,
    bool? requiresAuth,
    DateTime? lastSeen,
    DateTime? lastConnected,
    bool? isFavorite,
  }) {
    return BotServer(
      name: name ?? this.name,
      host: host ?? this.host,
      port: port ?? this.port,
      isDiscovered: isDiscovered ?? this.isDiscovered,
      version: version ?? this.version,
      requiresAuth: requiresAuth ?? this.requiresAuth,
      lastSeen: lastSeen ?? this.lastSeen,
      lastConnected: lastConnected ?? this.lastConnected,
      isFavorite: isFavorite ?? this.isFavorite,
    );
  }

  /// Convert server to JSON for caching
  String toJson() {
    return '''{
      "name": "$name",
      "host": "$host",
      "port": $port,
      "isDiscovered": $isDiscovered,
      "version": "$version",
      "requiresAuth": $requiresAuth,
      "lastSeen": "${lastSeen.toIso8601String()}",
      ${lastConnected != null ? '"lastConnected": "${lastConnected!.toIso8601String()}",' : ''}
      "isFavorite": $isFavorite
    }''';
  }

  /// Create server from JSON data
  factory BotServer.fromJson(String jsonString) {
    final json = Map<String, dynamic>.from(
      jsonDecode(jsonString) as Map,
    );
    
    return BotServer(
      name: json['name'] as String,
      host: json['host'] as String,
      port: json['port'] as int,
      isDiscovered: json['isDiscovered'] as bool,
      version: json['version'] as String,
      requiresAuth: json['requiresAuth'] as bool,
      lastSeen: DateTime.parse(json['lastSeen'] as String),
      lastConnected: json['lastConnected'] != null
          ? DateTime.parse(json['lastConnected'] as String)
          : null,
      isFavorite: json['isFavorite'] as bool? ?? false,
    );
  }
  
  /// Create a server from discovered network service
  factory BotServer.fromDiscoveredService({
    required String name,
    required String host,
    required int port,
    required String version,
    required bool requiresAuth,
  }) {
    return BotServer(
      name: name,
      host: host,
      port: port,
      isDiscovered: true,
      version: version,
      requiresAuth: requiresAuth,
      lastSeen: DateTime.now(),
    );
  }
  
  /// Create a server manually
  factory BotServer.manual({
    required String name,
    required String host,
    required int port,
    String version = 'Unknown',
    bool requiresAuth = true,
  }) {
    return BotServer(
      name: name,
      host: host,
      port: port,
      isDiscovered: false,
      version: version,
      requiresAuth: requiresAuth,
      lastSeen: DateTime.now(),
    );
  }

  @override
  List<Object?> get props => [host, port];

  @override
  String toString() => '$name ($host:$port)';
}
