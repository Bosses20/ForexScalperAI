import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:mobile_app/utils/formatters.dart';

import '../../blocs/network_discovery/network_discovery_bloc.dart';
import '../../blocs/network_discovery/network_discovery_event.dart';
import '../../blocs/network_discovery/network_discovery_state.dart';
import '../../models/bot_server.dart';
import 'add_server_dialog.dart';
import 'qr_scanner_screen.dart';

/// Screen for discovering trading bot servers on the local network
class ServerDiscoveryScreen extends StatefulWidget {
  const ServerDiscoveryScreen({Key? key}) : super(key: key);

  @override
  State<ServerDiscoveryScreen> createState() => _ServerDiscoveryScreenState();
}

class _ServerDiscoveryScreenState extends State<ServerDiscoveryScreen> {
  @override
  void initState() {
    super.initState();
    // Load cached servers on init
    context.read<NetworkDiscoveryBloc>().add(const LoadCachedServersEvent());
    
    // Auto-connect to last active server if available
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _tryAutoConnect();
    });
  }

  /// Try to automatically connect to the last active server
  Future<void> _tryAutoConnect() async {
    final bloc = context.read<NetworkDiscoveryBloc>();
    if (bloc.state is ServersLoadedState) {
      final servers = (bloc.state as ServersLoadedState).servers;
      if (servers.isNotEmpty) {
        // First try to find the last connected server
        final lastConnected = servers.where((s) => s.lastConnected != null)
            .toList()
            ..sort((a, b) => b.lastConnected!.compareTo(a.lastConnected!));
        
        if (lastConnected.isNotEmpty) {
          // Connect to the most recently used server
          _connectToServer(lastConnected.first);
          return;
        }
        
        // If no last connected server, try the first reachable server
        final reachable = servers.where((s) => s.isLikelyReachable).toList();
        if (reachable.isNotEmpty) {
          _connectToServer(reachable.first);
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Connect to Trading Bot'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            tooltip: 'Scan QR Code',
            onPressed: () => _navigateToQrScanner(),
          ),
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Add Server Manually',
            onPressed: () => _showAddServerDialog(),
          ),
        ],
      ),
      body: BlocConsumer<NetworkDiscoveryBloc, NetworkDiscoveryState>(
        listener: (context, state) {
          if (state is ServersLoadedState && state.error != null) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.error!),
                backgroundColor: Theme.of(context).colorScheme.error,
              ),
            );
          } else if (state is NetworkDiscoveryErrorState) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.message),
                backgroundColor: Theme.of(context).colorScheme.error,
              ),
            );
          }
        },
        builder: (context, state) {
          if (state is LoadingCachedServersState) {
            return const Center(child: CircularProgressIndicator());
          }
          
          if (state is ScanningNetworkState) {
            return _buildScanningView();
          }
          
          if (state is ConnectingToServerState) {
            return _buildConnectingView(state.server);
          }
          
          if (state is ServersLoadedState) {
            return _buildServerList(context, state.servers);
          }
          
          // Initial state or error state with no servers
          return _buildEmptyView();
        },
      ),
      floatingActionButton: BlocBuilder<NetworkDiscoveryBloc, NetworkDiscoveryState>(
        builder: (context, state) {
          if (state is ScanningNetworkState) {
            return FloatingActionButton(
              onPressed: () => _cancelScan(),
              tooltip: 'Cancel Scan',
              child: const Icon(Icons.close),
            );
          } else {
            return FloatingActionButton(
              onPressed: () => _startScan(),
              tooltip: 'Scan Network',
              child: const Icon(Icons.search),
            );
          }
        },
      ),
    );
  }

  Widget _buildEmptyView() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.computer,
            size: 80,
            color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'No Trading Bot Servers Found',
            style: Theme.of(context).textTheme.headlineSmall,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32.0),
            child: Text(
              'Make sure your trading bot is running on your PC and connected to the same network',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: () => _startScan(),
            icon: const Icon(Icons.wifi_find),
            label: const Text('Scan Network'),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () => _showAddServerDialog(),
            icon: const Icon(Icons.add),
            label: const Text('Add Server Manually'),
          ),
          const SizedBox(height: 16),
          TextButton.icon(
            onPressed: () => _navigateToQrScanner(),
            icon: const Icon(Icons.qr_code),
            label: const Text('Scan QR Code'),
          ),
        ],
      ),
    );
  }

  Widget _buildScanningView() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(
            width: 80,
            height: 80,
            child: CircularProgressIndicator(),
          ),
          const SizedBox(height: 24),
          Text(
            'Scanning Network...',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Looking for trading bot servers on your network',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 36),
          OutlinedButton.icon(
            onPressed: () => _cancelScan(),
            icon: const Icon(Icons.cancel),
            label: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  Widget _buildConnectingView(BotServer server) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(
            width: 80,
            height: 80,
            child: CircularProgressIndicator(),
          ),
          const SizedBox(height: 24),
          Text(
            'Connecting...',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Establishing connection to ${server.name}',
            style: Theme.of(context).textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            server.host,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _buildServerList(BuildContext context, List<BotServer> servers) {
    if (servers.isEmpty) {
      return _buildEmptyView();
    }
    
    // Sort servers: first favorites, then by last connection time
    final sortedServers = List<BotServer>.from(servers)
      ..sort((a, b) {
        // First sort by favorite status
        if (a.isFavorite && !b.isFavorite) return -1;
        if (!a.isFavorite && b.isFavorite) return 1;
        
        // Then sort by last connection time
        if (a.lastConnected != null && b.lastConnected != null) {
          return b.lastConnected!.compareTo(a.lastConnected!);
        } else if (a.lastConnected != null) {
          return -1;
        } else if (b.lastConnected != null) {
          return 1;
        }
        
        // Then sort by name
        return a.name.compareTo(b.name);
      });
    
    return Stack(
      children: [
        // List of servers
        ListView.builder(
          padding: const EdgeInsets.only(bottom: 80), // Space for quick trade button
          itemCount: sortedServers.length,
          itemBuilder: (context, index) {
            final server = sortedServers[index];
            return _buildServerListItem(context, server);
          },
        ),
        
        // Quick Trade button
        Positioned(
          bottom: 16,
          left: 0,
          right: 0,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: ElevatedButton.icon(
              onPressed: sortedServers.any((s) => s.isLikelyReachable)
                  ? () => _quickTradeStart(sortedServers)
                  : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.primary,
                foregroundColor: Theme.of(context).colorScheme.onPrimary,
                padding: const EdgeInsets.symmetric(vertical: 16),
                textStyle: Theme.of(context).textTheme.titleLarge,
              ),
              icon: const Icon(Icons.play_arrow, size: 30),
              label: const Text('QUICK TRADE'),
            ),
          ),
        ),
      ],
    );
  }
  
  /// Start trading with the best available server
  void _quickTradeStart(List<BotServer> servers) {
    // First, try to find an active favorite server
    final favoriteAndReachable = servers.where(
      (s) => s.isFavorite && s.isLikelyReachable
    ).toList();
    
    if (favoriteAndReachable.isNotEmpty) {
      _connectAndStartTrading(favoriteAndReachable.first);
      return;
    }
    
    // Next, try any reachable server
    final reachable = servers.where((s) => s.isLikelyReachable).toList();
    if (reachable.isNotEmpty) {
      _connectAndStartTrading(reachable.first);
      return;
    }
    
    // If no reachable servers, try the last connected server
    final lastConnected = servers.where((s) => s.lastConnected != null)
        .toList()
        ..sort((a, b) => b.lastConnected!.compareTo(a.lastConnected!));
    
    if (lastConnected.isNotEmpty) {
      _connectAndStartTrading(lastConnected.first);
      return;
    }
    
    // If no good options, use the first server
    if (servers.isNotEmpty) {
      _connectAndStartTrading(servers.first);
    } else {
      // No servers available, show error
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No trading servers available. Please add a server or scan the network.'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
  
  /// Connect to server and automatically start trading
  void _connectAndStartTrading(BotServer server) async {
    // First connect to the server
    _connectToServer(server);
    
    // Wait for connection to complete
    await Future.delayed(const Duration(seconds: 2));
    
    // Navigate to dashboard with auto-start flag
    Navigator.pushReplacementNamed(
      context, 
      '/dashboard',
      arguments: {'autoStartTrading': true}
    );
  }

  Widget _buildServerListItem(BuildContext context, BotServer server) {
    final lastSeen = formatTimeAgo(server.lastSeen);
    
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: InkWell(
        onTap: () => _connectToServer(server),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(24),
                ),
                child: Icon(
                  server.isDiscovered ? Icons.computer : Icons.dns,
                  color: Theme.of(context).colorScheme.onPrimaryContainer,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      server.name,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${server.host}:${server.port}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(
                          Icons.access_time,
                          size: 14,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          'Last seen $lastSeen',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Column(
                children: [
                  IconButton(
                    icon: Icon(
                      server.isFavorite ? Icons.star : Icons.star_border,
                      color: server.isFavorite 
                          ? Theme.of(context).colorScheme.primary 
                          : Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    onPressed: () => _toggleFavorite(server),
                    tooltip: server.isFavorite ? 'Remove from favorites' : 'Add to favorites',
                  ),
                  IconButton(
                    icon: const Icon(Icons.more_vert),
                    onPressed: () => _showServerOptions(server),
                    tooltip: 'More options',
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _startScan() {
    context.read<NetworkDiscoveryBloc>().add(const StartNetworkScanEvent());
  }
  
  void _cancelScan() {
    // We don't have a dedicated cancel event, so just load cached servers
    context.read<NetworkDiscoveryBloc>().add(const LoadCachedServersEvent());
  }
  
  void _showAddServerDialog() {
    showDialog(
      context: context,
      builder: (context) => const AddServerDialog(),
    );
  }
  
  void _navigateToQrScanner() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => const QrScannerScreen(),
      ),
    );
  }
  
  void _connectToServer(BotServer server) {
    context.read<NetworkDiscoveryBloc>().add(
      ConnectToServerEvent(server: server),
    );
  }
  
  void _toggleFavorite(BotServer server) {
    context.read<NetworkDiscoveryBloc>().add(
      ToggleServerFavoriteEvent(server),
    );
  }
  
  void _showServerOptions(BotServer server) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.connect_without_contact),
            title: const Text('Connect'),
            onTap: () {
              Navigator.pop(context);
              _connectToServer(server);
            },
          ),
          ListTile(
            leading: Icon(server.isFavorite ? Icons.star_border : Icons.star),
            title: Text(server.isFavorite ? 'Remove from favorites' : 'Add to favorites'),
            onTap: () {
              Navigator.pop(context);
              _toggleFavorite(server);
            },
          ),
          ListTile(
            leading: const Icon(Icons.delete),
            title: const Text('Remove'),
            onTap: () {
              Navigator.pop(context);
              _removeServer(server);
            },
          ),
        ],
      ),
    );
  }
  
  void _removeServer(BotServer server) {
    context.read<NetworkDiscoveryBloc>().add(
      RemoveServerEvent(server),
    );
  }
}
