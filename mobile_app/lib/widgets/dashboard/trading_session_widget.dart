import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:mobile_app/theme/app_theme.dart';

class TradingSessionWidget extends StatelessWidget {
  final List<TradingSession> activeSessions;
  final List<TradingSession> upcomingSessions;
  final Map<String, List<String>> recommendedInstruments;

  const TradingSessionWidget({
    Key? key,
    required this.activeSessions,
    required this.upcomingSessions,
    required this.recommendedInstruments,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      elevation: 2,
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
                  'Trading Sessions',
                  style: theme.textTheme.titleMedium,
                ),
                _buildLocalTimeWidget(context),
              ],
            ),
            const SizedBox(height: 16),
            _buildSessionTimeline(context),
            const SizedBox(height: 16),
            _buildActiveSessionsList(context),
            if (upcomingSessions.isNotEmpty) ...[
              const SizedBox(height: 12),
              _buildUpcomingSessionsList(context),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildLocalTimeWidget(BuildContext context) {
    final theme = Theme.of(context);
    final currentTime = DateTime.now();
    final timeFormat = DateFormat('HH:mm');
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.access_time,
            size: 16,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(width: 4),
          Text(
            timeFormat.format(currentTime),
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.primary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSessionTimeline(BuildContext context) {
    final theme = Theme.of(context);
    
    // Generate 24-hour timeline
    final currentHour = DateTime.now().hour;
    
    return SizedBox(
      height: 60,
      child: Row(
        children: List.generate(24, (hour) {
          final isActive = _isHourInActiveSessions(hour);
          final isUpcoming = _isHourInUpcomingSessions(hour);
          final isCurrent = hour == currentHour;
          
          return Expanded(
            child: Column(
              children: [
                // Hour label (show every 3 hours)
                if (hour % 3 == 0)
                  Text(
                    hour.toString().padLeft(2, '0'),
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontSize: 10,
                      color: isCurrent ? theme.colorScheme.primary : null,
                    ),
                  )
                else
                  SizedBox(height: theme.textTheme.bodySmall?.fontSize ?? 10),
                const SizedBox(height: 4),
                // Hour indicator
                Container(
                  height: 24,
                  width: double.infinity,
                  margin: const EdgeInsets.symmetric(horizontal: 1),
                  decoration: BoxDecoration(
                    color: isActive
                        ? theme.colorScheme.primary
                        : isUpcoming
                            ? theme.colorScheme.primary.withOpacity(0.3)
                            : theme.colorScheme.surface,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: isCurrent
                          ? theme.colorScheme.primary
                          : theme.colorScheme.primary.withOpacity(0.1),
                      width: isCurrent ? 2 : 1,
                    ),
                  ),
                  child: isCurrent
                      ? Center(
                          child: Container(
                            width: 4,
                            height: 12,
                            decoration: BoxDecoration(
                              color: isActive
                                  ? theme.colorScheme.onPrimary
                                  : theme.colorScheme.primary,
                              borderRadius: BorderRadius.circular(2),
                            ),
                          ),
                        )
                      : null,
                ),
                const SizedBox(height: 4),
                // Session label
                if (hour % 8 == 0) _buildSessionLabel(context, hour)
              ],
            ),
          );
        }),
      ),
    );
  }

  Widget _buildSessionLabel(BuildContext context, int hour) {
    final theme = Theme.of(context);
    String label = '';
    
    if (hour == 0) label = 'Sydney';
    if (hour == 8) label = 'London';
    if (hour == 16) label = 'New York';
    
    return Text(
      label,
      style: theme.textTheme.bodySmall?.copyWith(
        fontSize: 9,
        fontWeight: FontWeight.bold,
      ),
    );
  }

  Widget _buildActiveSessionsList(BuildContext context) {
    final theme = Theme.of(context);
    
    if (activeSessions.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: theme.colorScheme.outline.withOpacity(0.5)),
        ),
        child: Row(
          children: [
            Icon(
              Icons.info_outline,
              color: theme.colorScheme.onSurface.withOpacity(0.5),
              size: 18,
            ),
            const SizedBox(width: 8),
            Text(
              'No active trading sessions',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.7),
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: theme.colorScheme.primary,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              'Active Sessions',
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ...activeSessions.map((session) => _buildSessionItem(context, session, true)),
      ],
    );
  }

  Widget _buildUpcomingSessionsList(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withOpacity(0.3),
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              'Upcoming Sessions',
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ...upcomingSessions
            .take(2) // Show only next 2 upcoming sessions
            .map((session) => _buildSessionItem(context, session, false)),
      ],
    );
  }

  Widget _buildSessionItem(BuildContext context, TradingSession session, bool isActive) {
    final theme = Theme.of(context);
    final timeFormat = DateFormat('HH:mm');
    
    // Get recommended instruments for this session
    final sessionInstruments = recommendedInstruments[session.name] ?? [];
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isActive 
              ? theme.colorScheme.primary.withOpacity(0.1)
              : theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isActive
                ? theme.colorScheme.primary.withOpacity(0.3)
                : theme.colorScheme.outline.withOpacity(0.2),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(
                      _getSessionIcon(session.name),
                      color: isActive 
                          ? theme.colorScheme.primary
                          : theme.colorScheme.onSurface.withOpacity(0.6),
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      session.name,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: isActive
                            ? theme.colorScheme.primary
                            : theme.colorScheme.onSurface,
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (isActive && session.isOverlap)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.warningColor.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          'Overlap',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: AppTheme.warningColor,
                            fontWeight: FontWeight.bold,
                            fontSize: 10,
                          ),
                        ),
                      ),
                  ],
                ),
                Text(
                  '${timeFormat.format(session.startTime)} - ${timeFormat.format(session.endTime)}',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
            if (sessionInstruments.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: sessionInstruments.map((instrument) {
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: isActive
                          ? theme.colorScheme.primaryContainer.withOpacity(0.2)
                          : theme.colorScheme.surface,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: isActive
                            ? theme.colorScheme.primaryContainer.withOpacity(0.6)
                            : theme.colorScheme.outline.withOpacity(0.3),
                      ),
                    ),
                    child: Text(
                      instrument,
                      style: theme.textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: isActive
                            ? theme.colorScheme.primaryContainer
                            : theme.colorScheme.onSurface.withOpacity(0.7),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
            if (!isActive) ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  Icon(
                    Icons.schedule,
                    size: 14,
                    color: theme.colorScheme.onSurface.withOpacity(0.5),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    _formatTimeUntil(session.startTime),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.7),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  bool _isHourInActiveSessions(int hour) {
    for (final session in activeSessions) {
      final startHour = session.startTime.hour;
      final endHour = session.endTime.hour;
      
      if (startHour <= endHour) {
        // Session doesn't cross midnight
        if (hour >= startHour && hour < endHour) {
          return true;
        }
      } else {
        // Session crosses midnight
        if (hour >= startHour || hour < endHour) {
          return true;
        }
      }
    }
    return false;
  }

  bool _isHourInUpcomingSessions(int hour) {
    for (final session in upcomingSessions) {
      final startHour = session.startTime.hour;
      final endHour = session.endTime.hour;
      
      if (startHour <= endHour) {
        // Session doesn't cross midnight
        if (hour >= startHour && hour < endHour) {
          return true;
        }
      } else {
        // Session crosses midnight
        if (hour >= startHour || hour < endHour) {
          return true;
        }
      }
    }
    return false;
  }

  IconData _getSessionIcon(String sessionName) {
    switch (sessionName.toLowerCase()) {
      case 'asian session':
      case 'tokyo':
      case 'sydney':
        return Icons.wb_twilight;
      case 'london session':
      case 'european session':
        return Icons.account_balance;
      case 'new york session':
      case 'us session':
        return Icons.location_city;
      default:
        return Icons.public;
    }
  }

  String _formatTimeUntil(DateTime time) {
    final now = DateTime.now();
    final todayTargetTime = DateTime(
      now.year,
      now.month,
      now.day,
      time.hour,
      time.minute,
    );
    
    final targetTime = todayTargetTime.isBefore(now)
        ? todayTargetTime.add(const Duration(days: 1))
        : todayTargetTime;
    
    final difference = targetTime.difference(now);
    
    if (difference.inHours > 0) {
      return 'Starts in ${difference.inHours}h ${difference.inMinutes % 60}m';
    } else {
      return 'Starts in ${difference.inMinutes}m';
    }
  }
}

/// Model representing a trading session (e.g., Asian, London, New York)
class TradingSession {
  final String name;
  final DateTime startTime;
  final DateTime endTime;
  final bool isOverlap;
  final List<String> favorableInstruments;
  final String liquidityLevel;

  const TradingSession({
    required this.name,
    required this.startTime,
    required this.endTime,
    this.isOverlap = false,
    this.favorableInstruments = const [],
    this.liquidityLevel = 'Medium',
  });

  /// Creates a TradingSession from a JSON object
  factory TradingSession.fromJson(Map<String, dynamic> json) {
    return TradingSession(
      name: json['name'] ?? '',
      startTime: json['start_time'] != null
          ? DateTime.parse(json['start_time'])
          : DateTime.now(),
      endTime: json['end_time'] != null
          ? DateTime.parse(json['end_time'])
          : DateTime.now().add(const Duration(hours: 1)),
      isOverlap: json['is_overlap'] ?? false,
      favorableInstruments: json['favorable_instruments'] != null
          ? List<String>.from(json['favorable_instruments'])
          : [],
      liquidityLevel: json['liquidity_level'] ?? 'Medium',
    );
  }

  /// Checks if this session is currently active
  bool isActive() {
    final now = DateTime.now();
    final currentHour = now.hour;
    final startHour = startTime.hour;
    final endHour = endTime.hour;
    
    if (startHour < endHour) {
      // Session doesn't cross midnight
      return currentHour >= startHour && currentHour < endHour;
    } else {
      // Session crosses midnight
      return currentHour >= startHour || currentHour < endHour;
    }
  }
}
