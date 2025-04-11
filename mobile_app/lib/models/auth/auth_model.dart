import 'package:equatable/equatable.dart';

class AuthToken extends Equatable {
  final String accessToken;
  final String tokenType;
  final int expiresIn;
  final List<String> scopes;
  final DateTime createdAt;

  const AuthToken({
    required this.accessToken,
    required this.tokenType,
    required this.expiresIn,
    required this.scopes,
    required this.createdAt,
  });

  /// Check if the token is expired
  bool get isExpired {
    final expiryTime = createdAt.add(Duration(seconds: expiresIn));
    return DateTime.now().isAfter(expiryTime);
  }

  /// Get the expiry date
  DateTime get expiryDate {
    return createdAt.add(Duration(seconds: expiresIn));
  }

  /// Create from JSON response
  factory AuthToken.fromJson(Map<String, dynamic> json) {
    return AuthToken(
      accessToken: json['access_token'],
      tokenType: json['token_type'] ?? 'bearer',
      expiresIn: json['expires_in'] ?? 1800, // Default 30 minutes
      scopes: (json['scopes'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? ['read'],
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
    );
  }

  /// Convert to JSON for storage
  Map<String, dynamic> toJson() {
    return {
      'access_token': accessToken,
      'token_type': tokenType,
      'expires_in': expiresIn,
      'scopes': scopes,
      'created_at': createdAt.toIso8601String(),
    };
  }

  @override
  List<Object?> get props => [accessToken, tokenType, expiresIn, scopes, createdAt];
}

class MT5User extends Equatable {
  final String accountId;
  final String serverName;
  final String? name;
  final double? balance;
  final double? equity;
  final int? leverage;
  final List<String> scopes;

  const MT5User({
    required this.accountId,
    required this.serverName,
    required this.scopes,
    this.name,
    this.balance,
    this.equity,
    this.leverage,
  });

  /// Create from JSON response
  factory MT5User.fromJson(Map<String, dynamic> json) {
    return MT5User(
      accountId: json['account_id'] ?? json['login'] ?? '',
      serverName: json['server_name'] ?? '',
      scopes: (json['scopes'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? ['read'],
      name: json['name'],
      balance: json['balance'] != null ? double.tryParse(json['balance'].toString()) : null,
      equity: json['equity'] != null ? double.tryParse(json['equity'].toString()) : null,
      leverage: json['leverage'] != null ? int.tryParse(json['leverage'].toString()) : null,
    );
  }

  /// Convert to JSON for storage
  Map<String, dynamic> toJson() {
    return {
      'account_id': accountId,
      'server_name': serverName,
      'scopes': scopes,
      'name': name,
      'balance': balance,
      'equity': equity,
      'leverage': leverage,
    };
  }

  @override
  List<Object?> get props => [accountId, serverName, scopes, name, balance, equity, leverage];
}

class MT5Credentials extends Equatable {
  final String accountId; // MT5 Login ID
  final String password;
  final String serverName;

  const MT5Credentials({
    required this.accountId,
    required this.password,
    required this.serverName,
  });

  @override
  List<Object?> get props => [accountId, password, serverName];
}
