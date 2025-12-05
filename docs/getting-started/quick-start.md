# Quick Start

Get up and running with Python CEL in under 5 minutes.

## Your First Expression

The simplest way to use CEL is with the `evaluate` function:

```python
from cel import evaluate

# Basic arithmetic
result = evaluate("1 + 2")
assert result == 3  # → 3 (CEL handles math naturally)

# String operations
result = evaluate('"Hello " + "World"')
assert result == "Hello World"  # → "Hello World" (string concatenation works intuitively)

# Boolean logic
result = evaluate("5 > 3")
assert result == True  # → True (comparison operators return clear boolean values)

# Conditional expressions
result = evaluate('true ? "yes" : "no"')
assert result == "yes"  # → "yes" (ternary operator for clean conditional logic)

# Lists and maps
result = evaluate("[1, 2, 3]")
assert result == [1, 2, 3]  # → [1, 2, 3] (native Python list creation)

result = evaluate('{"name": "Alice", "age": 30}')
assert result == {'name': 'Alice', 'age': 30}  # → {'name': 'Alice', 'age': 30} (native Python dict)

print("✓ Basic expressions working correctly")
```

## Adding Context

CEL expressions can use variables from context:

```python
from cel import evaluate

# Simple context variables
result = evaluate("age >= 18", {"age": 25})
assert result == True  # → True (age check with context variable)

result = evaluate("name + ' is awesome!'", {"name": "CEL"})
assert result == "CEL is awesome!"  # → "CEL is awesome!" (variable interpolation made easy)

# Complex nested context
user = {
    "name": "Alice",
    "age": 30,
    "roles": ["user", "admin"],
    "profile": {
        "email": "alice@example.com",
        "verified": True
    }
}

# String concatenation with conditionals  
adult_status = evaluate('user.age >= 18 ? "adult" : "minor"', {"user": user})
result = evaluate('user.name + " is " + status', {"user": user, "status": adult_status})
assert result == "Alice is adult"  # → "Alice is adult" (nested objects with conditional logic)

# Working with lists
result = evaluate('"admin" in user.roles', {"user": user})
assert result == True  # → True (membership testing in arrays)

# Nested object access
result = evaluate('user.profile.verified && user.profile.email.endsWith("@example.com")', {"user": user})
assert result == True  # → True (deep object navigation with string methods)

# Type conversions - CEL enforces type safety
result = evaluate('user.name + " is " + string(user.age) + " years old"', {"user": user})
assert result == "Alice is 30 years old"  # → "Alice is 30 years old" (explicit type conversion with string())

# ❌ This would fail - no automatic type conversion between incompatible types:
# evaluate('user.name + " is " + user.age')  # TypeError: can't add string + int
# 
# ✅ Always use explicit conversion for mixed types:
# string(), int(), float(), double() functions

# Safe navigation with has()
result = evaluate('has(user.profile.phone) ? user.profile.phone : "No phone"', {"user": user})
assert result == "No phone"  # → "No phone" (safe field checking prevents errors)

print("✓ Context variables working correctly")
```

## Pre-compilation for Performance

Use `compile()` when evaluating the same expression many times with different contexts:

```python
from cel import compile

# Compile once, execute many times
program = compile("price * quantity > threshold")

result1 = program.execute({"price": 10, "quantity": 5, "threshold": 40})
assert result1 == True  # → True (50 > 40)

result2 = program.execute({"price": 5, "quantity": 3, "threshold": 20})
assert result2 == False  # → False (15 > 20)

print("Pre-compilation working correctly")
```

## Ready for More?

You've mastered the basics of CEL evaluation with dictionary context! For advanced features like custom Python functions, context objects, and production patterns, continue to the next guide.

## CLI Quick Start

The CLI tool is great for testing and interactive use:

### Basic Expressions

```bash
cel '1 + 2'                    # 3
cel '"Hello " + "World"'       # Hello World
cel '[1, 2, 3].size()'        # 3
cel 'true ? "yes" : "no"'     # yes
```

### With Context

```bash
# Inline context
cel 'name + " is " + string(age)' --context '{"name": "Alice", "age": 30}'

# From file
echo '{"user": {"name": "Bob", "admin": true}}' > context.json
cel 'user.admin ? "Welcome admin " + user.name : "Access denied"' --context-file context.json
```

### Interactive REPL

Launch the interactive REPL for experimentation:

```bash
cel --interactive
```

The REPL provides:

- 🎨 **Syntax highlighting** as you type
- 📝 **Auto-completion** for CEL functions and variables  
- 📚 **Command history** with up/down arrows
- 🔧 **Built-in commands**: `help`, `context`, `history`, `load`

## Common Patterns

### Configuration Validation

```python
from cel import evaluate

config = {
    "database": {
        "host": "localhost",
        "port": 5432,
        "ssl": True
    },
    "cache": {
        "enabled": True,
        "ttl": 3600
    }
}

# Validate configuration
checks = [
    ("has(database.host) && database.host != ''", "Database host required"),
    ("database.port > 0 && database.port < 65536", "Valid database port required"),
    ("!cache.enabled || cache.ttl > 0", "Cache TTL must be positive when enabled")
]

for expression, message in checks:
    result = evaluate(expression, config)
    assert result == True, f"Validation failed: {message}"  # → True (each validation passes)

print("✓ Configuration validation working correctly")
```

### Policy Evaluation

```python
from cel import evaluate

def check_access_policy(user, resource, action):
    policy = """
    (user.role == "admin") ||
    (user.role == "owner" && resource.owner == user.id) ||
    (user.role == "member" && action == "read" && resource.public)
    """
    
    context = {
        "user": user,
        "resource": resource, 
        "action": action
    }
    
    return evaluate(policy, context)

# Example usage
user = {"id": "alice", "role": "member"}
resource = {"id": "doc1", "owner": "bob", "public": True}

can_read = check_access_policy(user, resource, "read")
assert can_read == True  # → True (member can read public resources)

can_write = check_access_policy(user, resource, "write") 
assert can_write == False  # → False (member cannot write to others' resources)

print("✓ Policy evaluation working correctly")
```

### Data Transformation

```python
from cel import evaluate

def transform_user_data(users):
    """Transform and filter user data using CEL expressions."""
    
    # Filter active adult users
    active_adults = []
    for user in users:
        if evaluate("user.active && user.age >= 18", {"user": user}):
            active_adults.append(user)
    
    # Generate display names
    for user in active_adults:
        display_name = evaluate(
            'user.first_name + " " + user.last_name + " (" + user.role + ")"',
            {"user": user}
        )
        user["display_name"] = display_name
    
    return active_adults

# Example data
users = [
    {"first_name": "Alice", "last_name": "Smith", "age": 30, "role": "admin", "active": True},
    {"first_name": "Bob", "last_name": "Jones", "age": 16, "role": "user", "active": True},
    {"first_name": "Carol", "last_name": "Davis", "age": 25, "role": "user", "active": False}
]

result = transform_user_data(users)
expected = [{'first_name': 'Alice', 'last_name': 'Smith', 'age': 30, 'role': 'admin', 'active': True, 'display_name': 'Alice Smith (admin)'}]
assert result == expected  # → [Alice Smith (admin)] (filtered and transformed data)

print("✓ Data transformation working correctly")
```

## Type System Basics

CEL has a rich type system that maps naturally to Python:

```python
from cel import evaluate
from datetime import datetime, timedelta

# Numbers with operations
result = evaluate("42")
assert result == 42  # → 42 (integers work naturally)
assert isinstance(result, int)

result = evaluate("3.14 * double(2)")
assert result == 6.28  # → 6.28 (floating point arithmetic)
assert isinstance(result, float)

result = evaluate("1u + 5u")
assert result == 6  # → 6 (unsigned integers convert to regular int)

# Strings with methods
result = evaluate('"hello world".size()')
assert result == 11  # → 11 (string length via size() method)

# Note: String indexing like "hello"[1] is not supported in CEL
# Use string methods instead: startsWith(), endsWith(), contains(), matches()

result = evaluate('"test".startsWith("te")')
assert result == True  # → True (rich string method support)

# Bytes operations
result = evaluate("b'binary data'")
assert result == b'binary data'  # → b'binary data' (native bytes support)
assert isinstance(result, bytes)

result = evaluate("b'hello'.size()")
assert result == 5  # → 5 (bytes also have size() method)

# Collections with operations
result = evaluate("[1, 2, 3] + [4, 5]")
assert result == [1, 2, 3, 4, 5]  # → [1, 2, 3, 4, 5] (list concatenation)

result = evaluate("[1, 2, 3].size()")
assert result == 3  # → 3 (list length)

result = evaluate('{"name": "Alice", "age": 30}')
assert result == {'name': 'Alice', 'age': 30}  # → {'name': 'Alice', 'age': 30} (maps as dicts)
assert isinstance(result, dict)

result = evaluate('{"a": 1, "b": 2}.size()')
assert result == 2  # → 2 (map size)

# Special types with operations
result = evaluate("null == null")
assert result == True  # → True (null handling works correctly)

# Timestamps
result = evaluate('timestamp("2024-01-01T12:00:00Z")')
assert isinstance(result, datetime)  # → datetime object (RFC3339 string parsing)
assert result.year == 2024
assert result.month == 1
assert result.day == 1
assert result.hour == 12

# Durations
result = evaluate('duration("1h30m")')
assert isinstance(result, timedelta)  # → timedelta object (duration string parsing)
assert result.total_seconds() == 5400.0  # → 5400.0 (1.5 hours in seconds)

# Timestamp arithmetic
context = {"now": datetime.now()}
result = evaluate('now + duration("2h")', context)
assert isinstance(result, datetime)  # → datetime object (time arithmetic works naturally)

print("✓ Type system working correctly")
```

## Error Handling

CEL expressions can fail for various reasons. Always handle errors appropriately:

```python
from cel import evaluate

# Most idiomatic: Let exceptions bubble up naturally
def evaluate_expression(expression: str, context: dict = None):
    """Evaluate expression with proper exception handling."""
    return evaluate(expression, context or {})

# For cases where you need fallback values  
def evaluate_with_default(expression: str, context: dict = None, default = None):
    """Evaluate with fallback value on errors."""
    try:
        return evaluate(expression, context or {})
    except (ValueError, TypeError, RuntimeError):
        return default

# Result-like pattern for detailed error information
def safe_evaluate(expression: str, context: dict = None):
    """
    Evaluate with detailed success/error information.
    
    Returns: (success: bool, result: Any, error_message: str)
    """
    try:
        result = evaluate(expression, context or {})
        return (True, result, "")
    except ValueError as e:
        return (False, None, f"Syntax error: {e}")
    except TypeError as e:
        return (False, None, f"Type error: {e}")
    except RuntimeError as e:
        return (False, None, f"Runtime error: {e}")

# Examples demonstrating idiomatic error handling
context = {"age": 25, "name": "Alice"}

# Most idiomatic: let exceptions propagate to caller
try:
    result = evaluate_expression('name + " is " + string(age)', context)
    assert result == "Alice is 25"  # → "Alice is 25"
except (ValueError, TypeError, RuntimeError) as e:
    print(f"Expression failed: {e}")

# Fallback pattern for non-critical features
display_name = evaluate_with_default(
    'user.display_name', 
    {"user": {"first_name": "John"}}, 
    default="Unknown User"
)
assert display_name == "Unknown User"  # → "Unknown User" (missing field)

# Result pattern when you need detailed error info
success, result, error = safe_evaluate("undefined_variable + 1", context)
assert success == False
assert result is None
assert "Runtime error" in error

success, result, error = safe_evaluate("age * 2", context)  
assert success == True
assert result == 50
assert error == ""

# Practical example: validation utility
def validate_user_rules(rules: list[str], user_context: dict) -> dict[str, bool]:
    """Validate multiple business rules for a user."""
    results = {}
    for rule in rules:
        try:
            results[rule] = bool(evaluate_expression(rule, user_context))
        except (ValueError, TypeError, RuntimeError):
            results[rule] = False  # Invalid rules are considered failed
    return results

# Test business rules validation
user = {"age": 25, "role": "member", "verified": True}
business_rules = [
    "age >= 18",                    # Valid rule
    "role == 'admin'",              # Valid rule (false result)
    "verified && age > 21",         # Valid rule  
    "invalid_syntax + +",           # Invalid syntax
]

rule_results = validate_user_rules(business_rules, user)
assert rule_results["age >= 18"] == True
assert rule_results["role == 'admin'"] == False
assert rule_results["verified && age > 21"] == True
assert rule_results["invalid_syntax + +"] == False

print("✓ Idiomatic error handling working correctly")
```

## What's Next?

Congratulations! You've mastered basic CEL evaluation with dictionary context. Now choose your learning path:

**🚀 Start Building Real Applications (Recommended):**
- **[Your First Integration](../tutorials/your-first-integration.md)** - Learn Context objects and custom Python functions through practical examples

**📚 Understand CEL Philosophy First:**
- **[Thinking in CEL](../tutorials/thinking-in-cel.md)** - Core concepts, design principles, and when to use CEL

**📖 Reference Material (Bookmark These):**
- **[CEL Language Basics](../tutorials/cel-language-basics.md)** - Complete syntax reference for quick lookup

**🏢 Jump to Specific Applications:**
- **[Access Control Policies](../how-to-guides/access-control-policies.md)** - Build permission systems (requires Context knowledge)
- **[Business Logic & Data Transformation](../how-to-guides/business-logic-data-transformation.md)** - Implement business rules
- **[Production Patterns & Best Practices](../how-to-guides/production-patterns-best-practices.md)** - Deploy CEL safely

**💡 Recommended Learning Path:**

**Quick Start → [Your First Integration](../tutorials/your-first-integration.md) → [Access Control Policies](../how-to-guides/access-control-policies.md)**

This path takes you from basics to production-ready applications in the most efficient way.