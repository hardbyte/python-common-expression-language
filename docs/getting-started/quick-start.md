# Quick Start

Get up and running with Python CEL in under 5 minutes.

## Your First Expression

The simplest way to use CEL is with the `evaluate` function:

```python
from cel import evaluate

# Basic arithmetic
result = evaluate("1 + 2")
assert result == 3

# String operations
result = evaluate('"Hello " + "World"')
assert result == "Hello World"

# Boolean logic
result = evaluate("5 > 3")
assert result == True

# Conditional expressions
result = evaluate('true ? "yes" : "no"')
assert result == "yes"

# Lists and maps
result = evaluate("[1, 2, 3]")
assert result == [1, 2, 3]

result = evaluate('{"name": "Alice", "age": 30}')
assert result == {'name': 'Alice', 'age': 30}

print("✓ Basic expressions working correctly")
```

## Adding Context

CEL expressions can use variables from context:

```python
from cel import evaluate

# Simple context variables
result = evaluate("age >= 18", {"age": 25})
assert result == True

result = evaluate("name + ' is awesome!'", {"name": "CEL"})
assert result == "CEL is awesome!"

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
result = evaluate('user.name + " is " + (user.age >= 18 ? "adult" : "minor")', {"user": user})
assert result == "Alice is adult"

# Working with lists
result = evaluate('"admin" in user.roles', {"user": user})
assert result == True

# Nested object access
result = evaluate('user.profile.verified && user.profile.email.endsWith("@example.com")', {"user": user})
assert result == True

# Type conversions
result = evaluate('user.name + " is " + string(user.age) + " years old"', {"user": user})
assert result == "Alice is 30 years old"

# Safe navigation with has()
result = evaluate('has(user.profile.phone) ? user.profile.phone : "No phone"', {"user": user})
assert result == "No phone"

print("✓ Context variables working correctly")
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
    assert result == True, f"Validation failed: {message}"

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
assert can_read == True

can_write = check_access_policy(user, resource, "write") 
assert can_write == False

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
assert result == expected

print("✓ Data transformation working correctly")
```

## Type System Basics

CEL has a rich type system that maps naturally to Python:

```python
from cel import evaluate
from datetime import datetime, timedelta

# Numbers with operations
result = evaluate("42")
assert result == 42
assert isinstance(result, int)

result = evaluate("3.14 * 2")
assert result == 6.28
assert isinstance(result, float)

result = evaluate("1u + 5u")
assert result == 6
assert isinstance(result, int)

# Strings with methods
result = evaluate('"hello world".size()')
assert result == 11

result = evaluate('"hello"[1]')
assert result == "e"

result = evaluate('"test".startsWith("te")')
assert result == True

# Bytes operations
result = evaluate("b'binary data'")
assert result == b'binary data'
assert isinstance(result, bytes)

result = evaluate("b'hello'.size()")
assert result == 5

# Collections with operations
result = evaluate("[1, 2, 3] + [4, 5]")
assert result == [1, 2, 3, 4, 5]

result = evaluate("[1, 2, 3].size()")
assert result == 3

result = evaluate('{"name": "Alice", "age": 30}')
assert result == {'name': 'Alice', 'age': 30}
assert isinstance(result, dict)

result = evaluate('{"a": 1, "b": 2}.size()')
assert result == 2

# Special types with operations
result = evaluate("null == null")
assert result == True

# Timestamps
result = evaluate('timestamp("2024-01-01T12:00:00Z")')
assert isinstance(result, datetime)
assert result.year == 2024
assert result.month == 1
assert result.day == 1
assert result.hour == 12

# Durations
result = evaluate('duration("1h30m")')
assert isinstance(result, timedelta)
assert result.total_seconds() == 5400.0

# Timestamp arithmetic
context = {"now": datetime.now()}
result = evaluate('now + duration("2h")', context)
assert isinstance(result, datetime)

print("✓ Type system working correctly")
```

## Error Handling

CEL expressions can fail for various reasons. Always handle errors appropriately:

```python
from cel import evaluate

def safe_evaluate(expression, context=None, default=None):
    """Safely evaluate a CEL expression with error handling."""
    try:
        return evaluate(expression, context or {})
    except ValueError as e:
        print(f"Syntax error: {e}")
        return default
    except TypeError as e:
        print(f"Type error: {e}")
        return default
    except RuntimeError as e:
        print(f"Runtime error: {e}")
        return default
    except Exception as e:
        print(f"Unexpected error: {e}")
        return default

# Different types of errors
context = {"age": 25, "name": "Alice"}

# Runtime error - undefined variable
result = safe_evaluate("undefined_variable + 1", context, default=0)
assert result == 0

# Type error - incompatible types
result = safe_evaluate('"hello" + 42', context, default="error")
assert result == "error"

# Syntax error - invalid CEL
result = safe_evaluate("1 + + 2", context, default=None)
assert result == None

# Successful evaluation
result = safe_evaluate('name + " is " + string(age)', context)
assert result == "Alice is 25"

# Safe navigation patterns
result = safe_evaluate('has("user.email") ? user.email : "no email"', {"user": {"name": "Bob"}}, "unknown")
assert result == "unknown"  # Note: This will trigger an error, so returns the default

# Error recovery with fallbacks
def evaluate_with_fallback(expressions, context):
    """Try multiple expressions until one succeeds."""
    for expr in expressions:
        result = safe_evaluate(expr, context)
        if result is not None:
            return result
    return "No valid result"

# Try different ways to get a user display name
user_context = {"user": {"first_name": "John", "last_name": "Doe"}}
fallback_expressions = [
    'user.display_name',  # Might not exist
    'user.full_name',     # Might not exist
    'user.first_name + " " + user.last_name',  # Should work
    'user.name',          # Fallback
    '"Unknown User"'      # Final fallback
]

display_name = evaluate_with_fallback(fallback_expressions, user_context)
assert display_name == "John Doe"

print("✓ Error handling working correctly")
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