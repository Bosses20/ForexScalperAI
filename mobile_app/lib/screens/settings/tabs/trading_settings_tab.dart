import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../blocs/settings/settings_bloc.dart';
import '../../../blocs/settings/settings_event.dart';
import '../../../models/settings/bot_settings.dart';

class TradingSettingsTab extends StatefulWidget {
  final TradingSettings settings;

  const TradingSettingsTab({
    Key? key,
    required this.settings,
  }) : super(key: key);

  @override
  State<TradingSettingsTab> createState() => _TradingSettingsTabState();
}

class _TradingSettingsTabState extends State<TradingSettingsTab> {
  final _formKey = GlobalKey<FormState>();
  
  late List<TradingInstrument> _instruments;
  late List<String> _timeframes;
  late String _strategyTimeframe;
  late int _updateInterval;
  
  @override
  void initState() {
    super.initState();
    _initializeFromSettings();
  }
  
  @override
  void didUpdateWidget(TradingSettingsTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.settings != widget.settings) {
      _initializeFromSettings();
    }
  }
  
  void _initializeFromSettings() {
    _instruments = List.from(widget.settings.instruments);
    _timeframes = List.from(widget.settings.timeframes);
    _strategyTimeframe = widget.settings.strategyTimeframe;
    _updateInterval = widget.settings.updateInterval;
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
              'Trading Settings',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            _buildTimeframeSection(),
            const SizedBox(height: 24),
            _buildInstrumentsSection(),
            const SizedBox(height: 32),
            _buildSaveButton(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildTimeframeSection() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Timeframe Settings',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            
            // Strategy Timeframe Dropdown
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(
                labelText: 'Primary Strategy Timeframe',
                border: OutlineInputBorder(),
              ),
              value: _strategyTimeframe,
              items: ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
                  .map((timeframe) => DropdownMenuItem(
                        value: timeframe,
                        child: Text(timeframe),
                      ))
                  .toList(),
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _strategyTimeframe = value;
                  });
                }
              },
            ),
            
            const SizedBox(height: 16),
            
            // Update Interval Field
            TextFormField(
              decoration: const InputDecoration(
                labelText: 'Update Interval (seconds)',
                helperText: 'How often the trading loop runs',
                border: OutlineInputBorder(),
              ),
              initialValue: _updateInterval.toString(),
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
                _updateInterval = int.parse(value!);
              },
            ),
            
            const SizedBox(height: 16),
            
            // Timeframes Multiselect
            const Text(
              'Active Timeframes',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                _buildTimeframeChip('M1'),
                _buildTimeframeChip('M5'),
                _buildTimeframeChip('M15'),
                _buildTimeframeChip('M30'),
                _buildTimeframeChip('H1'),
                _buildTimeframeChip('H4'),
                _buildTimeframeChip('D1'),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildTimeframeChip(String timeframe) {
    final isSelected = _timeframes.contains(timeframe);
    
    return FilterChip(
      label: Text(timeframe),
      selected: isSelected,
      onSelected: (selected) {
        setState(() {
          if (selected) {
            if (!_timeframes.contains(timeframe)) {
              _timeframes.add(timeframe);
            }
          } else {
            // Don't allow removing the strategy timeframe
            if (timeframe != _strategyTimeframe) {
              _timeframes.remove(timeframe);
            } else {
              // Show a snackbar to inform the user
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text(
                    "Can't remove the primary strategy timeframe",
                  ),
                ),
              );
            }
          }
        });
      },
    );
  }
  
  Widget _buildInstrumentsSection() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Trading Instruments',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Select which instruments you want the bot to trade',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 16),
            
            // List of instruments with toggle switches
            ...List.generate(_instruments.length, (index) {
              final instrument = _instruments[index];
              return ListTile(
                title: Text(instrument.name),
                subtitle: Text(instrument.description),
                trailing: Switch(
                  value: instrument.enabled,
                  onChanged: (value) {
                    setState(() {
                      _instruments[index] = instrument.copyWith(enabled: value);
                    });
                  },
                ),
              );
            }),
          ],
        ),
      ),
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
        child: const Text('Save Trading Settings'),
      ),
    );
  }
  
  void _saveSettings() {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      
      // Make sure strategy timeframe is in timeframes list
      if (!_timeframes.contains(_strategyTimeframe)) {
        _timeframes.add(_strategyTimeframe);
      }
      
      // Create updated settings
      final updatedSettings = TradingSettings(
        instruments: _instruments,
        timeframes: _timeframes,
        strategyTimeframe: _strategyTimeframe,
        updateInterval: _updateInterval,
        tradeSessions: widget.settings.tradeSessions, // Keep existing trade sessions
      );
      
      // Dispatch update event
      context.read<SettingsBloc>().add(
        UpdateTradingSettings(updatedSettings),
      );
    }
  }
}
