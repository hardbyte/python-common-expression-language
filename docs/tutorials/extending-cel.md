# Extending CEL: Context and Custom Functions

You've learned the basics in [Your First Integration](your-first-integration.md) - now let's dive deeper into advanced Context patterns, function best practices, and testing strategies. This tutorial takes you from functional to production-ready CEL implementations.

> **Prerequisites:** Complete [Your First Integration](your-first-integration.md) to understand Context basics and custom function registration. This tutorial assumes you're comfortable with the fundamental concepts.

**What You'll Master:** Advanced Context patterns, reusable context builders, function best practices, comprehensive error handling, and testing strategies for production CEL implementations.

## The Context Class

While dictionary context works well for simple cases, the `Context` class provides more control and features for complex applications.

### Basic Context Usage

```python
from cel import evaluate, Context

# Create a context object
context = Context()

# Add variables one by one
context.add_variable("user_name", "Alice")
context.add_variable("user_age", 30)
context.add_variable("permissions", ["read", "write"])

# Use the context
result = evaluate("user_name + ' is ' + string(user_age)", context)
assert result == "Alice is 30"  # → String concatenation with type conversion

result = evaluate('"write" in permissions', context)
assert result == True  # → List membership check for permissions
```

### Adding Multiple Variables

```python
from cel import Context, evaluate

context = Context()

# Add multiple variables at once
context.update({
    "user": {
        "id": "user123",
        "name": "Bob",
        "email": "bob@example.com",
        "verified": True
    },
    "session": {
        "created_at": "2024-01-01T10:00:00Z",
        "expires_at": "2024-01-01T18:00:00Z"
    },
    "environment": "production"
})

# Complex expressions with nested data
policy = """
    user.verified && 
    environment == "production" &&
    user.email.endsWith("@example.com")
"""

result = evaluate(policy, context)
assert result == True  # → Complex multi-condition policy evaluation
```

### Context vs Dictionary - When to Use Which?

**Use Dictionary Context when:**
- Simple, one-off expressions
- Static data that doesn't change
- Quick prototyping or testing

**Use Context Class when:**
- Adding custom functions
- Building reusable evaluation environments
- Need to modify context dynamically
- Working with complex, evolving data structures

**Step 1: Simple Dictionary Example**
```python
# Simple case - dictionary is fine
result = evaluate("x + y", {"x": 10, "y": 20})
assert result == 30  # → Basic arithmetic with dictionary context
```

**Step 2: Define Custom Functions**
```python
# Complex case requires custom functions
def email_validator(email):
    return "@" in email and "." in email

def password_hasher(password):
    return f"hash_{len(password)}"

def check_permissions():
    return True
```

**Step 3: Create Context and Register Functions**
```python
context = Context()
context.add_function("validate_email", email_validator)
context.add_function("hash_password", password_hasher)
context.add_function("check_permissions", check_permissions)
```

**Step 4: Add Variables and Evaluate**
```python
context.add_variable("base_config", {"database": {"host": "localhost", "port": 5432}})
context.add_variable("user", {"email": "test@example.com"})

result = evaluate("validate_email(user.email) && check_permissions()", context)
assert result == True  # → Custom function orchestration for business logic
```

## Custom Functions

One of CEL's most powerful features is the ability to call Python functions from within expressions.

### Basic Function Registration

**Step 1: Define Your Functions**
```python
from cel import Context, evaluate

def calculate_tax(income, rate=0.1):
    """Calculate tax based on income and rate."""
    return income * rate

def is_valid_email(email):
    """Simple email validation."""
    return "@" in email and "." in email
```

**Step 2: Create Context and Register Functions**
```python
tax_context = Context()
tax_context.add_function("calculate_tax", calculate_tax)
tax_context.add_function("is_valid_email", is_valid_email)
```

**Step 3: Add Variables**
```python
tax_context.add_variable("user_income", 50000)
tax_context.add_variable("user_email", "alice@example.com")
```

**Step 4: Evaluate Expressions**
```python
tax_result = evaluate("calculate_tax(user_income, 0.15)", tax_context)
assert tax_result == 7500.0  # → Function with parameters: 50000 * 0.15

email_result = evaluate("is_valid_email(user_email)", tax_context)
assert email_result == True  # → Validation function returns boolean
```

### Functions with Complex Logic

**Step 1: Define Complex Business Functions**
```python
from cel import Context, evaluate

def score_calculation(base_score, bonus_multiplier):
    """Calculate final score with bonus."""
    return base_score * bonus_multiplier

def is_prime(n):
    """Check if number is prime (simple implementation)."""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

def format_user_info(name, age, department):
    """Format user information string."""
    return f"{name} ({age}) from {department}"
```

**Step 2: Create Context and Register Functions**
```python
demo_context = Context()
demo_context.add_function("score_calculation", score_calculation)
demo_context.add_function("is_prime", is_prime)  
demo_context.add_function("format_user_info", format_user_info)
```

**Step 3: Add Test Data**
```python
demo_context.update({
    "employee": {
        "name": "Alice",
        "age": 25,
        "department": "Engineering",
        "base_score": 85
    },
    "config": {
        "bonus_active": True,
        "multiplier": 1.2
    }
})
```

**Step 4: Test Individual Functions**
```python
calc_result = evaluate("score_calculation(employee.base_score, config.multiplier)", demo_context)
assert calc_result == 102.0  # → Mathematical function: 85 * 1.2

prime_check = evaluate("is_prime(employee.age)", demo_context)
assert prime_check == False  # → Algorithmic function: 25 is not prime

info_text = evaluate('format_user_info(employee.name, employee.age, employee.department)', demo_context)
assert info_text == "Alice (25) from Engineering"  # → String formatting function
```

**Step 5: Combine Functions in Complex Rules**
```python
business_rule = """
    config.bonus_active && 
    score_calculation(employee.base_score, config.multiplier) > 100 &&
    employee.age >= 18
"""

final_result = evaluate(business_rule, demo_context)
assert final_result == True  # → Complex business rule combining multiple functions

print("✓ Complex validation functions working correctly")
```

## Practical Example: Business Rules Engine

Now let's see how to combine custom functions for a real-world application - a business rules engine:

**Step 1: Define Business Validation Functions**
```python
from cel import Context, evaluate
import re
from datetime import datetime, timedelta

def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def days_until_expiry(expiry_date_str):
    """Calculate days until expiry."""
    try:
        expiry = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
        now = datetime.now()
        # Remove timezone info for comparison
        expiry_naive = expiry.replace(tzinfo=None)
        delta = expiry_naive - now
        return max(0, delta.days)
    except:
        return 0

def user_has_permission(user_id, permission, permissions_db):
    """Check if user has specific permission."""
    user_perms = permissions_db.get(user_id, [])
    return permission in user_perms
```

**Step 2: Create Business Rules Context**
```python
def create_business_rules_context():
    """Create a context with business validation functions."""
    context = Context()
    
    # Register all functions
    context.add_function("validate_password", validate_password)
    context.add_function("days_until_expiry", days_until_expiry)
    context.add_function("user_has_permission", user_has_permission)
    
    return context

business_context = create_business_rules_context()
```

**Step 3: Add Business Data**
```python
business_context.update({
    "user": {
        "id": "user123",
        "password": "MySecure123",
        "subscription_expires": "2030-12-31T23:59:59Z",
        "verified": True
    },
    "permissions_db": {
        "user123": ["read", "write", "admin"]
    }
})
```

**Step 4: Define Business Rules**
```python
account_access_rule = """
    user.verified &&
    validate_password(user.password) &&
    days_until_expiry(user.subscription_expires) > 30 &&
    user_has_permission(user.id, "admin", permissions_db)
"""

admin_actions_rule = """
    user_has_permission(user.id, "admin", permissions_db) &&
    days_until_expiry(user.subscription_expires) > 0
"""
```

**Step 5: Evaluate and Test Rules**
```python
# Test valid user
can_access_account = evaluate(account_access_rule, business_context)
can_perform_admin_actions = evaluate(admin_actions_rule, business_context)

assert can_access_account == True  # → Enterprise access control validation
assert can_perform_admin_actions == True  # → Admin privilege verification

# Test with invalid user
business_context.add_variable("user", {
    "id": "user456", 
    "password": "weak",  # Fails password validation
    "subscription_expires": "2023-01-01T00:00:00Z",  # Expired
    "verified": False
})

expired_user_access = evaluate(account_access_rule, business_context)
assert expired_user_access == False  # → Security policy correctly denies access

print("✓ Business rules engine working correctly")
```

This example demonstrates how custom functions enable complex business logic while keeping CEL expressions readable and maintainable.

### Function Best Practices

These patterns become essential when building production applications like those shown in [Access Control Policies](../how-to-guides/access-control-policies.md) and [Production Patterns & Best Practices](../how-to-guides/production-patterns-best-practices.md).

#### 1. Error Handling

**Step 1: Define Error-Safe Functions**
```python
def check_user_exists(user_id, database):
    """Check if user exists in database."""
    return user_id in database

def get_user_status(user_id, database):
    """Get user status safely."""
    user = database.get(user_id)
    return user.get("status", "unknown") if user else "not_found"

def safe_divide(a, b):
    """Division with error handling."""
    try:
        if b == 0:
            return float('inf')
        return a / b
    except Exception:
        return 0
```

**Step 2: Register Functions and Add Test Data**
```python
error_context = Context()
error_context.add_function("check_user_exists", check_user_exists)
error_context.add_function("get_user_status", get_user_status)
error_context.add_function("safe_divide", safe_divide)
error_context.add_variable("users_db", {
    "user123": {"name": "Alice", "status": "active"}
})
```

**Step 3: Test Error Handling**
```python
# Test individual safety functions
exists_check = evaluate('check_user_exists("user123", users_db)', error_context)
assert exists_check == True  # → Database existence check with error safety

status_check = evaluate('get_user_status("user123", users_db) == "active"', error_context)
assert status_check == True  # → Status validation with fallback handling

# Test combined safety check
safety_result = evaluate("""
    check_user_exists("user123", users_db) && 
    get_user_status("user123", users_db) == "active"
""", error_context)
assert safety_result == True  # → Chained safety validations for robustness
```

#### 2. Pure Functions (Recommended)

**Step 1: Define Pure Function**
```python
# ✅ Good - pure function (no side effects)
def format_currency(amount, currency="USD"):
    """Format amount as currency string."""
    return f"{currency} {amount:.2f}"
```

**Step 2: Register Function and Add Variables**
```python
currency_context = Context()
currency_context.add_function("format_currency", format_currency)
currency_context.add_variable("price", 29.99)
```

**Step 3: Test Pure Function**
```python
currency_result = evaluate('format_currency(price)', currency_context)
assert currency_result == "USD 29.99"  # → Pure function with default parameter

eur_result = evaluate('format_currency(price, "EUR")', currency_context)
assert eur_result == "EUR 29.99"  # → Pure function with explicit parameter

print("✓ Pure functions working correctly")
```

## Advanced Context Patterns

The Context patterns you learned in [Your First Integration](your-first-integration.md) work well for individual policies. But for complex applications that manage many policies and contexts - like the enterprise systems covered in [Access Control Policies](../how-to-guides/access-control-policies.md) - you need more scalable architectures.

These patterns provide the foundation for production-ready systems:

### Context Builders for Reusability

**Complete PolicyContext Implementation**
```python
from cel import Context, evaluate
from datetime import datetime

class PolicyContext:
    """Reusable context builder for policy evaluation."""
    
    def __init__(self):
        self.context = Context()
        self._setup_common_functions()
    
    def _setup_common_functions(self):
        """Set up commonly used functions."""
        def current_time():
            return datetime.now()
        
        def is_business_hours():
            # For testing purposes, always return True
            # In production, use: datetime.now().hour to check 9 <= hour <= 17
            return True
        
        def contains_any(text, keywords):
            """Check if text contains any of the keywords."""
            return any(keyword.lower() in text.lower() for keyword in keywords)
        
        self.context.add_function("current_time", current_time)
        self.context.add_function("is_business_hours", is_business_hours)
        self.context.add_function("contains_any", contains_any)
    
    def add_user(self, user_data):
        """Add user information to context."""
        self.context.add_variable("user", {
            "id": user_data.get("id"),
            "name": user_data.get("name"),
            "email": user_data.get("email"),
            "roles": user_data.get("roles", []),
            "verified": user_data.get("verified", False),
            "department": user_data.get("department", "unknown")
        })
        return self
    
    def add_resource(self, resource_data):
        """Add resource information to context."""
        self.context.add_variable("resource", {
            "id": resource_data.get("id"),
            "type": resource_data.get("type"),
            "owner": resource_data.get("owner"),
            "public": resource_data.get("public", False),
            "tags": resource_data.get("tags", [])
        })
        return self
    
    def add_request_info(self, method, path, ip_address):
        """Add request information to context."""
        self.context.add_variable("request", {
            "method": method,
            "path": path,
            "ip": ip_address,
            "time": datetime.now().isoformat()
        })
        return self
    
    def evaluate_policy(self, policy_expression):
        """Evaluate a policy expression with this context."""
        return evaluate(policy_expression, self.context)
```

**Using the Context Builder**
```python
policy_ctx = PolicyContext()
policy_ctx.add_user({
    "id": "alice",
    "name": "Alice Smith",
    "email": "alice@company.com", 
    "roles": ["user", "developer"],
    "verified": True,
    "department": "engineering"
}).add_resource({
    "id": "project-x",
    "type": "repository",
    "owner": "alice",
    "public": False,
    "tags": ["python", "web"]
}).add_request_info("GET", "/api/projects/project-x", "192.168.1.100")
```

**Step 5: Define and Evaluate Policy**
```python
access_policy = """
    user.verified &&
    (user.id == resource.owner || "admin" in user.roles) &&
    is_business_hours() &&
    contains_any(resource.type, ["repository", "document"])
"""

access_granted = policy_ctx.evaluate_policy(access_policy)
assert access_granted == True  # → Enterprise policy with reusable context builder
```

### Context Inheritance and Composition

**Step 1: Create Base Context Class**
```python
from cel import Context

class BaseContext:
    """Base context with common functions."""
    
    def __init__(self):
        self.context = Context()
        self._add_base_functions()
    
    def _add_base_functions(self):
        def string_length(s):
            return len(str(s))
        
        def is_empty(value):
            if value is None:
                return True
            if isinstance(value, (str, list, dict)):
                return len(value) == 0
            return False
        
        self.context.add_function("string_length", string_length)
        self.context.add_function("is_empty", is_empty)
```

**Step 2: Create Specialized Web Context**
```python
class WebAppContext(BaseContext):
    """Extended context for web applications."""
    
    def __init__(self):
        super().__init__()
        self._add_web_functions()
    
    def _add_web_functions(self):
        def is_safe_redirect(url):
            """Check if URL is safe for redirects."""
            dangerous_schemes = ["javascript:", "data:", "vbscript:"]
            return not any(url.lower().startswith(scheme) for scheme in dangerous_schemes)
        
        def extract_domain(email):
            """Extract domain from email address."""
            return email.split("@")[-1] if "@" in email else ""
        
        self.context.add_function("is_safe_redirect", is_safe_redirect)
        self.context.add_function("extract_domain", extract_domain)
```

**Step 3: Use Inherited Context**
```python
web_context = WebAppContext()
web_context.context.update({
    "redirect_url": "https://example.com/dashboard",
    "user_email": "alice@company.com"
})

safety_check = evaluate("""
    is_safe_redirect(redirect_url) && 
    extract_domain(user_email) == "company.com"
""", web_context.context)

assert safety_check == True  # → Inherited context with specialized web functions
```

## Testing Custom Functions

Always test your custom functions thoroughly:

```python
import pytest
from cel import Context, evaluate

def test_custom_functions():
    """Test custom function behavior."""
    
    def divide_safely(a, b):
        if b == 0:
            return float('inf')
        return a / b
    
    context = Context()
    context.add_function("divide_safely", divide_safely)
    
    # Test normal division
    result = evaluate("divide_safely(10, 2)", context)
    assert result == 5.0  # → Safe division function handles normal cases
    
    # Test division by zero
    result = evaluate("divide_safely(10, 0)", context)
    assert result == float('inf')  # → Graceful error handling returns infinity
    
    # Test with context variables
    context.add_variable("numerator", 15)
    context.add_variable("denominator", 3)
    result = evaluate("divide_safely(numerator, denominator)", context)
    assert result == 5.0  # → Function integration with context variables

def test_context_isolation():
    """Test that contexts don't interfere with each other."""
    
    context1 = Context()
    context1.add_variable("value", 10)
    
    context2 = Context()
    context2.add_variable("value", 20)
    
    result1 = evaluate("value * 2", context1)
    result2 = evaluate("value * 2", context2)
    
    assert result1 == 20  # → First context: 10 * 2
    assert result2 == 40  # → Second context: 20 * 2, isolated state

if __name__ == "__main__":
    test_custom_functions()
    test_context_isolation()
    # All tests passed!
else:
    # Execute tests when running through mktestdocs
    test_custom_functions()
    test_context_isolation()
```

## What You've Achieved

You now have the advanced skills needed for production CEL implementations:

✅ **Advanced Context Management** - Context builders, inheritance, and composition patterns  
✅ **Production-Quality Functions** - Error handling, pure functions, and comprehensive testing  
✅ **Scalable Architectures** - Reusable context builders for complex applications  
✅ **Testing Strategies** - Isolated testing and validation patterns  

## Ready for Production?

Choose your next step based on what you want to build:

**🔒 Security & Access Control:**
- **[Access Control Policies](../how-to-guides/access-control-policies.md)** - Apply these advanced patterns to build enterprise permission systems

**💼 Business Applications:**
- **[Business Logic & Data Transformation](../how-to-guides/business-logic-data-transformation.md)** - Build configurable rule engines with advanced Context patterns

**🚀 Production Deployment:**
- **[Production Patterns & Best Practices](../how-to-guides/production-patterns-best-practices.md)** - Performance optimization, security, and integration patterns
- **[Error Handling Guide](../how-to-guides/error-handling.md)** - Robust error handling for production systems

**📖 Reference Material:**
- **[Python API Reference](../reference/python-api.md)** - Complete API documentation for advanced usage
- **[CEL Compliance](../reference/cel-compliance.md)** - Feature support and limitations

**💡 Pro Tip:** With these advanced skills, you're ready to tackle enterprise-scale applications. Start with [Access Control Policies](../how-to-guides/access-control-policies.md) or [Business Logic & Data Transformation](../how-to-guides/business-logic-data-transformation.md) based on your use case.

Remember: CEL's power comes from combining simple, safe expressions with custom functions that encapsulate your business logic. You now have the tools to build production-ready systems!
