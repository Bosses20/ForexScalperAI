import 'package:flutter/material.dart';
import 'package:mobile_app/models/account/account_info.dart';

class AccountSummaryWidget extends StatelessWidget {
  final bool isLoading;
  final AccountInfo? accountInfo;

  const AccountSummaryWidget({
    Key? key,
    required this.isLoading,
    this.accountInfo,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (isLoading) {
      return _buildSkeletonCard(context);
    }

    if (accountInfo == null) {
      return Card(
        elevation: 3,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: const Padding(
          padding: EdgeInsets.all(16.0),
          child: Center(
            child: Text('Account information not available'),
          ),
        ),
      );
    }

    // Calculate daily change percentage
    final dailyChangePercent = accountInfo!.equity > 0
        ? (accountInfo!.dailyProfitLoss / accountInfo!.equity) * 100
        : 0.0;

    // Determine color based on profit/loss
    final profitLossColor = accountInfo!.dailyProfitLoss >= 0
        ? Colors.green
        : Colors.red;

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
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Account Summary',
                      style: theme.textTheme.titleLarge,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${accountInfo!.login} - ${accountInfo!.server}',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withOpacity(0.6),
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    accountInfo!.currency,
                    style: TextStyle(
                      color: theme.colorScheme.primary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: _buildBalanceSection(
                    context,
                    'Balance',
                    accountInfo!.balance,
                    accountInfo!.currency,
                  ),
                ),
                Expanded(
                  child: _buildBalanceSection(
                    context,
                    'Equity',
                    accountInfo!.equity,
                    accountInfo!.currency,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Margin Level',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      const SizedBox(height: 4),
                      _buildMarginLevelIndicator(context, accountInfo!.marginLevel),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Daily Profit/Loss',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Text(
                            _formatCurrency(accountInfo!.dailyProfitLoss, accountInfo!.currency),
                            style: theme.textTheme.titleMedium?.copyWith(
                              color: profitLossColor,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: profitLossColor.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              '${dailyChangePercent >= 0 ? '+' : ''}${dailyChangePercent.toStringAsFixed(2)}%',
                              style: TextStyle(
                                color: profitLossColor,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildMetricItem(
                    context,
                    'Free Margin',
                    _formatCurrency(accountInfo!.freeMargin, accountInfo!.currency),
                  ),
                ),
                Expanded(
                  child: _buildMetricItem(
                    context,
                    'Used Margin',
                    _formatCurrency(accountInfo!.margin, accountInfo!.currency),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBalanceSection(
    BuildContext context,
    String label,
    double value,
    String currency,
  ) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.6),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          _formatCurrency(value, currency),
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildMetricItem(
    BuildContext context,
    String label,
    String value,
  ) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.6),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: theme.textTheme.titleMedium,
        ),
      ],
    );
  }

  Widget _buildMarginLevelIndicator(BuildContext context, double marginLevel) {
    final theme = Theme.of(context);
    
    Color color;
    String status;
    
    if (marginLevel >= 500) {
      color = Colors.green;
      status = 'Excellent';
    } else if (marginLevel >= 200) {
      color = Colors.lightGreen;
      status = 'Good';
    } else if (marginLevel >= 100) {
      color = Colors.orange;
      status = 'Adequate';
    } else {
      color = Colors.red;
      status = 'Warning';
    }
    
    return Row(
      children: [
        Text(
          '${marginLevel.toStringAsFixed(0)}%',
          style: theme.textTheme.titleMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: 8,
            vertical: 2,
          ),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: color.withOpacity(0.5)),
          ),
          child: Text(
            status,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }

  String _formatCurrency(double value, String currency) {
    return '${value >= 0 ? '' : '-'}$currency ${value.abs().toStringAsFixed(2)}';
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
                _buildSkeletonBox(120, 24),
                _buildSkeletonBox(60, 24, radius: 20),
              ],
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(60, 14),
                      const SizedBox(height: 8),
                      _buildSkeletonBox(100, 28),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(60, 14),
                      const SizedBox(height: 8),
                      _buildSkeletonBox(100, 28),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(80, 14),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          _buildSkeletonBox(60, 24),
                          const SizedBox(width: 8),
                          _buildSkeletonBox(40, 20, radius: 4),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(100, 14),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          _buildSkeletonBox(60, 24),
                          const SizedBox(width: 8),
                          _buildSkeletonBox(40, 20, radius: 4),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(80, 14),
                      const SizedBox(height: 8),
                      _buildSkeletonBox(80, 20),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSkeletonBox(80, 14),
                      const SizedBox(height: 8),
                      _buildSkeletonBox(80, 20),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
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
