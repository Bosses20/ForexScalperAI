import 'package:equatable/equatable.dart';
import '../../models/settings/bot_settings.dart';

abstract class SettingsEvent extends Equatable {
  const SettingsEvent();
  
  @override
  List<Object?> get props => [];
}

class LoadSettings extends SettingsEvent {
  const LoadSettings();
}

class SaveSettings extends SettingsEvent {
  final BotSettings settings;
  
  const SaveSettings(this.settings);
  
  @override
  List<Object?> get props => [settings];
}

class UpdateMT5ConnectionSettings extends SettingsEvent {
  final MT5ConnectionSettings settings;
  
  const UpdateMT5ConnectionSettings(this.settings);
  
  @override
  List<Object?> get props => [settings];
}

class UpdateTradingSettings extends SettingsEvent {
  final TradingSettings settings;
  
  const UpdateTradingSettings(this.settings);
  
  @override
  List<Object?> get props => [settings];
}

class UpdateRiskManagementSettings extends SettingsEvent {
  final RiskManagementSettings settings;
  
  const UpdateRiskManagementSettings(this.settings);
  
  @override
  List<Object?> get props => [settings];
}

class UpdateStrategySettings extends SettingsEvent {
  final StrategySettings settings;
  
  const UpdateStrategySettings(this.settings);
  
  @override
  List<Object?> get props => [settings];
}

class ResetSettings extends SettingsEvent {
  const ResetSettings();
}
