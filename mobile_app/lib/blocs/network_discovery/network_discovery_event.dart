import 'package:equatable/equatable.dart';

import '../../models/bot_server.dart';

/// Events for the network discovery bloc
abstract class NetworkDiscoveryEvent extends Equatable {
  const NetworkDiscoveryEvent();

  @override
  List<Object?> get props => [];
}

/// Event to load previously cached servers
class LoadCachedServersEvent extends NetworkDiscoveryEvent {
  const LoadCachedServersEvent();
}

/// Event to start scanning the network for bot servers
class StartNetworkScanEvent extends NetworkDiscoveryEvent {
  const StartNetworkScanEvent();
}

/// Event to add a manually configured server
class AddManualServerEvent extends NetworkDiscoveryEvent {
  final BotServer server;

  const AddManualServerEvent(this.server);

  @override
  List<Object?> get props => [server];
}

/// Event to remove a server from the list
class RemoveServerEvent extends NetworkDiscoveryEvent {
  final BotServer server;

  const RemoveServerEvent(this.server);

  @override
  List<Object?> get props => [server];
}

/// Event to toggle a server's favorite status
class ToggleServerFavoriteEvent extends NetworkDiscoveryEvent {
  final BotServer server;

  const ToggleServerFavoriteEvent(this.server);

  @override
  List<Object?> get props => [server];
}

/// Event to connect to a server
class ConnectToServerEvent extends NetworkDiscoveryEvent {
  final BotServer server;
  final String? username;
  final String? password;

  const ConnectToServerEvent({
    required this.server,
    this.username,
    this.password,
  });

  @override
  List<Object?> get props => [server, username, password];
}

/// Event for scanning QR code to connect to a server
class ScanQrCodeEvent extends NetworkDiscoveryEvent {
  final String qrData;

  const ScanQrCodeEvent(this.qrData);

  @override
  List<Object?> get props => [qrData];
}
