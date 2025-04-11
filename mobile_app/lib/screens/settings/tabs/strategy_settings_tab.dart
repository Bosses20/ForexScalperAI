import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../blocs/settings/settings_bloc.dart';
import '../../../blocs/settings/settings_event.dart';
import '../../../models/settings/bot_settings.dart';

class StrategySettingsTab extends StatefulWidget {
  final StrategySettings settings;

  const StrategySettingsTab({
    Key? key,
    required this.settings,
  }) : super(key: key);

  @override
  State<StrategySettingsTab> createState() => _StrategySettingsTabState();
}

class _StrategySettingsTabState extends State<StrategySettingsTab> {
  final _formKey = GlobalKey<FormState>();
  
  late Map<String, bool> _enabledStrategies;
  late Map<String, dynamic> _strategyParameters;
  
  @override
  void initState() {
    super.initState();
    _initializeFromSettings();
  }
  
  @override
  void didUpdateWidget(StrategySettingsTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.settings != widget.settings) {
      _initializeFromSettings();
    }
  }
  
  void _initializeFromSettings() {
    _enabledStrategies = Map.from(widget.settings.enabledStrategies);
    _strategyParameters = Map.from(widget.settings.strategyParameters);
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
              'Strategy Settings',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            _buildStrategyEnablingSection(),
            const SizedBox(height: 24),
            _buildMarketConditionSection(),
            const SizedBox(height: 24),
            _buildMultiAssetSection(),
            const SizedBox(height: 24),
            _buildStrategyParametersSection(),
            const SizedBox(height: 32),
            _buildSaveButton(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildStrategyEnablingSection() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Active Strategies',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Enable or disable trading strategies',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 16),
            
            // Strategy activation switches
            ..._enabledStrategies.entries
                .map((entry) => SwitchListTile(
                      title: Text(_getReadableStrategyName(entry.key)),
                      value: entry.value,
                      onChanged: (value) {
                        setState(() {
                          _enabledStrategies[entry.key] = value;
                        });
                      },
                    ))
                .toList(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildMarketConditionSection() {
    // Check if market condition detector parameters exist
    final hasMarketCondition = _strategyParameters.containsKey('market_condition_detector') || 
                               _strategyParameters.containsKey('moving_average_cross');
    
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Market Condition Detection',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Configure how the bot detects and responds to market conditions',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 16),
            
            SwitchListTile(
              title: const Text('Enable Market Condition Detection'),
              subtitle: const Text('Automatically adapt to changing market conditions'),
              value: hasMarketCondition,
              onChanged: (value) {
                setState(() {
                  if (value && !hasMarketCondition) {
                    // Add default market condition parameters
                    _strategyParameters['market_condition_detector'] = {
                      'enabled': true,
                      'trend_lookback': 100,
                      'volatility_window': 20,
                      'min_trading_confidence': 0.6,
                    };
                  } else if (!value && hasMarketCondition) {
                    // Remove market condition parameters
                    _strategyParameters.remove('market_condition_detector');
                  }
                });
              },
            ),
            
            if (hasMarketCondition) ...[
              const SizedBox(height: 16),
              
              // Minimum confidence slider
              const Text('Minimum Trading Confidence'),
              Slider(
                value: (_getMarketParam('min_trading_confidence') as double?) ?? 0.6,
                min: 0.1,
                max: 0.9,
                divisions: 8,
                label: '${((_getMarketParam('min_trading_confidence') as double?) ?? 0.6).toStringAsFixed(1)}',
                onChanged: (value) {
                  setState(() {
                    _updateMarketParam('min_trading_confidence', value);
                  });
                },
              ),
              Text('Only trade when market conditions have a confidence of ${((_getMarketParam('min_trading_confidence') as double?) ?? 0.6).toStringAsFixed(1)} or higher'),
              
              const SizedBox(height: 16),
              TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Trend Lookback Period',
                  helperText: 'Number of candles to analyze for trend detection',
                  border: OutlineInputBorder(),
                ),
                initialValue: (_getMarketParam('trend_lookback') as int?)?.toString() ?? '100',
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter a value';
                  }
                  final number = int.tryParse(value);
                  if (number == null) {
                    return 'Please enter a valid number';
                  }
                  if (number < 10 || number > 500) {
                    return 'Please enter a value between 10 and 500';
                  }
                  return null;
                },
                onSaved: (value) {
                  if (value != null) {
                    _updateMarketParam('trend_lookback', int.parse(value));
                  }
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  Widget _buildMultiAssetSection() {
    // Check if multi-asset integrator parameters exist
    final hasMultiAsset = _strategyParameters.containsKey('multi_asset_integrator') ||
                          _strategyParameters.containsKey('correlation_manager');
    
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Multi-Asset Trading',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Configure correlation management and portfolio optimization',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 16),
            
            SwitchListTile(
              title: const Text('Enable Multi-Asset Integration'),
              subtitle: const Text('Optimize trading across multiple assets'),
              value: hasMultiAsset,
              onChanged: (value) {
                setState(() {
                  if (value && !hasMultiAsset) {
                    // Add default multi-asset parameters
                    _strategyParameters['multi_asset_integrator'] = {
                      'enabled': true,
                      'correlation_threshold': 0.7,
                      'max_correlation_exposure': 2,
                    };
                  } else if (!value && hasMultiAsset) {
                    // Remove multi-asset parameters
                    _strategyParameters.remove('multi_asset_integrator');
                    _strategyParameters.remove('correlation_manager');
                  }
                });
              },
            ),
            
            if (hasMultiAsset) ...[
              const SizedBox(height: 16),
              
              // Correlation threshold slider
              const Text('Correlation Threshold'),
              Slider(
                value: (_getMultiAssetParam('correlation_threshold') as double?) ?? 0.7,
                min: 0.5,
                max: 0.95,
                divisions: 9,
                label: '${((_getMultiAssetParam('correlation_threshold') as double?) ?? 0.7).toStringAsFixed(2)}',
                onChanged: (value) {
                  setState(() {
                    _updateMultiAssetParam('correlation_threshold', value);
                  });
                },
              ),
              Text('Assets with correlation above ${((_getMultiAssetParam('correlation_threshold') as double?) ?? 0.7).toStringAsFixed(2)} will be considered correlated'),
              
              const SizedBox(height: 16),
              TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Max Correlated Exposure',
                  helperText: 'Maximum number of correlated assets to trade at once',
                  border: OutlineInputBorder(),
                ),
                initialValue: (_getMultiAssetParam('max_correlation_exposure') as int?)?.toString() ?? '2',
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
                  if (value != null) {
                    _updateMultiAssetParam('max_correlation_exposure', int.parse(value));
                  }
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  Widget _buildStrategyParametersSection() {
    // For simplicity, we'll focus on the most common strategy: Moving Average Cross
    final hasMAStrat = _strategyParameters.containsKey('moving_average_cross');
    
    if (!hasMAStrat || _enabledStrategies['moving_average_cross'] != true) {
      return const SizedBox.shrink();
    }
    
    final maParams = _strategyParameters['moving_average_cross'] as Map<String, dynamic>? ?? {};
    
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Moving Average Cross Strategy',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              decoration: const InputDecoration(
                labelText: 'Fast MA Period',
                helperText: 'Period for the fast moving average',
                border: OutlineInputBorder(),
              ),
              initialValue: maParams['fast_ma_period']?.toString() ?? '5',
              keyboardType: TextInputType.number,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Please enter a value';
                }
                final number = int.tryParse(value);
                if (number == null) {
                  return 'Please enter a valid number';
                }
                if (number < 2 || number > 50) {
                  return 'Please enter a value between 2 and 50';
                }
                return null;
              },
              onSaved: (value) {
                if (value != null) {
                  _updateStrategyParam('moving_average_cross', 'fast_ma_period', int.parse(value));
                }
              },
            ),
            
            const SizedBox(height: 16),
            TextFormField(
              decoration: const InputDecoration(
                labelText: 'Slow MA Period',
                helperText: 'Period for the slow moving average',
                border: OutlineInputBorder(),
              ),
              initialValue: maParams['slow_ma_period']?.toString() ?? '20',
              keyboardType: TextInputType.number,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Please enter a value';
                }
                final number = int.tryParse(value);
                if (number == null) {
                  return 'Please enter a valid number';
                }
                if (number < 5 || number > 200) {
                  return 'Please enter a value between 5 and 200';
                }
                return null;
              },
              onSaved: (value) {
                if (value != null) {
                  _updateStrategyParam('moving_average_cross', 'slow_ma_period', int.parse(value));
                }
              },
            ),
            
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(
                labelText: 'MA Type',
                border: OutlineInputBorder(),
              ),
              value: maParams['ma_type']?.toString() ?? 'ema',
              items: ['sma', 'ema', 'wma', 'hull']
                  .map((type) => DropdownMenuItem(
                        value: type,
                        child: Text(_getMATypeName(type)),
                      ))
                  .toList(),
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _updateStrategyParam('moving_average_cross', 'ma_type', value);
                  });
                }
              },
            ),
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
        child: const Text('Save Strategy Settings'),
      ),
    );
  }
  
  void _saveSettings() {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      
      // Create updated settings
      final updatedSettings = StrategySettings(
        enabledStrategies: _enabledStrategies,
        strategyParameters: _strategyParameters,
      );
      
      // Dispatch update event
      context.read<SettingsBloc>().add(
        UpdateStrategySettings(updatedSettings),
      );
    }
  }
  
  String _getReadableStrategyName(String strategyKey) {
    switch (strategyKey) {
      case 'moving_average_cross':
        return 'Moving Average Cross';
      case 'break_and_retest':
        return 'Break and Retest';
      case 'break_of_structure':
        return 'Break of Structure';
      case 'jhook_pattern':
        return 'J-Hook Pattern';
      case 'ma_rsi_combo':
        return 'MA + RSI Combo';
      case 'stochastic_cross':
        return 'Stochastic Cross';
      default:
        return strategyKey.split('_').map((word) => 
          word.isEmpty ? word : word[0].toUpperCase() + word.substring(1)
        ).join(' ');
    }
  }
  
  String _getMATypeName(String maType) {
    switch (maType) {
      case 'sma':
        return 'Simple Moving Average (SMA)';
      case 'ema':
        return 'Exponential Moving Average (EMA)';
      case 'wma':
        return 'Weighted Moving Average (WMA)';
      case 'hull':
        return 'Hull Moving Average (HMA)';
      default:
        return maType.toUpperCase();
    }
  }
  
  dynamic _getMarketParam(String paramName) {
    if (_strategyParameters.containsKey('market_condition_detector')) {
      return _strategyParameters['market_condition_detector'][paramName];
    }
    return null;
  }
  
  void _updateMarketParam(String paramName, dynamic value) {
    if (!_strategyParameters.containsKey('market_condition_detector')) {
      _strategyParameters['market_condition_detector'] = {
        'enabled': true,
      };
    }
    _strategyParameters['market_condition_detector'][paramName] = value;
  }
  
  dynamic _getMultiAssetParam(String paramName) {
    final params = _strategyParameters.containsKey('multi_asset_integrator')
        ? _strategyParameters['multi_asset_integrator']
        : _strategyParameters.containsKey('correlation_manager')
            ? _strategyParameters['correlation_manager']
            : null;
    
    if (params != null) {
      return params[paramName];
    }
    return null;
  }
  
  void _updateMultiAssetParam(String paramName, dynamic value) {
    final key = _strategyParameters.containsKey('multi_asset_integrator')
        ? 'multi_asset_integrator'
        : 'correlation_manager';
    
    if (!_strategyParameters.containsKey(key)) {
      _strategyParameters[key] = {
        'enabled': true,
      };
    }
    _strategyParameters[key][paramName] = value;
  }
  
  void _updateStrategyParam(String strategy, String paramName, dynamic value) {
    if (!_strategyParameters.containsKey(strategy)) {
      _strategyParameters[strategy] = {};
    }
    _strategyParameters[strategy][paramName] = value;
  }
}
