/// Utility class with common form validation functions
class Validators {
  /// Validates that a field is not empty
  static String? Function(String?) required(String message) {
    return (String? value) {
      if (value == null || value.trim().isEmpty) {
        return message;
      }
      return null;
    };
  }
  
  /// Validates an email address format
  static String? Function(String?) email(String? value) {
    if (value == null || value.isEmpty) {
      return 'Email is required';
    }
    
    final emailRegex = RegExp(
      r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    );
    
    if (!emailRegex.hasMatch(value)) {
      return 'Enter a valid email address';
    }
    
    return null;
  }
  
  /// Validates password strength
  static String? Function(String?) password(String? value) {
    if (value == null || value.isEmpty) {
      return 'Password is required';
    }
    
    if (value.length < 8) {
      return 'Password must be at least 8 characters';
    }
    
    // Advanced password validation could be added here
    // For example, requiring uppercase, lowercase, numbers, and special characters
    
    return null;
  }
  
  /// Validates if a string is a number
  static String? Function(String?) number(String? value) {
    if (value == null || value.isEmpty) {
      return 'Field is required';
    }
    
    if (double.tryParse(value) == null) {
      return 'Enter a valid number';
    }
    
    return null;
  }
  
  /// Validates a string is an integer
  static String? Function(String?) integer(String? value) {
    if (value == null || value.isEmpty) {
      return 'Field is required';
    }
    
    if (int.tryParse(value) == null) {
      return 'Enter a valid integer';
    }
    
    return null;
  }
  
  /// Validates minimum length
  static String? Function(String?) minLength(int length, {String? message}) {
    return (String? value) {
      if (value == null || value.isEmpty) {
        return 'Field is required';
      }
      
      if (value.length < length) {
        return message ?? 'Must be at least $length characters';
      }
      
      return null;
    };
  }
  
  /// Validates maximum length
  static String? Function(String?) maxLength(int length, {String? message}) {
    return (String? value) {
      if (value == null) return null;
      
      if (value.length > length) {
        return message ?? 'Must be at most $length characters';
      }
      
      return null;
    };
  }
  
  /// Compares if two values match
  static String? Function(String?) match(String value, String matchName) {
    return (String? input) {
      if (input == null || input.isEmpty) {
        return 'Field is required';
      }
      
      if (input != value) {
        return 'Doesn\'t match $matchName';
      }
      
      return null;
    };
  }
}
