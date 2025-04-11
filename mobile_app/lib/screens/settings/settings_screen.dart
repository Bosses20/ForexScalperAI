import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../blocs/settings/settings_bloc.dart';
import '../../blocs/settings/settings_event.dart';
import '../../blocs/settings/settings_state.dart';
import '../../models/settings/bot_settings.dart';
import 'tabs/mt5_connection_tab.dart';
import 'tabs/trading_settings_tab.dart';
import 'tabs/risk_management_tab.dart';
import 'tabs/strategy_settings_tab.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    
    // Load settings when screen initializes
    context.read<SettingsBloc>().add(LoadSettings());
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bot Settings'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'MT5 Connection', icon: Icon(Icons.link)),
            Tab(text: 'Trading', icon: Icon(Icons.candlestick_chart)),
            Tab(text: 'Risk Management', icon: Icon(Icons.shield)),
            Tab(text: 'Strategies', icon: Icon(Icons.psychology)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              context.read<SettingsBloc>().add(RefreshSettings());
            },
            tooltip: 'Refresh settings',
          ),
          IconButton(
            icon: const Icon(Icons.restore),
            onPressed: _showResetConfirmation,
            tooltip: 'Reset to defaults',
          ),
        ],
      ),
      body: BlocConsumer<SettingsBloc, SettingsState>(
        listener: (context, state) {
          if (state is SettingsError) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.message),
                backgroundColor: Colors.red,
              ),
            );
          } else if (state is SettingsSaved) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Settings saved successfully'),
                backgroundColor: Colors.green,
              ),
            );
          }
        },
        builder: (context, state) {
          if (state is SettingsLoading) {
            return const Center(child: CircularProgressIndicator());
          } else if (state is SettingsLoaded || state is SettingsSaved) {
            final settings = state is SettingsLoaded
                ? state.settings
                : (state as SettingsSaved).settings;
                
            return TabBarView(
              controller: _tabController,
              children: [
                MT5ConnectionTab(settings: settings.mt5Connection),
                TradingSettingsTab(settings: settings.tradingSettings),
                RiskManagementTab(settings: settings.riskManagement),
                StrategySettingsTab(settings: settings.strategySettings),
              ],
            );
          } else if (state is SettingsError) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Error loading settings: ${state.message}',
                    style: const TextStyle(color: Colors.red),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      context.read<SettingsBloc>().add(LoadSettings());
                    },
                    child: const Text('Try Again'),
                  ),
                ],
              ),
            );
          }
          
          // Initial state or unhandled state
          return const Center(child: CircularProgressIndicator());
        },
      ),
    );
  }
  
  void _showResetConfirmation() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reset Settings'),
        content: const Text(
          'Are you sure you want to reset all settings to their default values? '
          'This cannot be undone.'
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              context.read<SettingsBloc>().add(ResetSettings());
            },
            child: const Text('Reset', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}
