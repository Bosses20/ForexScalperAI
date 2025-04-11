import 'package:flutter/material.dart';
import '../../models/bot_server.dart';

class ServerSelectionScreen extends StatefulWidget {
  final BotServer? initialServer;

  const ServerSelectionScreen({Key? key, this.initialServer}) : super(key: key);

  @override
  State<ServerSelectionScreen> createState() => _ServerSelectionScreenState();
}

class _ServerSelectionScreenState extends State<ServerSelectionScreen> {
  late List<BotServer> _availableServers;
  late BotServer _selectedServer;
  final TextEditingController _customServerController = TextEditingController();
  bool _isCustomServer = false;

  @override
  void initState() {
    super.initState();
    // Initialize with predefined MT5 broker servers
    _availableServers = [
      const BotServer(
        name: 'DerivBVI-Server-03',
        host: '127.0.0.1', // Local server for development
        port: 8000,
        isSecure: false,
      ),
      const BotServer(
        name: 'DerivLabuan-Server-01',
        host: '127.0.0.1', // Local server for development
        port: 8000,
        isSecure: false,
      ),
      const BotServer(
        name: 'MetaQuotes-Demo01',
        host: '127.0.0.1', // Local server for development
        port: 8000,
        isSecure: false,
      ),
      const BotServer(
        name: 'MetaQuotes-Demo02',
        host: '127.0.0.1', // Local server for development
        port: 8000,
        isSecure: false,
      ),
    ];

    // Set initial selected server
    _selectedServer = widget.initialServer ?? _availableServers.first;
  }

  @override
  void dispose() {
    _customServerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1E222D),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E222D),
        title: const Text('Select Server'),
        elevation: 0,
        iconTheme: const IconThemeData(
          color: Colors.white,
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Description text
            const Text(
              'Select your MT5 broker server',
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8.0),
            const Text(
              'Choose the server that matches your MT5 trading account.',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 24.0),
            
            // Server list
            Expanded(
              child: ListView.builder(
                itemCount: _availableServers.length + 1, // +1 for custom server option
                itemBuilder: (context, index) {
                  if (index < _availableServers.length) {
                    final server = _availableServers[index];
                    return _buildServerItem(server);
                  } else {
                    // Custom server option
                    return _buildCustomServerOption();
                  }
                },
              ),
            ),
            
            // Continue button
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context, _selectedServer);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              child: const Text(
                'CONTINUE',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildServerItem(BotServer server) {
    final isSelected = _selectedServer.name == server.name && !_isCustomServer;
    
    return Card(
      color: isSelected ? const Color(0xFF2F3542) : const Color(0xFF262A35),
      margin: const EdgeInsets.only(bottom: 8.0),
      child: InkWell(
        onTap: () {
          setState(() {
            _selectedServer = server;
            _isCustomServer = false;
          });
        },
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Icon(
                Icons.dns,
                color: isSelected ? Colors.blue : Colors.white70,
              ),
              const SizedBox(width: 16.0),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      server.name,
                      style: TextStyle(
                        color: isSelected ? Colors.white : Colors.white70,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        fontSize: 16,
                      ),
                    ),
                    Text(
                      'Local development server',
                      style: TextStyle(
                        color: Colors.white60,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              if (isSelected)
                const Icon(
                  Icons.check_circle,
                  color: Colors.blue,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCustomServerOption() {
    return Card(
      color: _isCustomServer ? const Color(0xFF2F3542) : const Color(0xFF262A35),
      margin: const EdgeInsets.only(bottom: 8.0),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            InkWell(
              onTap: () {
                setState(() {
                  _isCustomServer = true;
                  if (_customServerController.text.isNotEmpty) {
                    _selectedServer = BotServer(
                      name: _customServerController.text,
                      host: '127.0.0.1', // Default to localhost
                      port: 8000,
                      isSecure: false,
                    );
                  }
                });
              },
              child: Row(
                children: [
                  Icon(
                    Icons.add_circle_outline,
                    color: _isCustomServer ? Colors.blue : Colors.white70,
                  ),
                  const SizedBox(width: 16.0),
                  Text(
                    'Custom Server',
                    style: TextStyle(
                      color: _isCustomServer ? Colors.white : Colors.white70,
                      fontWeight: _isCustomServer ? FontWeight.bold : FontWeight.normal,
                      fontSize: 16,
                    ),
                  ),
                  const Spacer(),
                  if (_isCustomServer)
                    const Icon(
                      Icons.check_circle,
                      color: Colors.blue,
                    ),
                ],
              ),
            ),
            if (_isCustomServer) ...[
              const SizedBox(height: 16.0),
              TextField(
                controller: _customServerController,
                decoration: const InputDecoration(
                  labelText: 'Server Name',
                  labelStyle: TextStyle(color: Colors.white70),
                  hintText: 'Enter your broker\'s server name',
                  hintStyle: TextStyle(color: Colors.white30),
                  enabledBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: Colors.white30),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: Colors.blue),
                  ),
                ),
                style: const TextStyle(color: Colors.white),
                onChanged: (value) {
                  setState(() {
                    _selectedServer = BotServer(
                      name: value,
                      host: '127.0.0.1', // Default to localhost for local deployment
                      port: 8000,
                      isSecure: false,
                    );
                  });
                },
              ),
              const SizedBox(height: 8.0),
              const Text(
                'Note: This will connect to your local bot server.',
                style: TextStyle(
                  color: Colors.white60,
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
