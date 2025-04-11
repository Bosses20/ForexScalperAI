import 'package:equatable/equatable.dart';

import '../../models/bot_server.dart';

/// States for the network discovery bloc
abstract class NetworkDiscoveryState extends Equatable {
  const NetworkDiscoveryState();

  @override
  List<Object?> get props => [];
}

/// Initial state before any actions are taken
class NetworkDiscoveryInitial extends NetworkDiscoveryState {
  const NetworkDiscoveryInitial();
}

/// State when loading cached servers
class LoadingCachedServersState extends NetworkDiscoveryState {
  const LoadingCachedServersState();
}

/// State when scanning the network for servers
class ScanningNetworkState extends NetworkDiscoveryState {
  const ScanningNetworkState();
}

/// State when servers have been loaded or discovered
class ServersLoadedState extends NetworkDiscoveryState {
  final List<BotServer> servers;
  final bool isConnected;
  final BotServer? connectedServer;
  final String? error;

  const ServersLoadedState({
    required this.servers,
    this.isConnected = false,
    this.connectedServer,
    this.error,
  });

  @override
  List<Object?> get props => [servers, isConnected, connectedServer, error];

  /// Create a copy of this state with modified fields
  ServersLoadedState copyWith({
    List<BotServer>? servers,
    bool? isConnected,
    BotServer? connectedServer,
    String? error,
    bool clearError = false,
  }) {
    return ServersLoadedState(
      servers: servers ?? this.servers,
      isConnected: isConnected ?? this.isConnected,
      connectedServer: connectedServer ?? this.connectedServer,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// State when connecting to a server
class ConnectingToServerState extends NetworkDiscoveryState {
  final BotServer server;

  const ConnectingToServerState(this.server);

  @override
  List<Object?> get props => [server];
}

/// State when an error occurs during network discovery
class NetworkDiscoveryErrorState extends NetworkDiscoveryState {
  final String message;
  final List<BotServer> servers;

  const NetworkDiscoveryErrorState({
    required this.message,
    this.servers = const [],
  });

  @override
  List<Object?> get props => [message, servers];
}
