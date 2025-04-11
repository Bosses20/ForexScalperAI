import 'package:flutter/material.dart';
import 'package:mobile_app/models/trading/trading_instrument.dart';
import 'package:mobile_app/models/trading/correlation_data.dart';

class CorrelationMatrix extends StatelessWidget {
  final List<TradingInstrument> instruments;
  final Map<String, Map<String, double>>? correlationData;

  const CorrelationMatrix({
    Key? key,
    required this.instruments,
    this.correlationData,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (correlationData == null || instruments.isEmpty) {
      return _buildEmptyState(context);
    }

    // Filter to only include active instruments
    final activeInstruments = instruments
        .where((instrument) => instrument.isActive)
        .toList();

    if (activeInstruments.isEmpty) {
      return _buildEmptyState(context, message: 'No active instruments to display correlation data');
    }

    final symbols = activeInstruments.map((e) => e.symbol).toList();

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Correlation Heatmap',
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'The correlation matrix shows the relationship between different trading instruments. Values range from -1 (perfectly negatively correlated) to +1 (perfectly positively correlated).',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
            const SizedBox(height: 16),
            _buildMatrixLegend(context),
            const SizedBox(height: 16),
            _buildMatrix(context, symbols),
          ],
        ),
      ),
    );
  }

  Widget _buildMatrix(BuildContext context, List<String> symbols) {
    final theme = Theme.of(context);
    final cellSize = 60.0;
    final cellPadding = 2.0;

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: SizedBox(
        width: (symbols.length + 1) * (cellSize + cellPadding * 2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                // Empty top-left cell
                SizedBox(
                  width: cellSize + cellPadding * 2,
                  height: cellSize + cellPadding * 2,
                ),
                // Symbol headers
                ...symbols.map((symbol) {
                  return Padding(
                    padding: EdgeInsets.all(cellPadding),
                    child: SizedBox(
                      width: cellSize,
                      height: cellSize,
                      child: Center(
                        child: RotationTransition(
                          turns: const AlwaysStoppedAnimation(-45 / 360),
                          child: Padding(
                            padding: const EdgeInsets.only(right: 12.0),
                            child: Text(
                              symbol,
                              style: theme.textTheme.bodySmall?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }),
              ],
            ),
            // Data rows
            ...symbols.asMap().entries.map((rowEntry) {
              final rowSymbol = rowEntry.value;
              final rowIndex = rowEntry.key;

              return Row(
                children: [
                  // Row headers
                  Padding(
                    padding: EdgeInsets.all(cellPadding),
                    child: SizedBox(
                      width: cellSize,
                      height: cellSize,
                      child: Center(
                        child: Text(
                          rowSymbol,
                          style: theme.textTheme.bodySmall?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                  ),
                  // Correlation cells
                  ...symbols.asMap().entries.map((colEntry) {
                    final colSymbol = colEntry.value;
                    final colIndex = colEntry.key;

                    // Get correlation value
                    double correlationValue = 0.0;
                    if (rowSymbol == colSymbol) {
                      correlationValue = 1.0; // Perfect correlation with self
                    } else if (correlationData!.containsKey(rowSymbol) &&
                        correlationData![rowSymbol]!.containsKey(colSymbol)) {
                      correlationValue = correlationData![rowSymbol]![colSymbol]!;
                    } else if (correlationData!.containsKey(colSymbol) &&
                        correlationData![colSymbol]!.containsKey(rowSymbol)) {
                      correlationValue = correlationData![colSymbol]![rowSymbol]!;
                    }

                    return Padding(
                      padding: EdgeInsets.all(cellPadding),
                      child: SizedBox(
                        width: cellSize,
                        height: cellSize,
                        child: _buildCorrelationCell(
                          context,
                          correlationValue,
                          isHighlighted: rowIndex == colIndex,
                        ),
                      ),
                    );
                  }),
                ],
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildCorrelationCell(
    BuildContext context,
    double value,
    {bool isHighlighted = false}
  ) {
    final theme = Theme.of(context);
    final color = _getCorrelationColor(value);
    final textColor = value.abs() > 0.7
        ? Colors.white
        : theme.colorScheme.onSurface;

    return Material(
      color: color,
      borderRadius: BorderRadius.circular(8),
      elevation: isHighlighted ? 4 : 0,
      child: Container(
        decoration: BoxDecoration(
          border: isHighlighted
              ? Border.all(
                  color: theme.colorScheme.primary,
                  width: 2,
                )
              : null,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Center(
          child: Text(
            value.toStringAsFixed(2),
            style: theme.textTheme.bodySmall?.copyWith(
              color: textColor,
              fontWeight: isHighlighted ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMatrixLegend(BuildContext context) {
    final theme = Theme.of(context);
    final legendValues = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0];
    
    return Row(
      children: [
        Text(
          'Negative',
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Container(
            height: 24,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(4),
              gradient: LinearGradient(
                colors: [
                  _getCorrelationColor(-1.0),
                  _getCorrelationColor(-0.5),
                  _getCorrelationColor(0.0),
                  _getCorrelationColor(0.5),
                  _getCorrelationColor(1.0),
                ],
                stops: const [0.0, 0.25, 0.5, 0.75, 1.0],
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: legendValues.map((value) {
                return SizedBox(
                  width: 20,
                  child: Center(
                    child: Text(
                      value == 0 ? '0' : value.toStringAsFixed(1),
                      style: theme.textTheme.bodySmall?.copyWith(
                        fontSize: 10,
                        color: value.abs() > 0.5 ? Colors.white : Colors.black,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          'Positive',
          style: theme.textTheme.bodySmall,
        ),
      ],
    );
  }

  Widget _buildEmptyState(BuildContext context, {String? message}) {
    final theme = Theme.of(context);
    
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.scatter_plot_outlined,
                size: 48,
                color: theme.colorScheme.onSurface.withOpacity(0.3),
              ),
              const SizedBox(height: 16),
              Text(
                message ?? 'No correlation data available',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.7),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Select at least two active trading instruments',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.5),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getCorrelationColor(double value) {
    // Map correlation value [-1, 1] to a color
    if (value >= 0.9) return Colors.red[900]!;
    if (value >= 0.7) return Colors.red[700]!;
    if (value >= 0.5) return Colors.red[500]!;
    if (value >= 0.3) return Colors.red[300]!;
    if (value >= 0.1) return Colors.red[100]!;
    if (value > -0.1) return Colors.grey[300]!;
    if (value > -0.3) return Colors.blue[100]!;
    if (value > -0.5) return Colors.blue[300]!;
    if (value > -0.7) return Colors.blue[500]!;
    if (value > -0.9) return Colors.blue[700]!;
    return Colors.blue[900]!;
  }
}
