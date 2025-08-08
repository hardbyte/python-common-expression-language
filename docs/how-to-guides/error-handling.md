# Error Handling

Learn how to handle errors gracefully in production CEL applications, from basic exception handling to advanced safety patterns for untrusted input.

## Understanding CEL Exceptions

The library raises specific exception types based on the underlying error type. Understanding these patterns helps you write robust error handling:

### `ValueError` - Parse and Compilation Errors

Raised when the CEL expression has invalid syntax, is empty, or fails to compile:

```python
from cel import evaluate

try:
    evaluate("1 + + 2")  # Invalid syntax
    assert False, "Expected ValueError"
except ValueError as e:
    assert "Failed to compile expression" in str(e)
    # → ValueError: Failed to compile expression (graceful failure)

try:
    evaluate("")  # Empty expression
    assert False, "Expected ValueError"
except ValueError as e:
    assert "Invalid syntax" in str(e) or "malformed" in str(e)
    # → ValueError: Invalid syntax or malformed (safe error handling)
```

### `RuntimeError` - Variable and Function Errors

Raised for undefined variables/functions and function execution errors:

```python
# Undefined variables
try:
    evaluate("unknown_variable + 1", {})
    assert False, "Expected RuntimeError"
except RuntimeError as e:
    assert "Undefined variable or function" in str(e)
    # → RuntimeError: Undefined variable (prevents security issues)

# Undefined functions
try:
    evaluate("unknownFunction(42)", {})
    assert False, "Expected RuntimeError"
except RuntimeError as e:
    assert "Undefined variable or function" in str(e)
    # → RuntimeError: Undefined function (safe by default)

# Function execution errors
from cel import Context
def error_function():
    raise ValueError("Internal error")

context = Context()
context.add_function("error_func", error_function)

try:
    evaluate("error_func()", context)
    assert False, "Expected RuntimeError"
except RuntimeError as e:
    assert "Function 'error_func' error" in str(e)
    # → RuntimeError: Function error propagated safely
```

### `TypeError` - Type Compatibility Errors

Raised when operations are performed on incompatible types:

```python
# String + int operations
try:
    evaluate('"hello" + 42')  # String + int
    assert False, "Expected TypeError"
except TypeError as e:
    assert "Unsupported addition operation" in str(e)
    # → TypeError: Type safety enforced (no implicit conversion)

# Mixed signed/unsigned integers
try:
    evaluate("1u + 2")  # Mixed signed/unsigned int
    assert False, "Expected TypeError"
except TypeError as e:
    assert "Cannot mix signed and unsigned integers" in str(e)
    # → TypeError: Integer type mixing prevented

# Unsupported operations by type
try:
    evaluate('"text" * "more"')  # String multiplication
    assert False, "Expected TypeError"
except TypeError as e:
    assert "Unsupported multiplication operation" in str(e)
    # → TypeError: Invalid operation caught early
```

## ✅ Safe Error Handling for Malformed Input

**Good News**: All malformed expressions, including those that previously caused panics, now raise proper Python exceptions instead of crashing the process.

**Malformed syntax that now raises `ValueError`:**
- Unclosed quotes: `'timestamp("2024-01-01T00:00:00Z")`
- Mixed quote types: `"some text'` or `'some text"`
- Invalid syntax patterns

**Examples that now raise clean errors:**
```python
from cel import evaluate

try:
    evaluate("'unclosed quote", {})
    assert False, "Should have raised ValueError"
except ValueError as e:
    assert "Invalid syntax or malformed string" in str(e)
    # → ValueError: Malformed input handled safely (no crash)

try:
    evaluate('"mixed quotes\'', {})
    assert False, "Should have raised ValueError"
except ValueError as e:
    assert "Invalid syntax or malformed string" in str(e)
    # → ValueError: Quote mismatch detected (process remains stable)
```

**For untrusted input:**
The library now safely handles all malformed input by raising appropriate exceptions, making it safe to evaluate expressions from untrusted sources without additional pre-validation (though input validation is still a good practice for security).

## Production Error Handling Patterns

### 1. Safe Evaluation Wrapper

Create a wrapper function that handles all CEL exceptions gracefully:

```python
from cel import evaluate
from typing import Any, Optional, Dict
import logging

def safe_evaluate(expression: str, context: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """
    Safely evaluate a CEL expression with comprehensive error handling.
    
    Returns None if evaluation fails for any reason.
    """
    try:
        return evaluate(expression, context)
    except ValueError as e:
        logging.warning(f"CEL parse error: {e}")
        return None
    except TypeError as e:
        logging.warning(f"CEL type error: {e}")
        return None
    except RuntimeError as e:
        logging.warning(f"CEL runtime error: {e}")
        return None
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"Unexpected CEL error: {e}")
        return None

# Usage
result = safe_evaluate("user.age >= 18", {"user": {"age": 25}})
if result is not None:
    assert result is True
    # → True (safe evaluation with graceful error handling)
else:
    assert False, "Expression evaluation should not have failed"
```

### 2. Context Validation {#context-validation}

Validate context data before evaluation to prevent runtime errors:

```python
def validate_context(context: Dict[str, Any], required_fields: list[str]) -> None:
    """Validate that all required fields are present in context."""
    for field in required_fields:
        if field not in context:
            raise ValueError(f"Missing required field: {field}")

def validate_nested_field(context: Dict[str, Any], field_path: str) -> bool:
    """Check if a nested field exists (e.g., 'user.profile.verified')."""
    keys = field_path.split('.')
    current = context
    
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    
    return True

def safe_policy_evaluation(policy: str, context: Dict[str, Any]) -> bool:
    """Evaluate a policy with context validation."""
    try:
        # Validate required top-level fields
        validate_context(context, ["user", "resource"])
        
        # Validate specific nested fields used in policy
        if not validate_nested_field(context, "user.id"):
            raise ValueError("Missing required field: user.id")
        
        result = evaluate(policy, context)
        return bool(result) if result is not None else False
        
    except Exception as e:
        logging.error(f"Policy evaluation failed: {e}")
        return False  # Deny access on any error

# Usage
context = {
    "user": {"id": "alice", "role": "user"},
    "resource": {"owner": "alice", "type": "document"}
}

access_granted = safe_policy_evaluation(
    'user.role == "admin" || resource.owner == user.id',
    context
)
assert access_granted is True
# → True (policy allows access - user owns resource)

# Test 2: Missing required context field
incomplete_context = {
    "user": {"id": "alice", "role": "user"}
    # Missing "resource" field
}

result = safe_policy_evaluation('user.role == "admin"', incomplete_context)
assert result == False, "Should deny access when required context is missing"
# → False (graceful degradation - deny when context incomplete)

# Test 3: Missing nested required field
context_missing_user_id = {
    "user": {"role": "user"},  # Missing "id" field
    "resource": {"owner": "alice", "type": "document"}
}

result = safe_policy_evaluation('resource.owner == user.id', context_missing_user_id)
assert result == False, "Should deny access when required nested field is missing"
# → False (fail-safe - deny access on missing data)

# Test 4: Valid policy with different outcome
admin_context = {
    "user": {"id": "bob", "role": "admin"},
    "resource": {"owner": "alice", "type": "document"}
}

result = safe_policy_evaluation('user.role == "admin" || resource.owner == user.id', admin_context)
assert result == True, "Admin should have access regardless of ownership"
# → True (admin privilege overrides ownership check)

print("✓ Safe policy evaluation with context validation working correctly")
# → Output: Defensive programming prevents security bypass
```

### 3. Input Sanitization for Untrusted Expressions {#input-sanitization-for-untrusted-expressions}

When accepting CEL expressions from users, implement validation:

```python
import re
from typing import List, Optional

class CELValidator:
    """Validator for CEL expressions from untrusted sources."""
    
    # Patterns that are commonly malformed and raise ValueError
    DANGEROUS_PATTERNS = [
        r"'[^']*$",           # Unclosed single quote
        r'"[^"]*$',           # Unclosed double quote
        r"'[^']*\"",          # Mixed quotes: single -> double
        r'"[^"]*\'',          # Mixed quotes: double -> single
    ]
    
    # Maximum expression length to prevent DoS
    MAX_EXPRESSION_LENGTH = 1000
    
    def validate_expression(self, expression: str) -> List[str]:
        """
        Validate a CEL expression for common issues.
        
        Returns list of validation errors (empty if valid).
        """
        errors = []
        
        # Check length
        if len(expression) > self.MAX_EXPRESSION_LENGTH:
            errors.append(f"Expression too long (max {self.MAX_EXPRESSION_LENGTH} chars)")
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, expression):
                errors.append("Expression contains potentially problematic syntax")
                break
        
        # Check balanced quotes
        if not self._quotes_balanced(expression):
            errors.append("Unbalanced quotes detected")
        
        return errors
    
    def _quotes_balanced(self, expression: str) -> bool:
        """Check if quotes are properly balanced."""
        single_quotes = expression.count("'")
        double_quotes = expression.count('"')
        
        # Simple check - both should be even (assuming no escaping)
        return single_quotes % 2 == 0 and double_quotes % 2 == 0

def safe_user_expression_eval(user_expression: str, context: Dict[str, Any]) -> tuple[bool, Optional[Any], List[str]]:
    """
    Safely evaluate a user-provided CEL expression.
    
    Returns (success, result, errors).
    """
    validator = CELValidator()
    
    # Validate expression first
    validation_errors = validator.validate_expression(user_expression)
    if validation_errors:
        return False, None, validation_errors
    
    # Attempt evaluation
    try:
        result = evaluate(user_expression, context)
        return True, result, []
    except Exception as e:
        return False, None, [f"Evaluation error: {str(e)}"]

# Usage
user_input = 'user.age >= 18 && user.verified == true'
context = {"user": {"age": 25, "verified": True}}

success, result, errors = safe_user_expression_eval(user_input, context)
if success:
    assert result is True
    # → True (user meets age and verification requirements)
else:
    assert False, f"Validation should not have failed: {errors}"

# Test 2: Invalid expression (accessing Python internals)
dangerous_input = 'user.__class__.__name__'
success, result, errors = safe_user_expression_eval(dangerous_input, context)
assert success == False, "Dangerous expression should be blocked"
assert len(errors) > 0, "Should report validation or runtime errors"
# → False, errors: ['Evaluation error: ...'] (security threat blocked)

# Test 3: Invalid syntax
invalid_syntax = 'user.age >= 18 &&'
success, result, errors = safe_user_expression_eval(invalid_syntax, context)
assert success == False, "Invalid syntax should be rejected"
assert len(errors) > 0, "Should report syntax errors"
# → False, errors: ['Evaluation error: Failed to compile'] (malformed input caught)

# Test 4: Empty expression
success, result, errors = safe_user_expression_eval('', context)
assert success == False, "Empty expression should be rejected"
# → False, errors: ['Evaluation error: Invalid syntax'] (empty input handled)

# Test 5: Undefined variable
undefined_var = 'nonexistent_var == true'
success, result, errors = safe_user_expression_eval(undefined_var, context)
assert success == False, "Undefined variable should cause error"
# → False, errors: ['Evaluation error: Undefined variable'] (prevents data leakage)

print("✓ Safe expression validation working correctly")
# → Output: Comprehensive input validation working
```

## Defensive Expression Patterns

### Safe Field Access

Use CEL's built-in safety features to write robust expressions:

```python
# ❌ Risky - will fail if fields don't exist
risky_expr = 'user.profile.settings.theme == "dark"'

# ✅ Safe - check existence first
safe_expr = '''
    has(user.profile) && 
    has(user.profile.settings) && 
    has(user.profile.settings.theme) && 
    user.profile.settings.theme == "dark"
'''

# ✅ Even safer - use defaults (with has() checks)
safe_with_defaults = '''has(user.profile) && has(user.profile.settings) && 
    (has(user.profile.settings.theme) ? user.profile.settings.theme : "light") == "dark"'''

# Test both approaches
context_complete = {
    "user": {
        "profile": {
            "settings": {"theme": "dark"}
        }
    }
}

context_missing = {"user": {"name": "alice"}}

# Safe expressions work with both contexts
assert safe_evaluate(safe_expr, context_complete) is True
# → True (complete context allows proper evaluation)
assert safe_evaluate(safe_expr, context_missing) is False
# → False (missing fields cause safe failure)

assert safe_evaluate(safe_with_defaults, context_complete) is True
# → True (theme setting detected correctly)
assert safe_evaluate(safe_with_defaults, context_missing) is False
# → False (defensive pattern prevents runtime errors)
```

### Type-Safe Operations

Prevent type errors with careful expression design:

```python
# ❌ Risky - assumes numeric types
risky_expr = 'user.age > 18'

# ✅ Safe - use numeric conversion with error handling
safe_expr = 'has(user.age) && double(user.age) > 18.0'

# ✅ Alternative - check for common failure case first
defensive_expr = 'has(user.age) && user.age != null && user.age > 18'

# Note: type() function is not available in this CEL implementation
# Use conversion functions (double(), int()) for type safety instead
```

## Logging and Monitoring

### Structured Error Logging

Implement comprehensive logging for production debugging:

```python
import logging
import json
from datetime import datetime, timezone

def evaluate_with_logging(expression: str, context: Dict[str, Any], operation_id: str = None) -> Any:
    """Evaluate with comprehensive logging for production debugging."""
    
    start_time = datetime.now(timezone.utc)
    
    log_context = {
        "operation_id": operation_id,
        "expression": expression,
        "context_keys": list(context.keys()) if context else [],
        "timestamp": start_time.isoformat()
    }
    
    try:
        result = evaluate(expression, context)
        
        # Log successful evaluation
        logging.info("CEL evaluation succeeded", extra={
            **log_context,
            "result_type": type(result).__name__,
            "duration_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        })
        
        return result
        
    except Exception as e:
        # Log detailed error information
        logging.error("CEL evaluation failed", extra={
            **log_context,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "duration_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        })
        raise

# Usage in web application
def get_user(user_id: str):
    """Mock function to get user data."""
    return {"id": user_id, "role": "user"}

def get_resource(resource_id: str):
    """Mock function to get resource data."""
    return {"id": resource_id, "type": "document"}

def check_access(user_id: str, resource_id: str, policy: str) -> bool:
    context = {
        "user": get_user(user_id),
        "resource": get_resource(resource_id)
    }
    
    operation_id = f"access_check_{user_id}_{resource_id}"
    
    try:
        result = evaluate_with_logging(policy, context, operation_id)
        return bool(result)
    except Exception:
        # Log and deny access on any error
        return False

# Test the function
result = check_access("alice", "doc1", "user.id == 'alice'")
assert result is True
# → True (access granted with comprehensive logging)
```

## Testing Error Scenarios

### Unit Tests for Error Handling

Write comprehensive tests for your error handling:

```python
from cel import evaluate
from typing import Any, Optional, Dict
import logging

def safe_evaluate(expression: str, context: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """Safely evaluate a CEL expression with comprehensive error handling."""
    try:
        return evaluate(expression, context)
    except ValueError as e:
        logging.warning(f"CEL parse error: {e}")
        return None
    except TypeError as e:
        logging.warning(f"CEL type error: {e}")
        return None
    except RuntimeError as e:
        logging.warning(f"CEL runtime error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected CEL error: {e}")
        return None

def test_error_handling():
    """Test various error scenarios."""
    
    # Test parse errors
    try:
        evaluate("1 + + 2")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
        # → ValueError caught (syntax error handled gracefully)
    
    # Test runtime errors  
    try:
        evaluate("unknown_var", {})
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass  # Expected
        # → RuntimeError caught (undefined variable blocked safely)
    
    # Test type errors
    try:
        evaluate('"hello" + 42')
        assert False, "Should have raised TypeError"
    except TypeError:
        pass  # Expected
        # → TypeError caught (type safety enforced)

def test_safe_evaluation():
    """Test safe evaluation wrapper."""
    
    # Should return None for invalid expressions
    assert safe_evaluate("1 + + 2") is None
    # → None (parse error handled gracefully)
    assert safe_evaluate("unknown_var", {}) is None
    # → None (runtime error converted to safe None)
    assert safe_evaluate('"hello" + 42') is None
    # → None (type error handled without crash)
    
    # Should work for valid expressions
    assert safe_evaluate("1 + 2") == 3
    # → 3 (valid expression evaluates correctly)
    assert safe_evaluate("name", {"name": "Alice"}) == "Alice"
    # → "Alice" (context variable accessed safely)

# Run tests to verify everything works
test_error_handling()
test_safe_evaluation()
print("✓ Error handling test examples working correctly")
# → Output: All error scenarios handled robustly
```

## Best Practices Summary

1. **Always use exception handling** in production code
2. **Validate context data** before evaluation
3. **Use defensive expressions** with `has()` and ternary operators
4. **Implement input validation** for untrusted expressions
5. **Log errors comprehensively** for debugging
6. **Test error scenarios** thoroughly
7. **Handle malformed input** with proper exception handling
8. **Fail safely** - deny access on evaluation errors

Remember: CEL is designed to be safe, but your application's error handling determines how gracefully it handles edge cases and malicious input.