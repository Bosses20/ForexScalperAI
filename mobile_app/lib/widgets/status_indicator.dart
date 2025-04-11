import 'package:flutter/material.dart';

class StatusIndicator extends StatelessWidget {
  final bool isActive;
  final String label;
  final String? sublabel;
  final Color activeColor;
  final Color inactiveColor;
  final VoidCallback? onTap;

  const StatusIndicator({
    Key? key,
    required this.isActive,
    required this.label,
    this.sublabel,
    this.activeColor = Colors.green,
    this.inactiveColor = Colors.red,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 12.0),
        child: Row(
          children: [
            // Status indicator dot
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                color: isActive ? activeColor : inactiveColor,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: (isActive ? activeColor : inactiveColor).withOpacity(0.4),
                    blurRadius: 4,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            // Status text
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  if (sublabel != null)
                    Text(
                      sublabel!,
                      style: TextStyle(
                        fontSize: 12,
                        color: Theme.of(context).textTheme.bodyMedium?.color?.withOpacity(0.7),
                      ),
                    ),
                ],
              ),
            ),
            // Action icon if tappable
            if (onTap != null)
              const Icon(
                Icons.chevron_right,
                size: 18,
                color: Colors.grey,
              ),
          ],
        ),
      ),
    );
  }
}

class BotStatusIndicator extends StatelessWidget {
  final bool isRunning;
  final String? status;
  final VoidCallback? onTap;

  const BotStatusIndicator({
    Key? key,
    required this.isRunning,
    this.status,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return StatusIndicator(
      isActive: isRunning,
      label: 'Trading Bot',
      sublabel: status ?? (isRunning ? 'Running' : 'Stopped'),
      activeColor: Colors.green,
      inactiveColor: Colors.orange,
      onTap: onTap,
    );
  }
}

class ServerStatusIndicator extends StatelessWidget {
  final bool isConnected;
  final String serverName;
  final String? serverDetails;
  final VoidCallback? onTap;

  const ServerStatusIndicator({
    Key? key,
    required this.isConnected,
    required this.serverName,
    this.serverDetails,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return StatusIndicator(
      isActive: isConnected,
      label: 'Server: $serverName',
      sublabel: serverDetails ?? (isConnected ? 'Connected' : 'Disconnected'),
      activeColor: Colors.blue,
      inactiveColor: Colors.red,
      onTap: onTap,
    );
  }
}

class MarketStatusIndicator extends StatelessWidget {
  final double confidenceScore;
  final String trend;
  final VoidCallback? onTap;

  const MarketStatusIndicator({
    Key? key,
    required this.confidenceScore,
    required this.trend,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    Color statusColor;
    if (confidenceScore >= 70) {
      statusColor = Colors.green;
    } else if (confidenceScore >= 40) {
      statusColor = Colors.orange;
    } else {
      statusColor = Colors.red;
    }

    return StatusIndicator(
      isActive: confidenceScore >= 60,
      label: 'Market Conditions',
      sublabel: '$trend trend - ${confidenceScore.toStringAsFixed(0)}% favorable',
      activeColor: statusColor,
      inactiveColor: Colors.grey,
      onTap: onTap,
    );
  }
}
