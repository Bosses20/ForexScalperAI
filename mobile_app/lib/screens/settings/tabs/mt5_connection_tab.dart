import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../blocs/settings/settings_bloc.dart';
import '../../../blocs/settings/settings_event.dart';
import '../../../models/settings/bot_settings.dart';

class MT5ConnectionTab extends StatefulWidget {
  final MT5ConnectionSettings settings;

  const MT5ConnectionTab({
    Key? key,
    required this.settings,
  }) : super(key: key);

  @override
  State<MT5ConnectionTab> createState() => _MT5ConnectionTabState();
}

class _MT5ConnectionTabState extends State<MT5ConnectionTab> {
  late int _maxRetries;
  late int _retryDelay;
  late int _pingInterval;

  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _maxRetries = widget.settings.maxRetries;
    _retryDelay = widget.settings.retryDelay;
    _pingInterval = widget.settings.pingInterval;
  }

  @override
  void didUpdateWidget(MT5ConnectionTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.settings != widget.settings) {
      _maxRetries = widget.settings.maxRetries;
      _retryDelay = widget.settings.retryDelay;
      _pingInterval = widget.settings.pingInterval;
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'MT5 Connection Settings',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            _buildInfoCard(),
            const SizedBox(height: 24),
            _buildMaxRetriesField(),
            const SizedBox(height: 16),
            _buildRetryDelayField(),
            const SizedBox(height: 16),
            _buildPingIntervalField(),
            const SizedBox(height: 32),
            _buildSaveButton(),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text(
              'Connection Parameters',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: 8),
            Text(
              'These settings control how the app connects to the MT5 terminal. '
              'Adjusting these values can help with unstable connections or '
              'network issues.',
              style: TextStyle(fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMaxRetriesField() {
    return TextFormField(
      decoration: const InputDecoration(
        labelText: 'Maximum connection retries',
        helperText: 'Number of times to retry connecting to MT5 before giving up',
        border: OutlineInputBorder(),
      ),
      initialValue: _maxRetries.toString(),
      keyboardType: TextInputType.number,
      validator: (value) {
        if (value == null || value.isEmpty) {
          return 'Please enter a value';
        }
        final number = int.tryParse(value);
        if (number == null) {
          return 'Please enter a valid number';
        }
        if (number < 1 || number > 10) {
          return 'Please enter a value between 1 and 10';
        }
        return null;
      },
      onSaved: (value) {
        _maxRetries = int.parse(value!);
      },
    );
  }

  Widget _buildRetryDelayField() {
    return TextFormField(
      decoration: const InputDecoration(
        labelText: 'Retry delay (seconds)',
        helperText: 'Seconds to wait between connection retry attempts',
        border: OutlineInputBorder(),
      ),
      initialValue: _retryDelay.toString(),
      keyboardType: TextInputType.number,
      validator: (value) {
        if (value == null || value.isEmpty) {
          return 'Please enter a value';
        }
        final number = int.tryParse(value);
        if (number == null) {
          return 'Please enter a valid number';
        }
        if (number < 1 || number > 60) {
          return 'Please enter a value between 1 and 60';
        }
        return null;
      },
      onSaved: (value) {
        _retryDelay = int.parse(value!);
      },
    );
  }

  Widget _buildPingIntervalField() {
    return TextFormField(
      decoration: const InputDecoration(
        labelText: 'Ping interval (seconds)',
        helperText: 'How often to check if connection is still alive',
        border: OutlineInputBorder(),
      ),
      initialValue: _pingInterval.toString(),
      keyboardType: TextInputType.number,
      validator: (value) {
        if (value == null || value.isEmpty) {
          return 'Please enter a value';
        }
        final number = int.tryParse(value);
        if (number == null) {
          return 'Please enter a valid number';
        }
        if (number < 5 || number > 300) {
          return 'Please enter a value between 5 and 300';
        }
        return null;
      },
      onSaved: (value) {
        _pingInterval = int.parse(value!);
      },
    );
  }

  Widget _buildSaveButton() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: _saveSettings,
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 16),
        ),
        child: const Text('Save Connection Settings'),
      ),
    );
  }

  void _saveSettings() {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();

      final updatedSettings = MT5ConnectionSettings(
        maxRetries: _maxRetries,
        retryDelay: _retryDelay,
        pingInterval: _pingInterval,
      );

      context.read<SettingsBloc>().add(
            UpdateMT5ConnectionSettings(updatedSettings),
          );
    }
  }
}
