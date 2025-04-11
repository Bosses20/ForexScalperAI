import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../blocs/network_discovery/network_discovery_bloc.dart';
import '../../blocs/network_discovery/network_discovery_event.dart';
import '../../models/bot_server.dart';

/// Dialog for manually adding a trading bot server
class AddServerDialog extends StatefulWidget {
  const AddServerDialog({Key? key}) : super(key: key);

  @override
  State<AddServerDialog> createState() => _AddServerDialogState();
}

class _AddServerDialogState extends State<AddServerDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController(text: 'Trading Bot Server');
  final _hostController = TextEditingController();
  final _portController = TextEditingController(text: '8000');

  @override
  void dispose() {
    _nameController.dispose();
    _hostController.dispose();
    _portController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add Server Manually'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Server Name',
                hintText: 'Trading Bot Server',
                prefixIcon: Icon(Icons.label),
              ),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Please enter a server name';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _hostController,
              decoration: const InputDecoration(
                labelText: 'IP Address / Hostname',
                hintText: '192.168.1.100',
                prefixIcon: Icon(Icons.computer),
              ),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Please enter an IP address or hostname';
                }
                // Basic IP address validation
                if (!value.contains('.') && 
                    !RegExp(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]').hasMatch(value)) {
                  return 'Please enter a valid IP address or hostname';
                }
                return null;
              },
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _portController,
              decoration: const InputDecoration(
                labelText: 'Port',
                hintText: '8000',
                prefixIcon: Icon(Icons.router),
              ),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Please enter a port';
                }
                final port = int.tryParse(value);
                if (port == null || port <= 0 || port > 65535) {
                  return 'Please enter a valid port number (1-65535)';
                }
                return null;
              },
              keyboardType: TextInputType.number,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
              ],
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () => _submitForm(),
          child: const Text('Add Server'),
        ),
      ],
    );
  }

  void _submitForm() {
    if (_formKey.currentState?.validate() ?? false) {
      final name = _nameController.text.trim();
      final host = _hostController.text.trim();
      final port = int.parse(_portController.text.trim());

      final server = BotServer(
        name: name,
        host: host,
        port: port,
        isDiscovered: false, // Manual entry
        version: '1.0.0', // Default value
        requiresAuth: true, // Assume authentication is required
        lastSeen: DateTime.now(),
      );

      context.read<NetworkDiscoveryBloc>().add(AddManualServerEvent(server));
      Navigator.of(context).pop();
    }
  }
}
