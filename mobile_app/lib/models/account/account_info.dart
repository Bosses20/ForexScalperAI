import 'package:equatable/equatable.dart';

/// Model representing the MT5 trading account information.
class AccountInfo extends Equatable {
  /// MT5 account login number.
  final int login;
  
  /// MT5 broker server name.
  final String server;
  
  /// Account balance (not including open positions).
  final double balance;
  
  /// Account equity (balance + floating profit/loss).
  final double equity;
  
  /// Used margin for open positions.
  final double margin;
  
  /// Margin level as a percentage (equity/margin * 100).
  final double marginLevel;
  
  /// Free margin available for new positions.
  final double freeMargin;
  
  /// Account currency (USD, EUR, etc.).
  final String currency;
  
  /// Daily profit or loss amount.
  final double dailyProfitLoss;
  
  /// Number of open positions.
  final int openPositions;
  
  /// Number of pending orders.
  final int pendingOrders;

  const AccountInfo({
    required this.login,
    required this.server,
    required this.balance,
    required this.equity,
    required this.margin,
    required this.marginLevel,
    required this.freeMargin,
    required this.currency,
    required this.dailyProfitLoss,
    required this.openPositions,
    required this.pendingOrders,
  });

  /// Creates a default empty instance.
  factory AccountInfo.empty() {
    return const AccountInfo(
      login: 0,
      server: '',
      balance: 0.0,
      equity: 0.0,
      margin: 0.0,
      marginLevel: 0.0,
      freeMargin: 0.0,
      currency: 'USD',
      dailyProfitLoss: 0.0,
      openPositions: 0,
      pendingOrders: 0,
    );
  }
  
  /// Creates an AccountInfo from a JSON object.
  factory AccountInfo.fromJson(Map<String, dynamic> json) {
    return AccountInfo(
      login: json['login'] ?? 0,
      server: json['server'] ?? '',
      balance: json['balance']?.toDouble() ?? 0.0,
      equity: json['equity']?.toDouble() ?? 0.0,
      margin: json['margin']?.toDouble() ?? 0.0,
      marginLevel: json['margin_level']?.toDouble() ?? 0.0,
      freeMargin: json['free_margin']?.toDouble() ?? 0.0,
      currency: json['currency'] ?? 'USD',
      dailyProfitLoss: json['daily_profit_loss']?.toDouble() ?? 0.0,
      openPositions: json['open_positions'] ?? 0,
      pendingOrders: json['pending_orders'] ?? 0,
    );
  }
  
  /// Converts this AccountInfo to a JSON object.
  Map<String, dynamic> toJson() {
    return {
      'login': login,
      'server': server,
      'balance': balance,
      'equity': equity,
      'margin': margin,
      'margin_level': marginLevel,
      'free_margin': freeMargin,
      'currency': currency,
      'daily_profit_loss': dailyProfitLoss,
      'open_positions': openPositions,
      'pending_orders': pendingOrders,
    };
  }
  
  /// Creates a copy of this AccountInfo with the given fields replaced.
  AccountInfo copyWith({
    int? login,
    String? server,
    double? balance,
    double? equity,
    double? margin,
    double? marginLevel,
    double? freeMargin,
    String? currency,
    double? dailyProfitLoss,
    int? openPositions,
    int? pendingOrders,
  }) {
    return AccountInfo(
      login: login ?? this.login,
      server: server ?? this.server,
      balance: balance ?? this.balance,
      equity: equity ?? this.equity,
      margin: margin ?? this.margin,
      marginLevel: marginLevel ?? this.marginLevel,
      freeMargin: freeMargin ?? this.freeMargin,
      currency: currency ?? this.currency,
      dailyProfitLoss: dailyProfitLoss ?? this.dailyProfitLoss,
      openPositions: openPositions ?? this.openPositions,
      pendingOrders: pendingOrders ?? this.pendingOrders,
    );
  }

  @override
  List<Object?> get props => [
    login,
    server,
    balance,
    equity,
    margin,
    marginLevel,
    freeMargin,
    currency,
    dailyProfitLoss,
    openPositions,
    pendingOrders,
  ];
}
