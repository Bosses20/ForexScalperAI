import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../blocs/settings/settings_bloc.dart';
import '../../../blocs/settings/settings_event.dart';
import '../../../models/settings/bot_settings.dart';

class RiskManagementTab extends StatefulWidget {
  final RiskManagementSettings settings;

  const RiskManagementTab({
    Key? key,
    required this.settings,
  }) : super(key: key);

  @override
  State<RiskManagementTab> createState() => _RiskManagementTabState();
}

class _RiskManagementTabState extends State<RiskManagementTab> {
  final _formKey = GlobalKey<FormState>();
  
  late double _maxRiskPerTrade;
  late double _maxDailyRisk;
  late double _maxDrawdownPercent;
  late double _maxOpenTrades;
  late StopLossSettings _stopLoss;
  late TakeProfitSettings _takeProfit;
  
  @override
  void initState() {
    super.initState();
    _initializeFromSettings();
  }
  
  @override
  void didUpdateWidget(RiskManagementTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.settings != widget.settings) {
      _initializeFromSettings();
    }
  }
  
  void _initializeFromSettings() {
    _maxRiskPerTrade = widget.settings.maxRiskPerTrade;
    _maxDailyRisk = widget.settings.maxDailyRisk;
    _maxDrawdownPercent = widget.settings.maxDrawdownPercent;
    _maxOpenTrades = widget.settings.maxOpenTrades;
    _stopLoss = widget.settings.stopLoss;
    _takeProfit = widget.settings.takeProfit;
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
              'Risk Management',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            _buildRiskLimitSection(),
            const SizedBox(height: 24),
            _buildStopLossSection(),
            const SizedBox(height: 24),
            _buildTakeProfitSection(),
            const SizedBox(height: 32),
            _buildSaveButton(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildRiskLimitSection() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Risk Limits',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Set limits on how much of your account the bot can risk',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 16),
            
            // Max Risk Per Trade Slider
            const Text('Maximum Risk Per Trade'),
            Slider(
              value: _maxRiskPerTrade,
              min: 0.001,
              max: 0.05,
              divisions: 49,
              label: '${(_maxRiskPerTrade * 100).toStringAsFixed(1)}%',
              onChanged: (value) {
                setState(() {
                  _maxRiskPerTrade = value;
                });
              },
            ),
            Text('${(_maxRiskPerTrade * 100).toStringAsFixed(1)}% of account balance'),
            const SizedBox(height: 16),
            
            // Max Daily Risk Slider
            const Text('Maximum Daily Risk'),
            Slider(
              value: _maxDailyRisk,
              min: 0.01,
              max: 0.2,
              divisions: 19,
              label: '${(_maxDailyRisk * 100).toStringAsFixed(1)}%',
              onChanged: (value) {
                setState(() {
                  _maxDailyRisk = value;
                });
              },
            ),
            Text('${(_maxDailyRisk * 100).toStringAsFixed(1)}% of account balance'),
            const SizedBox(height: 16),
            
            // Max Drawdown Slider
            const Text('Maximum Drawdown Before Shutdown'),
            Slider(
              value: _maxDrawdownPercent,
              min: 0.05,
              max: 0.5,
              divisions: 45,
              label: '${(_maxDrawdownPercent * 100).toStringAsFixed(1)}%',
              onChanged: (value) {
                setState(() {
                  _maxDrawdownPercent = value;
                });
              },
            ),
            Text('${(_maxDrawdownPercent * 100).toStringAsFixed(1)}% of account balance'),
            const SizedBox(height: 16),
            
            // Max Open Trades
            TextFormField(
              decoration: const InputDecoration(
                labelText: 'Maximum Open Trades',
                helperText: 'Maximum number of trades the bot can have open simultaneously',
                border: OutlineInputBorder(),
              ),
              initialValue: _maxOpenTrades.toString(),
              keyboardType: TextInputType.number,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Please enter a value';
                }
                final number = double.tryParse(value);
                if (number == null) {
                  return 'Please enter a valid number';
                }
                if (number < 1 || number > 50) {
                  return 'Please enter a value between 1 and 50';
                }
                return null;
              },
              onSaved: (value) {
                _maxOpenTrades = double.parse(value!);
              },
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildStopLossSection() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Stop Loss Settings',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Configure how stop losses are calculated to protect your account',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 16),
            
            // Stop Loss Method
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(
                labelText: 'Stop Loss Method',
                border: OutlineInputBorder(),
              ),
              value: _stopLoss.defaultStrategy,
              items: ['fixed', 'atr', 'structure']
                  .map((method) => DropdownMenuItem(
                        value: method,
                        child: Text(_getStopLossMethodName(method)),
                      ))
                  .toList(),
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _stopLoss = _stopLoss.copyWith(defaultStrategy: value);
                  });
                }
              },
            ),
            const SizedBox(height: 16),
            
            // Fixed SL in pips
            if (_stopLoss.defaultStrategy == 'fixed' || _stopLoss.defaultStrategy == 'atr')
              TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Fixed Stop Loss (pips)',
                  helperText: 'Distance from entry in pips',
                  border: OutlineInputBorder(),
                ),
                initialValue: _stopLoss.fixedSlPips.toString(),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter a value';
                  }
                  final number = double.tryParse(value);
                  if (number == null) {
                    return 'Please enter a valid number';
                  }
                  if (number < 1 || number > 200) {
                    return 'Please enter a value between 1 and 200';
                  }
                  return null;
                },
                onSaved: (value) {
                  _stopLoss = _stopLoss.copyWith(
                    fixedSlPips: double.parse(value!),
                  );
                },
              ),
            
            // ATR Multiplier
            if (_stopLoss.defaultStrategy == 'atr')
              Column(
                children: [
                  const SizedBox(height: 16),
                  TextFormField(
                    decoration: const InputDecoration(
                      labelText: 'ATR Multiplier',
                      helperText: 'Multiplier for ATR-based stop loss',
                      border: OutlineInputBorder(),
                    ),
                    initialValue: _stopLoss.atrMultiplier.toString(),
                    keyboardType: TextInputType.number,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter a value';
                      }
                      final number = double.tryParse(value);
                      if (number == null) {
                        return 'Please enter a valid number';
                      }
                      if (number < 0.5 || number > 5) {
                        return 'Please enter a value between 0.5 and 5';
                      }
                      return null;
                    },
                    onSaved: (value) {
                      _stopLoss = _stopLoss.copyWith(
                        atrMultiplier: double.parse(value!),
                      );
                    },
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildTakeProfitSection() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Take Profit Settings',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Configure how profits are taken',
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 16),
            
            // Take Profit Method
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(
                labelText: 'Take Profit Method',
                border: OutlineInputBorder(),
              ),
              value: _takeProfit.method,
              items: ['fixed', 'risk_ratio', 'structure']
                  .map((method) => DropdownMenuItem(
                        value: method,
                        child: Text(_getTakeProfitMethodName(method)),
                      ))
                  .toList(),
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _takeProfit = _takeProfit.copyWith(method: value);
                  });
                }
              },
            ),
            const SizedBox(height: 16),
            
            // Fixed TP in pips
            if (_takeProfit.method == 'fixed')
              TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Fixed Take Profit (pips)',
                  helperText: 'Distance from entry in pips',
                  border: OutlineInputBorder(),
                ),
                initialValue: _takeProfit.fixedTpPips.toString(),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Please enter a value';
                  }
                  final number = double.tryParse(value);
                  if (number == null) {
                    return 'Please enter a valid number';
                  }
                  if (number < 1 || number > 500) {
                    return 'Please enter a value between 1 and 500';
                  }
                  return null;
                },
                onSaved: (value) {
                  _takeProfit = _takeProfit.copyWith(
                    fixedTpPips: double.parse(value!),
                  );
                },
              ),
            
            // Risk Reward Ratio
            if (_takeProfit.method == 'risk_ratio')
              Column(
                children: [
                  const SizedBox(height: 16),
                  TextFormField(
                    decoration: const InputDecoration(
                      labelText: 'Risk-Reward Ratio',
                      helperText: 'Take profit will be set at X times the risk',
                      border: OutlineInputBorder(),
                    ),
                    initialValue: _takeProfit.riskRewardRatio.toString(),
                    keyboardType: TextInputType.number,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter a value';
                      }
                      final number = double.tryParse(value);
                      if (number == null) {
                        return 'Please enter a valid number';
                      }
                      if (number < 0.5 || number > 10) {
                        return 'Please enter a value between 0.5 and 10';
                      }
                      return null;
                    },
                    onSaved: (value) {
                      _takeProfit = _takeProfit.copyWith(
                        riskRewardRatio: double.parse(value!),
                      );
                    },
                  ),
                  
                  // Multiple Take Profit Targets
                  const SizedBox(height: 16),
                  const Text(
                    'Multiple Take Profit Targets',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  SwitchListTile(
                    title: const Text('Use Multiple Take Profit Levels'),
                    subtitle: const Text('Split profit taking into multiple levels'),
                    value: _takeProfit.multipleTargets.containsKey('tp1_ratio'),
                    onChanged: (value) {
                      setState(() {
                        if (value) {
                          _takeProfit = _takeProfit.copyWith(
                            multipleTargets: {
                              'tp1_ratio': 1.0,
                              'tp2_ratio': 2.0,
                              'tp1_size': 0.5,
                            },
                          );
                        } else {
                          _takeProfit = _takeProfit.copyWith(
                            multipleTargets: {},
                          );
                        }
                      });
                    },
                  ),
                  
                  // Multiple TP settings
                  if (_takeProfit.multipleTargets.containsKey('tp1_ratio'))
                    Column(
                      children: [
                        const SizedBox(height: 16),
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'First Take Profit (ratio)',
                            helperText: 'First TP at X times the risk',
                            border: OutlineInputBorder(),
                          ),
                          initialValue: _takeProfit.multipleTargets['tp1_ratio'].toString(),
                          keyboardType: TextInputType.number,
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return 'Please enter a value';
                            }
                            final number = double.tryParse(value);
                            if (number == null) {
                              return 'Please enter a valid number';
                            }
                            if (number < 0.5 || number > 5) {
                              return 'Please enter a value between 0.5 and 5';
                            }
                            return null;
                          },
                          onSaved: (value) {
                            final newTargets = Map<String, double>.from(_takeProfit.multipleTargets);
                            newTargets['tp1_ratio'] = double.parse(value!);
                            _takeProfit = _takeProfit.copyWith(
                              multipleTargets: newTargets,
                            );
                          },
                        ),
                        
                        const SizedBox(height: 16),
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'Second Take Profit (ratio)',
                            helperText: 'Second TP at X times the risk',
                            border: OutlineInputBorder(),
                          ),
                          initialValue: _takeProfit.multipleTargets['tp2_ratio'].toString(),
                          keyboardType: TextInputType.number,
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return 'Please enter a value';
                            }
                            final number = double.tryParse(value);
                            if (number == null) {
                              return 'Please enter a valid number';
                            }
                            if (number < 1 || number > 10) {
                              return 'Please enter a value between 1 and 10';
                            }
                            return null;
                          },
                          onSaved: (value) {
                            final newTargets = Map<String, double>.from(_takeProfit.multipleTargets);
                            newTargets['tp2_ratio'] = double.parse(value!);
                            _takeProfit = _takeProfit.copyWith(
                              multipleTargets: newTargets,
                            );
                          },
                        ),
                        
                        const SizedBox(height: 16),
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'First TP Size (portion)',
                            helperText: 'Portion of position to close at first TP (0-1)',
                            border: OutlineInputBorder(),
                          ),
                          initialValue: _takeProfit.multipleTargets['tp1_size'].toString(),
                          keyboardType: TextInputType.number,
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return 'Please enter a value';
                            }
                            final number = double.tryParse(value);
                            if (number == null) {
                              return 'Please enter a valid number';
                            }
                            if (number <= 0 || number >= 1) {
                              return 'Please enter a value between 0 and 1 (exclusive)';
                            }
                            return null;
                          },
                          onSaved: (value) {
                            final newTargets = Map<String, double>.from(_takeProfit.multipleTargets);
                            newTargets['tp1_size'] = double.parse(value!);
                            _takeProfit = _takeProfit.copyWith(
                              multipleTargets: newTargets,
                            );
                          },
                        ),
                      ],
                    ),
                ],
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
        child: const Text('Save Risk Management Settings'),
      ),
    );
  }
  
  void _saveSettings() {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      
      // Create updated settings
      final updatedSettings = RiskManagementSettings(
        maxRiskPerTrade: _maxRiskPerTrade,
        maxDailyRisk: _maxDailyRisk,
        maxDrawdownPercent: _maxDrawdownPercent,
        maxOpenTrades: _maxOpenTrades,
        stopLoss: _stopLoss,
        takeProfit: _takeProfit,
      );
      
      // Dispatch update event
      context.read<SettingsBloc>().add(
        UpdateRiskManagementSettings(updatedSettings),
      );
    }
  }
  
  String _getStopLossMethodName(String method) {
    switch (method) {
      case 'fixed':
        return 'Fixed (pips)';
      case 'atr':
        return 'ATR-based';
      case 'structure':
        return 'Market Structure';
      default:
        return method;
    }
  }
  
  String _getTakeProfitMethodName(String method) {
    switch (method) {
      case 'fixed':
        return 'Fixed (pips)';
      case 'risk_ratio':
        return 'Risk/Reward Ratio';
      case 'structure':
        return 'Market Structure';
      default:
        return method;
    }
  }
}
