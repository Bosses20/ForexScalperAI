import 'package:flutter/material.dart';
import '../../models/trading_model.dart';
import '../charts/mini_sparkline.dart';

class ActiveAssetsCard extends StatelessWidget {
  final List<TradingInstrument> activeAssets;
  final Function(String, bool) onAssetToggled;

  const ActiveAssetsCard({
    Key? key,
    required this.activeAssets,
    required this.onAssetToggled,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12.0),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Active Trading Assets',
                  style: theme.textTheme.titleLarge,
                ),
                TextButton.icon(
                  icon: const Icon(Icons.add),
                  label: const Text('Add'),
                  onPressed: () {
                    // Navigate to asset management screen
                    Navigator.pushNamed(context, '/assets');
                  },
                ),
              ],
            ),
            const Divider(),
            
            // Asset list
            if (activeAssets.isEmpty)
              _buildEmptyState(context)
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: activeAssets.length,
                separatorBuilder: (context, index) => const Divider(height: 1),
                itemBuilder: (context, index) => _buildAssetItem(
                  context,
                  activeAssets[index],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);
    
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 32.0),
      alignment: Alignment.center,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.currency_exchange,
            size: 48,
            color: theme.colorScheme.primary.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'No active trading assets',
            style: theme.textTheme.titleMedium!.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.7),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Add assets to start trading',
            style: theme.textTheme.bodyMedium!.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.5),
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('Add Assets'),
            onPressed: () {
              // Navigate to asset management screen
              Navigator.pushNamed(context, '/assets');
            },
          ),
        ],
      ),
    );
  }

  Widget _buildAssetItem(BuildContext context, TradingInstrument asset) {
    final theme = Theme.of(context);
    final priceColor = asset.isPriceGoingUp
        ? const Color(0xFF00C853)
        : const Color(0xFFFF3D00);
    
    return InkWell(
      onTap: () {
        // Navigate to asset detail view
        Navigator.pushNamed(
          context,
          '/assets/details',
          arguments: asset,
        );
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12.0),
        child: Row(
          children: [
            // Instrument icon based on type
            _buildAssetTypeIcon(asset),
            const SizedBox(width: 12),
            
            // Symbol and name
            Expanded(
              flex: 3,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    asset.symbol,
                    style: theme.textTheme.titleMedium!.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    asset.displayName,
                    style: theme.textTheme.bodySmall!.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.6),
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (asset.sessionStatus != null)
                    _buildSessionStatusChip(context, asset.sessionStatus!),
                ],
              ),
            ),
            
            // Price information
            Expanded(
              flex: 2,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  if (asset.currentPrice != null)
                    Text(
                      _formatPrice(asset.currentPrice!, asset.decimalPlaces ?? 5),
                      style: theme.textTheme.titleMedium!.copyWith(
                        fontWeight: FontWeight.bold,
                        fontFamily: 'Roboto Mono',
                      ),
                    ),
                  if (asset.dailyChangePercent != null)
                    Text(
                      asset.dailyChangePercent! >= 0
                          ? '+${asset.dailyChangePercent!.toStringAsFixed(2)}%'
                          : '${asset.dailyChangePercent!.toStringAsFixed(2)}%',
                      style: theme.textTheme.bodyMedium!.copyWith(
                        color: priceColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                ],
              ),
            ),
            
            // Mini sparkline chart
            if (asset.recentPrices != null && asset.recentPrices!.isNotEmpty)
              SizedBox(
                width: 60,
                height: 30,
                child: MiniSparkline(
                  data: asset.recentPrices!,
                  lineColor: priceColor,
                  fillColor: priceColor.withOpacity(0.2),
                ),
              )
            else
              const SizedBox(width: 60),
            
            // Toggle switch
            Switch(
              value: asset.isActive,
              onChanged: (value) => onAssetToggled(asset.symbol, value),
              activeColor: theme.colorScheme.primary,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAssetTypeIcon(TradingInstrument asset) {
    final Color backgroundColor;
    final IconData iconData;
    
    // Set icon and color based on asset type
    switch (asset.type.toLowerCase()) {
      case 'forex':
        backgroundColor = Colors.blue;
        iconData = Icons.currency_exchange;
        break;
      case 'synthetic':
        backgroundColor = Colors.purple;
        iconData = Icons.auto_graph;
        break;
      case 'crypto':
        backgroundColor = Colors.orange;
        iconData = Icons.currency_bitcoin;
        break;
      case 'commodity':
        backgroundColor = Colors.amber;
        iconData = Icons.monetization_on;
        break;
      case 'stock':
        backgroundColor = Colors.green;
        iconData = Icons.trending_up;
        break;
      default:
        backgroundColor = Colors.grey;
        iconData = Icons.show_chart;
    }
    
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: backgroundColor.withOpacity(0.2),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: backgroundColor, width: 1),
      ),
      child: Icon(
        iconData,
        color: backgroundColor,
        size: 20,
      ),
    );
  }

  Widget _buildSessionStatusChip(BuildContext context, String status) {
    final theme = Theme.of(context);
    
    final Color backgroundColor;
    final Color textColor;
    
    switch (status.toLowerCase()) {
      case 'open':
        backgroundColor = Colors.green.withOpacity(0.2);
        textColor = Colors.green;
        break;
      case 'closed':
        backgroundColor = Colors.red.withOpacity(0.2);
        textColor = Colors.red;
        break;
      case 'pre-market':
      case 'post-market':
        backgroundColor = Colors.orange.withOpacity(0.2);
        textColor = Colors.orange;
        break;
      default:
        backgroundColor = Colors.grey.withOpacity(0.2);
        textColor = Colors.grey;
    }
    
    return Container(
      margin: const EdgeInsets.only(top: 4),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        status,
        style: theme.textTheme.bodySmall!.copyWith(
          color: textColor,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  String _formatPrice(double price, int decimalPlaces) {
    return price.toStringAsFixed(decimalPlaces);
  }
}

class ActiveAssetsCardSkeleton extends StatelessWidget {
  const ActiveAssetsCardSkeleton({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12.0),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildSkeletonBox(160, 24),
                _buildSkeletonBox(80, 36),
              ],
            ),
            const Divider(),
            
            // Skeleton items
            for (int i = 0; i < 3; i++) ...[
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12.0),
                child: Row(
                  children: [
                    _buildSkeletonBox(40, 40, radius: 8),
                    const SizedBox(width: 12),
                    
                    Expanded(
                      flex: 3,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildSkeletonBox(80, 20),
                          const SizedBox(height: 4),
                          _buildSkeletonBox(120, 16),
                          const SizedBox(height: 4),
                          _buildSkeletonBox(60, 20, radius: 4),
                        ],
                      ),
                    ),
                    
                    Expanded(
                      flex: 2,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          _buildSkeletonBox(70, 20),
                          const SizedBox(height: 4),
                          _buildSkeletonBox(50, 16),
                        ],
                      ),
                    ),
                    
                    const SizedBox(width: 8),
                    _buildSkeletonBox(60, 30),
                    const SizedBox(width: 8),
                    _buildSkeletonBox(40, 24, radius: 12),
                  ],
                ),
              ),
              if (i < 2) const Divider(height: 1),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSkeletonBox(double width, double height, {double radius = 4}) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: Colors.grey[300],
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }
}
