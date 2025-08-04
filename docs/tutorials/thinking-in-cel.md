# Thinking in CEL: Core Concepts

Before diving deeper into CEL, let's step back and understand what makes CEL fundamentally different from other expression languages. Whether you're coming from [Quick Start](../getting-started/quick-start.md) or planning your first integration, understanding CEL's philosophy will help you make better design decisions.

> **When to Read This:** This tutorial is valuable at any stage - whether you're just getting started or already building applications. The concepts here will help you choose the right tool for the job and design better CEL-based solutions.

**What You'll Learn:** By the end of this tutorial, you'll understand CEL's design philosophy, know when to use CEL vs other solutions, and have the mental models needed to design effective CEL-based systems.

## What Makes CEL Special

### Non-Turing Complete by Design

CEL is intentionally **not** a general-purpose programming language. You can't write loops, define functions, or perform I/O operations. This limitation is actually CEL's greatest strength.

```python
from cel import evaluate

# ✅ This works - safe expression evaluation
result = evaluate("user.age >= 18 && user.verified", {"user": {"age": 25, "verified": True}})
assert result == True

# ❌ This is impossible - no loops or side effects
# No way to write: for user in users: send_email(user)
# No way to write: delete_file("/important/data")
```

**Why this matters:**

- **Guaranteed termination**: Every CEL expression will finish executing
- **No side effects**: Expressions can't modify data or call external services
- **Predictable resource usage**: No infinite loops or recursive calls
- **Safe for untrusted input**: Users can write expressions without security risks

### Declarative, Not Imperative

CEL expressions describe **what** you want, not **how** to compute it.

```python
from cel import evaluate

# Declarative: "I want users who are adults and verified"
user_filter = "user.age >= 18 && user.verified"

# Test with valid user
result = evaluate(user_filter, {"user": {"age": 25, "verified": True}})
assert result == True

# Test with unverified user
result = evaluate(user_filter, {"user": {"age": 25, "verified": False}})
assert result == False

# Compare to imperative Python:
# if user.age >= 18:
#     if user.verified:
#         return True
#     else:
#         return False
# else:
#     return False
```

This declarative nature makes CEL expressions:

- **Easier to reason about**: The intent is clear from reading the expression
- **Language-agnostic**: The same expression works across different platforms
- **Portable**: Expressions can be stored in databases, config files, or transmitted over networks

### Idempotent and Deterministic

CEL expressions always return the same result given the same input.

```python
from cel import evaluate

# This expression will ALWAYS return the same result for the same user
policy = "user.role == 'admin' || (user.department == 'IT' && user.yearsOfService > 2)"

# Test admin user
result = evaluate(policy, {"user": {"role": "admin", "department": "sales", "yearsOfService": 1}})
assert result == True

# Test experienced IT user
result = evaluate(policy, {"user": {"role": "user", "department": "IT", "yearsOfService": 3}})
assert result == True

# Test new IT user
result = evaluate(policy, {"user": {"role": "user", "department": "IT", "yearsOfService": 1}})
assert result == False

# No hidden state, no random numbers, no time-dependent behavior
# (unless you explicitly provide time in the context)
```

## When to Choose CEL

### ✅ Perfect Use Cases

**Policy and Rules Engines**
```python
from cel import evaluate

# Business rules that change frequently
pricing_rule = "base_price * (1 + tax_rate) * (premium_customer ? 0.9 : 1.0)"
result = evaluate(pricing_rule, {
    "base_price": 100.0,
    "tax_rate": 0.08,
    "premium_customer": True
})
assert result == 97.2  # 100 * 1.08 * 0.9

# Access control policies
access_policy = """
  user.role == 'admin' || 
  (resource.owner == user.id && action in ['read', 'update']) ||
  (resource.public && action == 'read')
"""
result = evaluate(access_policy, {
    "user": {"role": "admin", "id": "user1"},
    "resource": {"owner": "user2", "public": False},
    "action": "delete"
})
assert result == True  # Admin can do anything
```

**Configuration Validation**
```python
from cel import evaluate

# Validate complex configuration without writing code
validation_rules = [
    "config.database.port > 0 && config.database.port < 65536",
    "config.cache.ttl >= 60",  # At least 1 minute
    "config.features.ssl_enabled || config.environment == 'development'"
]

# Test valid configuration
config = {
    "config": {
        "database": {"port": 5432},
        "cache": {"ttl": 300},
        "features": {"ssl_enabled": True},
        "environment": "production"
    }
}

for rule in validation_rules:
    result = evaluate(rule, config)
    assert result == True
```

**Data Filtering and Transformation**
```python
from cel import evaluate

# Dynamic filters for APIs
user_filter = "user.active && user.department in ['engineering', 'product']"
result = evaluate(user_filter, {
    "user": {"active": True, "department": "engineering"}
})
assert result == True

# Data transformation
score_calculation = "base_score * effort_multiplier + bonus_points"
result = evaluate(score_calculation, {
    "base_score": 80,
    "effort_multiplier": 1.2,
    "bonus_points": 10
})
assert result == 106.0  # 80 * 1.2 + 10
```

### ❌ When NOT to Use CEL

**Complex Business Logic**
```python
# Don't use CEL for multi-step processes
# Use Python instead:
def complex_approval_workflow(request):
    if request.amount > 10000:
        return "executive_approval"  # route_to_executive_approval(request)
    elif request.department == "finance":
        return "finance_approval"   # route_to_finance_approval(request)
    else:
        return "auto_approve"       # auto_approve(request)

# Test the function
class MockRequest:
    def __init__(self, amount, department):
        self.amount = amount
        self.department = department

result = complex_approval_workflow(MockRequest(15000, "engineering"))
assert result == "executive_approval"

result = complex_approval_workflow(MockRequest(5000, "finance"))
assert result == "finance_approval"

result = complex_approval_workflow(MockRequest(1000, "marketing"))
assert result == "auto_approve"
```

**I/O Operations**
```python
# CEL can't do this - use Python
def send_notification(user, message):
    # email_service.send(user.email, message)
    # slack_service.post(user.slack_id, message)
    return f"Sent '{message}' to {user['email']} and {user['slack_id']}"

# Test the function
user = {"email": "test@example.com", "slack_id": "@test"}
result = send_notification(user, "Hello!")
assert "Sent 'Hello!' to test@example.com and @test" == result
```

**Stateful Operations**
```python
# CEL can't track state across evaluations
class RateLimiter:
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, user_id, max_requests=100):
        # Track request counts over time
        current_count = self.requests.get(user_id, 0)
        if current_count < max_requests:
            self.requests[user_id] = current_count + 1
            return True
        return False

# Test the class
rate_limiter = RateLimiter()
assert rate_limiter.is_allowed("user1", max_requests=2) == True
assert rate_limiter.is_allowed("user1", max_requests=2) == True
assert rate_limiter.is_allowed("user1", max_requests=2) == False
```

## Core Principles for Effective CEL

### 1. Design for Humans

CEL expressions should be readable by non-programmers. Business users should be able to understand and potentially modify them.

```python
from cel import evaluate

# ✅ Clear and readable
clear_rule = "order.total > 100 && customer.loyalty_tier == 'gold'"
result = evaluate(clear_rule, {
    "order": {"total": 150},
    "customer": {"loyalty_tier": "gold"}
})
assert result == True

# ❌ Too cryptic - avoid this style
cryptic_rule = "o.t > 1e2 && c.lt == 'g'"
result = evaluate(cryptic_rule, {
    "o": {"t": 150},
    "c": {"lt": "g"}
})
assert result == True  # Works but hard to understand
```

### 2. Keep Context Simple

Provide clean, well-structured data to your expressions.

```python
from cel import evaluate

# ✅ Clean, structured context
context = {
    "user": {
        "id": "user123",
        "role": "admin",
        "permissions": ["read", "write", "delete"]
    },
    "resource": {
        "type": "document",
        "owner": "user123",
        "public": False
    },
    "action": "delete"
}

policy = "user.role == 'admin' || (resource.owner == user.id && 'delete' in user.permissions)"
result = evaluate(policy, context)
assert result == True
```

### 3. Test Your Expressions

CEL expressions are code - treat them as such with proper testing.

```python
import pytest
from cel import evaluate

def test_admin_access():
    context = {
        "user": {"role": "admin"},
        "resource": {"type": "document"},
        "action": "delete"
    }
    policy = "user.role == 'admin'"
    assert evaluate(policy, context) == True

def test_owner_access():
    context = {
        "user": {"id": "user123", "role": "user"},
        "resource": {"owner": "user123"},
        "action": "read"
    }
    policy = "resource.owner == user.id"
    assert evaluate(policy, context) == True

# Execute the test functions
test_admin_access()
test_owner_access()
```

### 4. Use Type-Safe Patterns

Always check for field existence when dealing with optional data.

```python
from cel import evaluate

# ✅ Safe - check existence first
safe_expression = 'has(user.profile) && user.profile.verified'
result = evaluate(safe_expression, {"user": {"profile": {"verified": True}}})
assert result == True

result = evaluate(safe_expression, {"user": {}})
assert result == False

# ❌ Unsafe - will fail if profile doesn't exist
unsafe_expression = 'user.profile.verified'
result = evaluate(unsafe_expression, {"user": {"profile": {"verified": True}}})
assert result == True

# This would fail: evaluate(unsafe_expression, {"user": {}})
```

### 5. Document Your Context Schema

Make it clear what data your expressions expect.

```python
from cel import evaluate

# Expected context schema:
# {
#     "user": {
#         "id": str,
#         "role": str ("admin" | "user" | "guest"),
#         "department": str,
#         "verified": bool
#     },
#     "resource": {
#         "type": str,
#         "owner": str,
#         "public": bool
#     },
#     "action": str ("read" | "write" | "delete")
# }

access_policy = """
    user.role == 'admin' || 
    (resource.public && action == 'read') ||
    (resource.owner == user.id && action in ['read', 'write'])
"""

# Test the access policy
test_context = {
    "user": {"id": "user1", "role": "user", "department": "engineering", "verified": True},
    "resource": {"type": "document", "owner": "user1", "public": False},
    "action": "read"
}

result = evaluate(access_policy, test_context)
assert result == True  # User can read their own resource
```

## Mental Model: CEL as a Smart Calculator

As you move from understanding CEL conceptually to building applications (like in [Your First Integration](your-first-integration.md)), this mental model will guide your design decisions.

Think of CEL as a very smart calculator that can work with complex data structures. You give it:

1. **An expression** (the calculation you want)
2. **Context data** (the numbers/values to work with)
3. **Get a result** (always the same for the same inputs)

```python
from cel import evaluate

# Like a calculator, but for complex logic
expression = "price * quantity * (1 + tax_rate) * (customer.vip ? 0.9 : 1.0)"
context = {
    "price": 29.99,
    "quantity": 2, 
    "tax_rate": 0.08,
    "customer": {"vip": True}
}

total = evaluate(expression, context)  # 58.38 (with VIP discount)
assert abs(total - 58.3006) < 0.001  # 29.99 * 2 * 1.08 * 0.9
```

This mental model helps you understand CEL's boundaries:
- Calculators don't send emails → CEL doesn't do I/O
- Calculators don't remember previous calculations → CEL doesn't have state  
- Calculators always give the same answer → CEL is deterministic

## Understanding CEL's Place in Your Architecture

Now that you understand CEL's philosophy, you can make informed decisions about where and how to use it:

**💡 Key Insight:** CEL's constraints are features, not limitations. They make your applications more predictable, secure, and maintainable.

## What's Next?

Choose your path based on your current experience and goals:

**🚀 Ready to Start Building:**
- **[Your First Integration](your-first-integration.md)** - Learn Context objects and custom Python functions
- **[CEL Language Basics](cel-language-basics.md)** - Complete syntax reference for quick lookup

**🔧 Build Advanced Features:**
- **[Extending CEL](extending-cel.md)** - Advanced patterns and production-ready implementations

**🏢 Solve Specific Problems:**
- **[Access Control Policies](../how-to-guides/access-control-policies.md)** - Perfect CEL use case - policies and security rules
- **[Business Logic & Data Transformation](../how-to-guides/business-logic-data-transformation.md)** - Configurable business rules and validation
- **[Production Patterns & Best Practices](../how-to-guides/production-patterns-best-practices.md)** - Deploy CEL safely in production

**💡 Recommended Learning Paths:**

- **New to CEL:** Thinking in CEL → [Your First Integration](your-first-integration.md) → [Access Control Policies](../how-to-guides/access-control-policies.md)
- **Have CEL experience:** Use this as a design reference when building complex applications
- **Evaluating CEL:** This tutorial + [CEL Compliance](../reference/cel-compliance.md) will help you decide if CEL fits your needs

Armed with these concepts, you're ready to build safe, maintainable, and powerful expression-based systems!