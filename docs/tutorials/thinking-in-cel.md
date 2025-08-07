# Thinking in CEL: Core Concepts

Before diving deeper into CEL, let's step back and understand what makes CEL fundamentally different from other expression languages. Whether you're coming from [Quick Start](../getting-started/quick-start.md) or planning your first integration, understanding CEL's philosophy will help you make better design decisions.

## 🎯 When to Use CEL (Quick Decision Guide)

### ✅ **Perfect For**
- **Policy & rules engines** that change frequently
- **Configuration validation** without custom code
- **Data filtering & transformation** with user input
- **Access control** where business users need to understand rules
- **Safe evaluation** of untrusted expressions

### ❌ **Not Suitable For**
- **Complex multi-step workflows** with branching logic
- **I/O operations** (file access, network calls, database queries)
- **Stateful operations** that need to remember previous results
- **Performance-critical** tight loops (use native code instead)

> **🔒 Security Advantage:** CEL expressions can be safely stored in databases or edited by non-developers without code-execution risks. No `eval()` dangers.

**What You'll Learn:** By the end of this tutorial, you'll understand CEL's design philosophy, know when to use CEL vs other solutions, and have the mental models needed to design effective CEL-based systems.

## What Makes CEL Special

### Non-Turing Complete by Design

CEL is intentionally **not** a general-purpose programming language. You can't write loops, define functions, or perform I/O operations. This limitation is actually CEL's greatest strength.

```python
from cel import evaluate

# ✅ This works - safe expression evaluation
result = evaluate("user.age >= 18 && user.verified", {"user": {"age": 25, "verified": True}})
assert result == True  # → True (adult verified user)

# ❌ This is impossible - no loops or side effects
# No way to write: for user in users: send_email(user)
# No way to write: delete_file("/important/data")
```

**Why this matters:**

- **Guaranteed termination**: Every CEL expression will finish executing
- **No side effects**: Expressions can't modify data or call external services
- **Predictable resource usage**: No infinite loops or recursive calls
- **Safe for untrusted input**: Users can write expressions without security risks

**💡 Takeaway: CEL's limitations are security features — expressions always terminate safely.**

### Declarative, Not Imperative

CEL expressions describe **what** you want, not **how** to compute it.

```python
from cel import evaluate

# Declarative: "I want users who are adults and verified"
user_filter = "user.age >= 18 && user.verified"

# Test cases
test_cases = [
    ({"user": {"age": 25, "verified": True}}, True),   # Valid adult
    ({"user": {"age": 25, "verified": False}}, False), # Unverified
    ({"user": {"age": 16, "verified": True}}, False),  # Minor
]

for context, expected in test_cases:
    result = evaluate(user_filter, context)
    assert result == expected
```

This declarative nature makes CEL expressions:

- **Easier to reason about**: The intent is clear from reading the expression
- **Language-agnostic**: The same expression works across different platforms
- **Portable**: Expressions can be stored in databases, config files, or transmitted over networks

**💡 Takeaway: Write business intent, not implementation steps — CEL handles the "how" for you.**

### Idempotent and Deterministic

CEL expressions always return the same result given the same input.

```python
from cel import evaluate

# This expression will ALWAYS return the same result for the same user
policy = "user.role == 'admin' || (user.department == 'IT' && user.yearsOfService > 2)"

# Compact test table
test_scenarios = [
    ({"role": "admin", "department": "sales", "yearsOfService": 1}, True),    # Admin override
    ({"role": "user", "department": "IT", "yearsOfService": 3}, True),       # Senior IT
    ({"role": "user", "department": "IT", "yearsOfService": 1}, False),      # Junior IT
    ({"role": "user", "department": "sales", "yearsOfService": 5}, False),   # Non-IT
]

for user_data, expected in test_scenarios:
    result = evaluate(policy, {"user": user_data})
    assert result == expected  # → Results match expected access levels
```

**💡 Takeaway: Same input = same output, always. Perfect for caching and predictable behavior.**

## Detailed Use Case Analysis

### ✅ Perfect Use Cases

**Policy and Rules Engines**
```python
from cel import evaluate

# Business pricing with multiple factors
pricing_rule = "base_price * (1 + tax_rate) * (premium_customer ? 0.9 : 1.0)"
result = evaluate(pricing_rule, {
    "base_price": 100.0, "tax_rate": 0.08, "premium_customer": True
})
# → 97.2 (premium customer gets 10% discount)
assert result == 97.2  # Testing for illustration - not required in your code

# Multi-tier access control
access_policy = "user.role == 'admin' || (resource.owner == user.id && action in ['read', 'update']) || (resource.public && action == 'read')"
result = evaluate(access_policy, {
    "user": {"role": "admin", "id": "user1"},
    "resource": {"owner": "user2", "public": False},
    "action": "delete"
})
# → True (admin role grants access to any action)
assert result == True  # Testing for illustration - not required in your code
```

→ [**Complete Implementation Guide**](../how-to-guides/access-control-policies.md)

**Configuration Validation**
```python
from cel import evaluate

# Business rule validation table
validation_rules = {
    "Valid port range": "config.database.port > 0 && config.database.port < 65536",
    "Cache TTL minimum": "config.cache.ttl >= 60",
    "SSL in production": "config.features.ssl_enabled || config.environment == 'development'"
}

config = {
    "config": {
        "database": {"port": 5432}, "cache": {"ttl": 300},
        "features": {"ssl_enabled": True}, "environment": "production"
    }
}

# Validate all rules
for description, rule in validation_rules.items():
    result = evaluate(rule, config)
    assert result == True, f"Failed: {description}"
```

**Data Filtering and Transformation**
```python
from cel import evaluate

# Dynamic API filters
filters = {
    "Active engineering/product": ("user.active && user.department in ['engineering', 'product']", {"user": {"active": True, "department": "engineering"}}, True),    # → True (active eng user)
    "Performance scoring": ("base_score * effort_multiplier + bonus_points", {"base_score": 80, "effort_multiplier": 1.2, "bonus_points": 10}, 106.0)  # → 106.0 (calculated score)
}

for name, (expr, ctx, expected) in filters.items():
    result = evaluate(expr, ctx)
    assert result == expected  # → Results match expected filter outcomes
```

→ [**Complete Data Transformation Guide**](../how-to-guides/business-logic-data-transformation.md)

### ❌ When NOT to Use CEL

**Complex Business Logic**

CEL can't handle multi-step workflows with branching logic:

```
// This type of logic needs traditional programming:
if amount > 10000:
    route_to_executive_approval()
    send_email_to_cfo()
    log_high_value_request()
else if department == "finance":
    route_to_finance_approval()
    check_budget_constraints()
else:
    auto_approve()
    update_metrics()
```

Use Python for complex workflows:
```python
def complex_approval_workflow(request):
    if request.amount > 10000:
        return "executive_approval"  # Multiple steps happen here
    elif request.department == "finance":
        return "finance_approval"   # Different approval path
    else:
        return "auto_approve"       # Simple approval

# Test the function
class MockRequest:
    def __init__(self, amount, department):
        self.amount = amount
        self.department = department

result = complex_approval_workflow(MockRequest(15000, "engineering"))
# → "executive_approval" (high-value request)
assert result == "executive_approval"

result = complex_approval_workflow(MockRequest(5000, "finance"))
# → "finance_approval" (department-specific routing)
assert result == "finance_approval"

result = complex_approval_workflow(MockRequest(1000, "marketing"))
# → "auto_approve" (standard approval)
assert result == "auto_approve"
```

**I/O Operations**

CEL can't perform external operations:

```
// This type of logic needs I/O capabilities:
send_email(user.email, "Welcome!")
post_to_slack(user.slack_id, "New user joined")
log_to_database(user.id, "registration")
```

Use Python for I/O operations:
```python
def send_notification(user, message):
    # email_service.send(user.email, message)
    # slack_service.post(user.slack_id, message)
    return f"Sent '{message}' to {user['email']} and {user['slack_id']}"

# Test the function
user = {"email": "test@example.com", "slack_id": "@test"}
result = send_notification(user, "Hello!")
# → "Sent 'Hello!' to test@example.com and @test" (notification sent)
assert "Sent 'Hello!' to test@example.com and @test" == result
```

**Stateful Operations**

CEL can't remember state between evaluations:

```
// This type of logic needs persistent state:
if user_request_count < max_requests:
    increment_request_count(user_id)
    return allow_request()
else:
    return deny_request()
```

Use Python for stateful operations:
```python
class RateLimiter:
    def __init__(self):
        self.requests = {}  # Persistent state
    
    def is_allowed(self, user_id, max_requests=100):
        # Track request counts over time
        current_count = self.requests.get(user_id, 0)
        if current_count < max_requests:
            self.requests[user_id] = current_count + 1
            return True
        return False

# Test the class
rate_limiter = RateLimiter()
assert rate_limiter.is_allowed("user1", max_requests=2) == True   # → True (first request)
assert rate_limiter.is_allowed("user1", max_requests=2) == True   # → True (second request)
assert rate_limiter.is_allowed("user1", max_requests=2) == False  # → False (limit exceeded)
```

## Core Principles for Effective CEL

### 1. Design for Humans

CEL expressions should be readable by non-programmers. Business users should be able to understand and potentially modify them.

```python
from cel import evaluate

# ✅ GOOD: Clear and readable
clear_rule = "order.total > 100 && customer.loyalty_tier == 'gold'"
result = evaluate(clear_rule, {"order": {"total": 150}, "customer": {"loyalty_tier": "gold"}})
assert result == True  # → True (gold customer with large order)

# ❌ BAD: Too cryptic - avoid this style  
cryptic_rule = "o.t > 1e2 && c.lt == 'g'"
result = evaluate(cryptic_rule, {"o": {"t": 150}, "c": {"lt": "g"}})
assert result == True  # → True (works but unreadable)
```

**Visual Comparison:**

| **❌ Cryptic (Don't Do This)** | **✅ Human-Readable (Do This)** |
|--------------------------------|----------------------------------|
| `o.t > 1e2 && c.lt == 'g'` | `order.total > 100 && customer.loyalty_tier == 'gold'` |
| `u.r in ['a','m'] && p.c < 5` | `user.role in ['admin','manager'] && project.complexity < 5` |
| `d.ts > now() - 86400` | `document.timestamp > now() - duration('24h')` |

**Why readable names matter:**
- Business users can review and suggest changes
- Debugging is faster when expressions are self-documenting  
- Code reviews focus on logic, not deciphering abbreviations

**💡 Takeaway: Use readable identifiers so policies are self-documenting.**

### 2. Keep Context Simple

Provide clean, well-structured data to your expressions.

```python
from cel import evaluate

# ✅ Clean, structured context
context = {
    "user": {"id": "user123", "role": "admin", "permissions": ["read", "write", "delete"]},
    "resource": {"type": "document", "owner": "user123", "public": False},
    "action": "delete"
}

policy = "user.role == 'admin' || (resource.owner == user.id && 'delete' in user.permissions)"
result = evaluate(policy, context)
assert result == True
```

**💡 Takeaway: Structure context data clearly — it's the foundation of readable expressions.**

→ [**Variable Structuring Patterns**](your-first-integration.md#context-management)

### 3. Test Your Expressions

CEL expressions are code - treat them as such with proper testing.

```python
from cel import evaluate

# Compact test scenarios
test_cases = [
    ("Admin access", "user.role == 'admin'", {"user": {"role": "admin"}, "resource": {"type": "document"}, "action": "delete"}, True),    # → True (admin access)
    ("Owner access", "resource.owner == user.id", {"user": {"id": "user123", "role": "user"}, "resource": {"owner": "user123"}, "action": "read"}, True),    # → True (owner access)
    ("Denied access", "resource.owner == user.id", {"user": {"id": "user456", "role": "user"}, "resource": {"owner": "user123"}, "action": "read"}, False),   # → False (denied access)
]

for name, policy, context, expected in test_cases:
    result = evaluate(policy, context)
    assert result == expected  # → Results match expected access decisions
```

**💡 Takeaway: Test edge cases and failure scenarios — expressions fail silently.**

### 4. Use Type-Safe Patterns

Always check for field existence when dealing with optional data.

```python
from cel import evaluate

# ✅ Safe patterns with has() checks
safety_examples = [
    ("Complete profile", 'has(user.profile) && user.profile.verified', {"user": {"profile": {"verified": True}}}, True),    # → True (profile exists and verified)
    ("Missing profile", 'has(user.profile) && user.profile.verified', {"user": {}}, False),    # → False (no profile, safe fallback)
    ("Fallback value", 'has(user.display_name) ? user.display_name : user.email', {"user": {"email": "test@example.com"}}, "test@example.com"),    # → "test@example.com" (fallback to email)
]

for name, expr, context, expected in safety_examples:
    result = evaluate(expr, context)
    assert result == expected  # → Results show safe handling of optional fields
```

**💡 Takeaway: Always use `has()` for optional fields — prevent runtime errors.**

### 5. Document Your Context Schema

Make it clear what data your expressions expect.

```python
from cel import evaluate

# Expected context schema:
# {
#     "user": {"id": str, "role": str ("admin" | "user" | "guest"), "department": str, "verified": bool},
#     "resource": {"type": str, "owner": str, "public": bool},
#     "action": str ("read" | "write" | "delete")
# }

access_policy = "user.role == 'admin' || (resource.public && action == 'read') || (resource.owner == user.id && action in ['read', 'write'])"

# Schema-compliant test
test_context = {
    "user": {"id": "user1", "role": "user", "department": "engineering", "verified": True},
    "resource": {"type": "document", "owner": "user1", "public": False},
    "action": "read"
}

result = evaluate(access_policy, test_context)
assert result == True  # → True (owner access granted)
```

**💡 Takeaway: Document expected data shapes — context structure is API contract.**

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