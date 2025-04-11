import 'package:flutter/material.dart';
import 'package:mobile_app/models/trading/trading_summary.dart';

class BotControlPanel extends StatelessWidget {
  final bool isLoading;
  final bool isBotRunning;
  final Function(bool) onToggleBot;
  final TradingSummary? tradingSummary;

  const BotControlPanel({
    Key? key,
    required this.isLoading,
    required this.isBotRunning,
    required this.onToggleBot,
    this.tradingSummary,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (isLoading) {
      return _buildSkeletonCard(context);
    }

    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Trading Bot Control',
                  style: theme.textTheme.titleLarge,
                ),
                _buildStatusBadge(context, isBotRunning),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 16),
            
            // Bot Stats
            if (tradingSummary != null) ...[
              Row(
                children: [
                  Expanded(
                    child: _buildStatItem(
                      context,
                      'Active Trades',
                      tradingSummary!.activeTrades.toString(),
                      icon: Icons.sync_alt,
                    ),
                  ),
                  Expanded(
                    child: _buildStatItem(
                      context,
                      'Active Symbols',
                      tradingSummary!.activeSymbols.join(', '),
                      icon: Icons.currency_exchange,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: _buildStatItem(
                      context,
                      'Total Positions',
                      tradingSummary!.totalPositions.toString(),
                      icon: Icons.account_balance,
                    ),
                  ),
                  Expanded(
                    child: _buildStatItem(
                      context,
                      'Running Since',
                      _formatDuration(tradingSummary!.runningTime),
                      icon: Icons.timer,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
            ],

            // Control Buttons
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => onToggleBot(!isBotRunning),
                icon: Icon(isBotRunning ? Icons.stop : Icons.play_arrow),
                label: Text(isBotRunning ? 'STOP BOT' : 'START BOT'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: isBotRunning ? Colors.red : theme.colorScheme.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.spaceBetween,
              children: [
                OutlinedButton.icon(
                  onPressed: isBotRunning ? () {
                    // Would open configuration dialog
                    _showConfigDialog(context);
                  } : null,
                  icon: const Icon(Icons.settings),
                  label: const Text('Configure'),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(150, 40),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () {
                    // Would open symbol selection dialog
                    _showSymbolSelectionDialog(context);
                  },
                  icon: const Icon(Icons.playlist_add),
                  label: const Text('Edit Symbols'),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(150, 40),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBadge(BuildContext context, bool isRunning) {
    final color = isRunning ? Colors.green : Colors.red;
    final text = isRunning ? 'RUNNING' : 'STOPPED';
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            text,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(
    BuildContext context,
    String label,
    String value, {
    required IconData icon,
  }) {
    final theme = Theme.of(context);
    
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: theme.colorScheme.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            icon,
            color: theme.colorScheme.primary,
            size: 20,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.6),
                ),
              ),
              Text(
                value,
                style: theme.textTheme.titleSmall,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    
    if (hours > 24) {
      final days = hours ~/ 24;
      return '$days days';
    } else if (hours > 0) {
      return '$hours hrs $minutes min';
    } else {
      return '$minutes min';
    }
  }

  void _showConfigDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Bot Configuration'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Risk Settings
              const Text(
                'Risk Settings',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              _buildSliderWithLabel(
                context,
                'Risk per trade (%)',
                2.0, // Default value
                0.1,
                10.0,
                (value) {
                  // Update risk per trade
                },
              ),
              _buildSliderWithLabel(
                context,
                'Max daily risk (%)',
                10.0, // Default value
                1.0,
                50.0,
                (value) {
                  // Update max daily risk
                },
              ),
              
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 16),
              
              // Strategy Selection
              const Text(
                'Active Strategies',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              _buildCheckboxWithLabel(
                context,
                'Trend Following',
                true, // Default value
                (value) {
                  // Update strategy selection
                },
              ),
              _buildCheckboxWithLabel(
                context,
                'Breakout',
                true, // Default value
                (value) {
                  // Update strategy selection
                },
              ),
              _buildCheckboxWithLabel(
                context,
                'Mean Reversion',
                false, // Default value
                (value) {
                  // Update strategy selection
                },
              ),
              _buildCheckboxWithLabel(
                context,
                'Momentum',
                false, // Default value
                (value) {
                  // Update strategy selection
                },
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CANCEL'),
          ),
          ElevatedButton(
            onPressed: () {
              // Save configuration
              Navigator.pop(context);
            },
            child: const Text('SAVE'),
          ),
        ],
      ),
    );
  }

  void _showSymbolSelectionDialog(BuildContext context) {
    final availableSymbols = [
      'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCHF', 
      'EURGBP', 'USDCAD', 'XAUUSD', 'BTCUSD', 'Oil'
    ];
    final selectedSymbols = <String>[];
    
    // Default to currently active symbols if we have them
    if (tradingSummary != null) {
      selectedSymbols.addAll(tradingSummary!.activeSymbols);
    }
    
    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('Select Trading Instruments'),
              content: SizedBox(
                width: double.maxFinite,
                child: ListView(
                  shrinkWrap: true,
                  children: availableSymbols.map((symbol) {
                    return CheckboxListTile(
                      title: Text(symbol),
                      value: selectedSymbols.contains(symbol),
                      onChanged: (value) {
                        setState(() {
                          if (value ?? false) {
                            selectedSymbols.add(symbol);
                          } else {
                            selectedSymbols.remove(symbol);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('CANCEL'),
                ),
                ElevatedButton(
                  onPressed: selectedSymbols.isEmpty
                      ? null
                      : () {
                          // Update the bot's active symbols
                          Navigator.pop(context);
                        },
                  child: const Text('APPLY'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Widget _buildSliderWithLabel(
    BuildContext context,
    String label,
    double value,
    double min,
    double max,
    Function(double) onChanged,
  ) {
    return StatefulBuilder(
      builder: (context, setState) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(label),
                Text(
                  value.toStringAsFixed(1),
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            Slider(
              value: value,
              min: min,
              max: max,
              divisions: ((max - min) * 10).toInt(),
              label: value.toStringAsFixed(1),
              onChanged: (newValue) {
                setState(() {
                  value = newValue;
                });
                onChanged(newValue);
              },
            ),
          ],
        );
      },
    );
  }

  Widget _buildCheckboxWithLabel(
    BuildContext context,
    String label,
    bool value,
    Function(bool?) onChanged,
  ) {
    return CheckboxListTile(
      title: Text(label),
      value: value,
      onChanged: onChanged,
      contentPadding: EdgeInsets.zero,
      controlAffinity: ListTileControlAffinity.leading,
      dense: true,
    );
  }

  Widget _buildSkeletonCard(BuildContext context) {
    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildSkeletonBox(150, 24),
                _buildSkeletonBox(80, 24, radius: 16),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 16),
            
            // Stats placeholders
            Row(
              children: [
                Expanded(
                  child: _buildSkeletonStatItem(context),
                ),
                Expanded(
                  child: _buildSkeletonStatItem(context),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildSkeletonStatItem(context),
                ),
                Expanded(
                  child: _buildSkeletonStatItem(context),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // Button placeholders
            _buildSkeletonBox(double.infinity, 48),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildSkeletonBox(double.infinity, 40),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _buildSkeletonBox(double.infinity, 40),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSkeletonStatItem(BuildContext context) {
    return Row(
      children: [
        _buildSkeletonBox(36, 36, radius: 8),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildSkeletonBox(80, 12),
              const SizedBox(height: 4),
              _buildSkeletonBox(60, 16),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSkeletonBox(double width, double height, {double radius = 8}) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: Colors.grey.withOpacity(0.2),
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }
}
