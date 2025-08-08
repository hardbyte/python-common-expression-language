# Your First Python Integration

Now that you understand the basics from [Quick Start](../getting-started/quick-start.md), let's dive deeper into CEL's powerful Python integration features. You'll learn to use the Context class for better control and add custom Python functions to create domain-specific expressions.

> **Prerequisites:** Complete the [Quick Start Guide](../getting-started/quick-start.md) to understand basic CEL evaluation with dictionary context. If you want to understand CEL's design philosophy first, read [Thinking in CEL](thinking-in-cel.md).

## What You'll Learn

By the end of this tutorial, you'll be able to:

- ✅ Use the Context class for advanced variable management
- ✅ Register and call custom Python functions from CEL expressions  
- ✅ Build practical business policies that combine CEL expressions with Python logic
- ✅ Handle errors gracefully in production scenarios
- ✅ Apply common patterns for access control, validation, and business rules

## The Context Class

While dictionary context is convenient for simple use cases, the `Context` class provides more control and enables advanced features like custom Python functions:

```python
from cel import evaluate, Context

# Create a context object
context = Context()

# Add variables
context.add_variable("name", "Alice")
context.add_variable("age", 30)
context.add_variable("roles", ["user", "admin"])

# Use the context in evaluations
result = evaluate("name + ' is ' + string(age)", context)
# → "Alice is 30"
assert result == "Alice is 30"

result = evaluate('"admin" in roles', context)
# → True
assert result == True

print("✓ Context class basics working correctly")
```

### Batch Updates

Add multiple variables at once using `update()`:

```python
context = Context()
context.update({
    "user": {
        "name": "Bob",
        "email": "bob@example.com", 
        "profile": {"verified": True, "department": "engineering"}
    },
    "current_time": "2024-01-15T10:30:00Z",
    "permissions": ["read", "write"]
})

result = evaluate("user.profile.verified && 'write' in permissions", context)
# → True (verified user with write permission)
assert result == True

print("✓ Batch context updates working correctly")
```

## Custom Python Functions

The Context class enables you to call Python functions from CEL expressions, opening up unlimited possibilities for domain-specific logic:

```python
from cel import evaluate, Context
import re
import hashlib
from datetime import datetime

def calculate_tax(income, rate=0.1):
    """Calculate tax based on income and rate."""
    return income * rate

def is_weekend(day):
    """Check if a day is weekend."""
    return day.lower() in ["saturday", "sunday"]

def validate_email(email):
    """Simple email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def calculate_discount(price, customer_type, quantity=1):
    """Calculate discount based on customer type and quantity."""
    discounts = {"vip": 0.2, "premium": 0.15, "regular": 0.05}
    base_discount = discounts.get(customer_type, 0)
    volume_discount = 0.05 if quantity >= 10 else 0
    return price * (base_discount + volume_discount)

# Set up context with variables and functions
context = Context()
context.add_variable("income", 50000)
context.add_variable("user_email", "alice@example.com")
context.add_variable("today", "saturday")
context.add_variable("price", 100.0)
context.add_variable("customer", "vip")
context.add_variable("quantity", 15)

context.add_function("calculate_tax", calculate_tax)
context.add_function("is_weekend", is_weekend)
context.add_function("validate_email", validate_email)
context.add_function("hash_password", hash_password)
context.add_function("calculate_discount", calculate_discount)

# Use functions in expressions
tax = evaluate("calculate_tax(income, 0.15)", context)
# → 7500.0 (50000 * 0.15)
assert tax == 7500.0

# Test weekend detection
weekend = evaluate('is_weekend(today)', context)
# → True (saturday is a weekend)
assert weekend == True

# Validate email
email_valid = evaluate('validate_email(user_email)', context)
# → True (alice@example.com is valid)
assert email_valid == True

# Calculate discount with volume bonus
discount = evaluate('calculate_discount(price, customer, quantity)', context)
# → 25.0 (20% VIP discount + 5% volume discount on $100)
assert discount == 25.0  # 20% VIP + 5% volume

# Complex expressions combining multiple functions
final_price = evaluate('price - calculate_discount(price, customer, quantity)', context)
# → 75.0 ($100 - $25 discount)
assert final_price == 75.0

# Conditional logic with functions
weekend_greeting = evaluate('is_weekend(today) ? "Have a great weekend!" : "Have a productive day!"', context)
# → "Have a great weekend!" (today is saturday)
assert weekend_greeting == "Have a great weekend!"

# Hash password (showing first 8 chars for brevity)
password_hash = evaluate('hash_password("secret123")', context)
# → "88a9f4259abef45a..." (SHA-256 hash)
assert password_hash.startswith("88a9f4259abef45a")

print("✓ Custom functions working correctly")
```

### Best Practices for Custom Functions

1. **Keep functions pure**: Avoid side effects when possible
2. **Handle edge cases**: Check for None/invalid inputs
3. **Use clear names**: Function names should be self-documenting
4. **Return appropriate types**: Use CEL-compatible types (int, float, str, bool, list, dict)

```python
def safe_divide(numerator, denominator):
    """Safe division that handles zero denominator."""
    if denominator == 0:
        return None  # or raise an appropriate error
    return numerator / denominator

def check_user_permission(user_id, required_permission, user_database):
    """Check if user has a specific permission."""
    user = user_database.get(user_id, {})
    permissions = user.get("permissions", [])
    return required_permission in permissions

def format_currency(amount, currency="USD"):
    """Format amount as currency string."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, "$")
    return f"{symbol}{amount:.2f}"

# Example usage with error handling
context = Context()
context.add_function("safe_divide", safe_divide)
context.add_function("check_permission", check_user_permission)
context.add_function("format_currency", format_currency)

# Test data
user_db = {
    "alice": {"permissions": ["read", "write", "admin"]},
    "bob": {"permissions": ["read"]}
}

context.add_variable("users", user_db)

# Use functions with safe patterns
result = evaluate('safe_divide(100, 0) == null', context)
# → True (division by zero returns null)
assert result == True

result = evaluate('check_permission("alice", "admin", users)', context)
# → True (alice has admin permission)
assert result == True

result = evaluate('format_currency(29.99, "EUR")', context)
# → "€29.99" (formatted with Euro symbol)
assert result == "€29.99"

print("✓ Advanced function patterns working correctly")
```

## Building Practical Policies

Now that you understand Context objects and custom functions, let's combine them to build real-world policies. CEL's true power emerges when you use it for business policies - these patterns will prepare you for the advanced use cases covered in [Access Control Policies](../how-to-guides/access-control-policies.md) and [Business Logic & Data Transformation](../how-to-guides/business-logic-data-transformation.md).

Let's build from simple rules to sophisticated access control - each example teaches patterns you'll use in production systems.

### Step 1: Simple Business Rules

Start with basic business logic to get comfortable with policy patterns:

```python
from cel import evaluate

def check_discount_eligibility(customer):
    """Simple business rule for customer discounts."""
    
    # Business rule: Customers get discounts if they are verified 
    # and have either premium status OR made 5+ orders
    discount_policy = """
        customer.verified && 
        (customer.premium || customer.order_count >= 5)
    """
    
    context = {"customer": customer}
    return evaluate(discount_policy, context)

# Test different customer scenarios
premium_customer = {"verified": True, "premium": True, "order_count": 2}
loyal_customer = {"verified": True, "premium": False, "order_count": 8}
new_customer = {"verified": True, "premium": False, "order_count": 1}

assert check_discount_eligibility(premium_customer) == True  # → True (verified + premium)
assert check_discount_eligibility(loyal_customer) == True   # → True (verified + 8 orders >= 5)
assert check_discount_eligibility(new_customer) == False   # → False (verified but only 1 order)
```

### Step 2: Multi-Factor Decision Making

Build on simple rules by adding time and context awareness:

```python
from datetime import datetime

def check_order_approval(order, current_time=None):
    """Multi-factor approval policy for orders."""
    
    if current_time is None:
        current_time = datetime.now()
    
    # Business rule: Orders are auto-approved if:
    # 1. Amount is under $1000, OR
    # 2. Customer is premium AND amount under $5000, OR  
    # 3. During business hours AND amount under $2500
    approval_policy = """
        order.amount < 1000 ||
        (order.customer.premium && order.amount < 5000) ||
        (current_hour >= 9 && current_hour <= 17 && order.amount < 2500)
    """
    
    context = {
        "order": order,
        "current_hour": current_time.hour
    }
    
    return evaluate(approval_policy, context)

# Test scenarios
small_order = {"amount": 500, "customer": {"premium": False}}
premium_order = {"amount": 3000, "customer": {"premium": True}}
business_hours_order = {"amount": 2000, "customer": {"premium": False}}

business_time = datetime.now().replace(hour=14)  # 2 PM

assert check_order_approval(small_order) == True  # → True ($500 < $1000 threshold)
assert check_order_approval(premium_order) == True  # → True (premium customer, $3000 < $5000)
assert check_order_approval(business_hours_order, business_time) == True  # → True (business hours, $2000 < $2500)
```

### Step 3: Resource Access Control

Now apply these patterns to access control - the foundation of secure applications:

```python
def check_resource_access(user, resource, action, current_time=None):
    """Production-ready access control policy."""
    
    if current_time is None:
        current_time = datetime.now()
    
    # Access control policy with multiple authorization paths:
    # 1. Admins can always access anything
    # 2. Resource owners can read/write their own resources
    # 3. Team members can read shared resources during business hours
    # 4. Public resources are readable by anyone
    access_policy = """
        user.role == "admin" ||
        (resource.owner == user.id && action in ["read", "write"]) ||
        (has(resource.team) && user.team == resource.team && action == "read" && 
         current_hour >= 9 && current_hour <= 17) ||
        (resource.public && action == "read")
    """
    
    context = {
        "user": user,
        "resource": resource,
        "action": action,
        "current_hour": current_time.hour
    }
    
    return evaluate(access_policy, context)

# Test realistic scenarios
alice = {"id": "alice", "role": "user", "team": "engineering"}
bob = {"id": "bob", "role": "admin", "team": "security"}

project_doc = {
    "id": "project_plan",
    "owner": "alice", 
    "team": "engineering",
    "public": False
}

public_doc = {"id": "company_blog", "owner": "marketing", "public": True}

# Alice can read her own document
assert check_resource_access(alice, project_doc, "read") == True  # → True (owner can read own resource)

# Admin Bob can access anything
assert check_resource_access(bob, project_doc, "write") == True  # → True (admin role grants all access)

# Anyone can read public documents
assert check_resource_access(alice, public_doc, "read") == True  # → True (public resource readable by all)

print("✓ Policy progression examples working correctly")
```

**Key Learning Points:**

- **Start Simple**: Begin with straightforward business rules before adding complexity
- **Layer Complexity**: Add factors like time, user attributes, and resource properties incrementally  
- **Test Scenarios**: Each policy should handle multiple real-world scenarios
- **Clear Intent**: Write policies that business stakeholders can understand and verify

These patterns scale from simple validation to enterprise access control systems, as you'll see in [Access Control Policies](../how-to-guides/access-control-policies.md).

## Common Expression Patterns

### Basic Comparisons
```python
context = {"score": 85, "threshold": 80}

# Numeric comparisons
result = evaluate("score > threshold", context)
# → True (85 > 80)
assert result == True
result = evaluate("score >= 90", context)
# → False (85 < 90)
assert result == False

# String comparisons  
context = {"status": "active"}
result = evaluate('status == "active"', context)
# → True (exact string match)
assert result == True
```

### Logical Operations
```python
context = {
    "user": {"verified": True, "age": 25},
    "feature_enabled": True
}

# AND logic
result = evaluate("user.verified && feature_enabled", context)
# → True (both conditions are true)
assert result == True

# OR logic  
result = evaluate("user.age < 18 || user.verified", context)
# → True (user is verified, even though age >= 18)
assert result == True

# NOT logic
result = evaluate("!user.verified", context)
# → False (user.verified is True)
assert result == False
```

### Working with Lists
```python
context = {
    "permissions": ["read", "write"],
    "numbers": [1, 2, 3, 4, 5]
}

# Check membership
result = evaluate('"write" in permissions', context)
# → True ("write" is in ["read", "write"])
assert result == True
result = evaluate('"admin" in permissions', context)
# → False ("admin" is not in ["read", "write"])
assert result == False

# List operations
result = evaluate("numbers.size()", context)
# → 5 (length of [1, 2, 3, 4, 5])
assert result == 5
result = evaluate("numbers[0]", context)
# → 1 (first element)
assert result == 1
```

### Safe Field Access
```python
# Handle optional/missing fields safely
context = {"user": {"name": "Charlie"}}  # No "age" field

# Check if field exists before using it
result = evaluate('has(user.age) && user.age > 18', context)
# → False (user.age field doesn't exist)
assert result == False

# Use has() for safe access with fallback
result = evaluate('has(user.age) ? user.age >= 18 : false', context)
# → False (user.age doesn't exist, fallback to false)
assert result == False
```

## Error Handling

CEL expressions can fail for various reasons. Handle errors gracefully:

```python
from cel import evaluate

def safe_evaluate(expression, context):
    """Evaluate with basic error handling."""
    try:
        return evaluate(expression, context)
    except ValueError as e:
        return f"Invalid syntax: {e}"
    except TypeError as e:
        return f"Type error: {e}"
    except RuntimeError as e:
        return f"Runtime error: {e}"

# Examples
context = {"x": 10}

# Valid expression
result = safe_evaluate("x * 2", context)
# → 20 (10 * 2)
assert result == 20

# Syntax error
result = safe_evaluate("x + + 2", context)
assert "Invalid syntax" in str(result) or "error" in str(result)

# Missing variable
result = safe_evaluate("y * 2", context)
assert isinstance(result, str) and "error" in result.lower()

# Type mismatch
result = safe_evaluate('"hello" + 42', context)
assert isinstance(result, str) and "error" in result.lower()
```

## Quick Wins - Real Examples

### Configuration Validation
```python
config = {
    "database": {"host": "localhost", "port": 5432},
    "cache": {"enabled": True, "ttl": 300},
    "features": {"ssl_enabled": True}
}

# Validate configuration
rules = [
    'config.database.port > 0 && config.database.port < 65536',
    'config.cache.ttl >= 60',
    'config.features.ssl_enabled == true'
]

for rule in rules:
    result = evaluate(rule, {"config": config})
    # → True (all config values meet validation criteria)
    assert result == True, f"Config validation failed: {rule}"
```

### Feature Flags
```python
user_context = {
    "user": {"id": "user123", "beta_tester": True},
    "feature_flags": {"new_ui": True, "advanced_search": False}
}

# Check if user should see new UI
show_new_ui = evaluate(
    "feature_flags.new_ui && user.beta_tester", 
    user_context
)
# → True (feature enabled AND user is beta tester)
assert show_new_ui == True
```

### Input Validation
```python
form_data = {
    "email": "user@example.com",
    "age": 25,
    "terms_accepted": True
}

# Validate form input
validations = [
    'email.contains("@")',
    'age >= 18 && age <= 120', 
    'terms_accepted == true'
]

all_valid = all(
    evaluate(rule, form_data) 
    for rule in validations
)
# → True (all validation rules pass: email has @, age in range, terms accepted)
assert all_valid == True
```

## What's Next?

Congratulations! You've mastered the Context class and custom Python functions. Now you can build sophisticated applications with CEL. Choose your next step based on your goals:

**📚 Fill Knowledge Gaps:**
- **[CEL Language Basics](cel-language-basics.md)** - Complete syntax reference if you need to look up specific features
- **[Thinking in CEL](thinking-in-cel.md)** - Understand CEL's philosophy and design principles

**🚀 Add Advanced Capabilities:**
- **[Extending CEL](extending-cel.md)** - Advanced Context patterns, function best practices, and testing strategies
- **[Error Handling Guide](../how-to-guides/error-handling.md)** - Production-ready error handling and validation

**🏢 Build Production Applications:**
- **[Access Control Policies](../how-to-guides/access-control-policies.md)** - Start here for permission systems and security rules
- **[Business Logic & Data Transformation](../how-to-guides/business-logic-data-transformation.md)** - Configurable rule engines and data processing
- **[Production Patterns & Best Practices](../how-to-guides/production-patterns-best-practices.md)** - Flask/FastAPI integration, performance, and security

**💡 Recommended Next Steps:**

1. **For Security Applications:** Go to [Access Control Policies](../how-to-guides/access-control-policies.md) - You have the foundation to build enterprise-grade permission systems

2. **For Business Applications:** Try [Business Logic & Data Transformation](../how-to-guides/business-logic-data-transformation.md) - Apply what you've learned to real business rules

3. **For Advanced Usage:** Read [Extending CEL](extending-cel.md) - Learn advanced patterns and best practices

You're now ready to handle thousands of policies in production systems!