import 'package:flutter/material.dart';
import '../../models/bot_server.dart';
import '../../utils/validators.dart';
import '../../widgets/custom_button.dart';
import '../../widgets/custom_text_field.dart';
import '../../widgets/loading_indicator.dart';

class ForgotPasswordScreen extends StatefulWidget {
  final BotServer selectedServer;

  const ForgotPasswordScreen({
    Key? key,
    required this.selectedServer,
  }) : super(key: key);

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _accountController = TextEditingController();
  final _emailController = TextEditingController();
  bool _isLoading = false;
  bool _isSuccess = false;

  @override
  void dispose() {
    _accountController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _resetPassword() async {
    if (_formKey.currentState?.validate() != true) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      // This would typically call the API service to initiate password reset
      // For now, we'll simulate a successful request after a delay
      await Future.delayed(const Duration(seconds: 2));
      
      if (mounted) {
        setState(() {
          _isSuccess = true;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to request password reset: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1E222D),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E222D),
        title: const Text('Forgot Password'),
        elevation: 0,
        iconTheme: const IconThemeData(
          color: Colors.white,
        ),
      ),
      body: _isLoading
          ? const Center(child: LoadingIndicator(message: 'Requesting password reset...'))
          : _isSuccess
              ? _buildSuccessView()
              : _buildResetForm(),
    );
  }

  Widget _buildResetForm() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Title
            const Text(
              'Reset Your MT5 Password',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            
            // Description
            const Text(
              'Enter your MT5 account ID and registered email address. We\'ll send instructions to reset your password.',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 14,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),

            // Account ID field
            CustomTextField(
              controller: _accountController,
              label: 'MT5 Account ID',
              hintText: 'Enter your MT5 account ID',
              keyboardType: TextInputType.number,
              prefixIcon: const Icon(Icons.account_circle, color: Colors.white70),
              validator: Validators.required('MT5 Account ID is required'),
            ),
            const SizedBox(height: 16),

            // Email field
            CustomTextField(
              controller: _emailController,
              label: 'Email Address',
              hintText: 'Enter your registered email address',
              keyboardType: TextInputType.emailAddress,
              prefixIcon: const Icon(Icons.email, color: Colors.white70),
              validator: Validators.email,
            ),
            const SizedBox(height: 16),

            // Server information
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF262A35),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.white24),
              ),
              child: Row(
                children: [
                  const Icon(Icons.dns, color: Colors.white70),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Server',
                          style: TextStyle(
                            color: Colors.white70,
                            fontSize: 12,
                          ),
                        ),
                        Text(
                          widget.selectedServer.name,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // Submit button
            CustomButton(
              text: 'RESET PASSWORD',
              onPressed: _resetPassword,
              color: Colors.blue,
            ),
            const SizedBox(height: 16),

            // Back to login
            CustomButton(
              text: 'BACK TO LOGIN',
              onPressed: () => Navigator.pop(context),
              color: Colors.transparent,
              borderColor: Colors.white30,
              textColor: Colors.white,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSuccessView() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Success icon
          const Icon(
            Icons.check_circle_outline,
            size: 80,
            color: Colors.green,
          ),
          const SizedBox(height: 24),
          
          // Success message
          const Text(
            'Password Reset Request Sent',
            style: TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          
          Text(
            'We\'ve sent password reset instructions to ${_emailController.text}. Please check your email for further instructions.',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 16,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          
          // Note about MT5 broker process
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF262A35),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.white24),
            ),
            child: const Column(
              children: [
                Text(
                  'Note:',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'MT5 password reset is handled by your broker. The exact process may vary depending on your broker\'s policies. If you don\'t receive an email, please contact your broker\'s support team directly.',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          
          // Back to login button
          CustomButton(
            text: 'BACK TO LOGIN',
            onPressed: () => Navigator.pop(context),
            color: Colors.blue,
          ),
        ],
      ),
    );
  }
}
