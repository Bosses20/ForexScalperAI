import 'package:flutter/material.dart';
import 'package:mobile_app/models/trading/trading_instrument.dart';

class TradingInstrumentCard extends StatelessWidget {
  final TradingInstrument instrument;
  final VoidCallback? onTap;

  const TradingInstrumentCard({
    Key? key,
    required this.instrument,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isActive = instrument.isActive;
    
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12.0),
        side: BorderSide(
          color: isActive ? theme.colorScheme.primary : Colors.transparent,
          width: isActive ? 2.0 : 0.0,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12.0),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      _buildInstrumentIcon(context, instrument.type),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            instrument.symbol,
                            style: theme.textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            _getInstrumentTypeLabel(instrument.type),
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurface.withOpacity(0.6),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  _buildStatusIndicator(context, isActive),
                ],
              ),
              const SizedBox(height: 16),
              
              // Trading metrics
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _buildMetricItem(
                    context,
                    'Spread',
                    '${instrument.spread.toStringAsFixed(1)} pts',
                    color: _getSpreadColor(context, instrument.spread),
                  ),
                  _buildMetricItem(
                    context,
                    'Win Rate',
                    '${(instrument.winRate * 100).toStringAsFixed(0)}%',
                    color: _getWinRateColor(context, instrument.winRate),
                  ),
                  _buildMetricItem(
                    context,
                    'Performance',
                    instrument.performanceScore.toStringAsFixed(1),
                    color: _getPerformanceColor(context, instrument.performanceScore),
                  ),
                ],
              ),
              
              const SizedBox(height: 16),
              const Divider(),
              
              // Active sessions
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Active Sessions',
                    style: theme.textTheme.titleSmall,
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _buildSessionChips(context, instrument.activeSessions),
                  ),
                ],
              ),
              
              const SizedBox(height: 16),
              
              // Strategy compatibility
              if (instrument.compatibleStrategies.isNotEmpty) ...[
                Text(
                  'Compatible Strategies',
                  style: theme.textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: instrument.compatibleStrategies.map((strategy) => Chip(
                    label: Text(
                      strategy,
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.onSecondaryContainer,
                      ),
                    ),
                    backgroundColor: theme.colorScheme.secondaryContainer,
                    padding: const EdgeInsets.all(4),
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  )).toList(),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInstrumentIcon(BuildContext context, String type) {
    final color = Theme.of(context).colorScheme.primary;
    IconData iconData;
    
    switch (type.toLowerCase()) {
      case 'forex':
        iconData = Icons.currency_exchange;
        break;
      case 'indices':
        iconData = Icons.insert_chart;
        break;
      case 'commodities':
        iconData = Icons.oil_barrel;
        break;
      case 'crypto':
        iconData = Icons.currency_bitcoin;
        break;
      case 'stocks':
        iconData = Icons.business;
        break;
      default:
        iconData = Icons.show_chart;
    }
    
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(
        iconData,
        color: color,
      ),
    );
  }

  Widget _buildStatusIndicator(BuildContext context, bool isActive) {
    final theme = Theme.of(context);
    final color = isActive ? theme.colorScheme.primary : theme.disabledColor;
    final text = isActive ? 'Active' : 'Inactive';
    
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

  Widget _buildMetricItem(
    BuildContext context,
    String label,
    String value, {
    Color? color,
  }) {
    return Column(
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  List<Widget> _buildSessionChips(BuildContext context, List<String> sessions) {
    final theme = Theme.of(context);
    final colors = {
      'asian': Colors.purple,
      'london': Colors.blue,
      'new york': Colors.green,
      'sydney': Colors.orange,
      'tokyo': Colors.red,
    };
    
    return sessions.map((session) {
      final lowerSession = session.toLowerCase();
      final color = colors[lowerSession] ?? theme.colorScheme.primary;
      
      return Chip(
        label: Text(
          session,
          style: TextStyle(
            fontSize: 12,
            color: theme.brightness == Brightness.dark ? Colors.white : Colors.black87,
          ),
        ),
        backgroundColor: color.withOpacity(0.2),
        side: BorderSide(color: color.withOpacity(0.5)),
        padding: const EdgeInsets.all(4),
        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      );
    }).toList();
  }

  Color _getSpreadColor(BuildContext context, double spread) {
    // Lower spreads are better
    if (spread < 1.0) {
      return Colors.green;
    } else if (spread < 3.0) {
      return Colors.orange;
    } else {
      return Colors.red;
    }
  }

  Color _getWinRateColor(BuildContext context, double winRate) {
    if (winRate >= 0.6) {
      return Colors.green;
    } else if (winRate >= 0.5) {
      return Colors.orange;
    } else {
      return Colors.red;
    }
  }

  Color _getPerformanceColor(BuildContext context, double performance) {
    if (performance >= 7.0) {
      return Colors.green;
    } else if (performance >= 5.0) {
      return Colors.orange;
    } else {
      return Colors.red;
    }
  }

  String _getInstrumentTypeLabel(String type) {
    switch (type.toLowerCase()) {
      case 'forex':
        return 'Forex Currency Pair';
      case 'indices':
        return 'Stock Index';
      case 'commodities':
        return 'Commodity';
      case 'crypto':
        return 'Cryptocurrency';
      case 'stocks':
        return 'Stock';
      default:
        return type;
    }
  }
}
