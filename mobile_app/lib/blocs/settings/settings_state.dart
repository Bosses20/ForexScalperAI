import 'package:equatable/equatable.dart';
import '../../models/settings/bot_settings.dart';

enum SettingsStatus {
  initial,
  loading,
  loaded,
  saving,
  saved,
  error,
}

class SettingsState extends Equatable {
  final SettingsStatus status;
  final BotSettings? settings;
  final String? errorMessage;
  
  const SettingsState({
    this.status = SettingsStatus.initial,
    this.settings,
    this.errorMessage,
  });
  
  @override
  List<Object?> get props => [status, settings, errorMessage];
  
  SettingsState copyWith({
    SettingsStatus? status,
    BotSettings? settings,
    String? errorMessage,
  }) {
    return SettingsState(
      status: status ?? this.status,
      settings: settings ?? this.settings,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }
  
  // Check if the settings are currently being loaded or saved
  bool get isLoading => status == SettingsStatus.loading || status == SettingsStatus.saving;
  
  // Check if settings were successfully loaded
  bool get hasSettings => settings != null;
  
  // Check if there is an error
  bool get hasError => errorMessage != null && errorMessage!.isNotEmpty;
}
