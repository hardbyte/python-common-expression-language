# CEL Cookbook

Welcome to the CEL Cookbook! This is your one-stop reference for solving common problems with the Common Expression Language. Each recipe provides practical, tested solutions you can adapt for your specific use case.

## 🎯 Quick Problem Solver

**Looking for something specific?** Jump directly to the solution:

| **I want to...** | **Recipe** | **Difficulty** |
|------------------|------------|----------------|
| Build secure access control rules | [Access Control Policies](#access-control) | ⭐⭐ |
| Transform and validate data | [Business Logic & Data Transformation](#data-transformation) | ⭐⭐ |
| Create dynamic database filters | [Dynamic Query Filters](#query-filters) | ⭐⭐⭐ |
| Handle errors gracefully | [Error Handling](#error-handling) | ⭐⭐ |
| Use the CLI effectively | [CLI Usage Recipes](#cli-recipes) | ⭐ |
| Follow production best practices | [Production Patterns](#production-patterns) | ⭐⭐⭐ |

---

## 🛡️ Access Control {#access-control}

**Perfect for:** IAM systems, API gateways, resource protection

Build robust access control policies that are easy to understand and maintain.

### What You'll Learn
- Role-based access control (RBAC) patterns
- Attribute-based access control (ABAC) implementations  
- Time-based access restrictions
- Multi-tenant authorization
- Audit logging for access decisions

### Key Recipes

**Role-based access:**
```python
from cel import evaluate

expression = 'user.role in ["admin", "editor"] && resource.type == "document"'
context = {
    "user": {"role": "editor", "id": "user123"}, 
    "resource": {"type": "document", "owner": "user456"}
}

result = evaluate(expression, context)
print(result)  # → True
```

**Time-sensitive access:**
```python
# Check permissions with time-based access
expression = '"read" in user.permissions && user.active'
context = {
    "user": {"permissions": ["read", "write"], "active": True}
}

result = evaluate(expression, context)
print(result)  # → True (user has read permission and is active)
```

> ⚠️ **Security Note**: Always validate user inputs and sanitize context data. Never trust user-provided expressions without proper validation.

**→ [Full Access Control Guide](how-to-guides/access-control-policies.md) | [API Reference](reference/python-api.md)**

---

## 🔄 Business Logic & Data Transformation {#data-transformation}

**Perfect for:** Data pipelines, validation rules, configuration management

Transform and validate data with declarative expressions that business users can understand.

### What You'll Learn
- Input validation and sanitization
- Data transformation patterns
- Business rule implementation
- Configuration validation
- Complex conditional logic

### Key Recipes

**User data transformation:**
```python
from cel import evaluate

# Transform user data into a structured format
expression = '''{
  "name": user.first_name + " " + user.last_name,
  "can_vote": user.age >= 18,
  "tier": user.spend > 1000 ? "gold" : "silver"
}'''

context = {
    "user": {
        "first_name": "Alice", 
        "last_name": "Johnson",
        "age": 25,
        "spend": 1500
    }
}

result = evaluate(expression, context)
print(result)  # → {'name': 'Alice Johnson', 'can_vote': True, 'tier': 'gold'}
```

**Email validation:**
```python
expression = 'email.matches(r"^[^@]+@[^@]+\\.[^@]+$") && size(email) <= 254'
context = {"email": "user@company.com"}

result = evaluate(expression, context)
print(result)  # → True
```

**→ [Full Data Transformation Guide](how-to-guides/business-logic-data-transformation.md) | [API Reference](reference/python-api.md)**

---

## 🔍 Dynamic Query Filters {#query-filters}

**Perfect for:** Search APIs, database queries, reporting systems

Build flexible, secure query filters that adapt to user input while preventing injection attacks.

### What You'll Learn
- Safe query construction patterns
- User-driven filtering interfaces
- Search query builders
- SQL/NoSQL integration patterns
- Performance optimization techniques

### Key Recipes

**Multi-field search:**
```python
from cel import evaluate

# Search across multiple fields safely
expression = '(name.contains(query) || description.contains(query)) && status == "active"'
context = {
    "name": "Python CEL Library",
    "description": "Fast expression evaluation",
    "status": "active",
    "query": "Python"
}

result = evaluate(expression, context)
print(result)  # → True (matches name field)
```

**Date range filtering:**
```python
expression = 'created_at >= start_date && created_at <= end_date'
context = {
    "created_at": "2024-06-15T10:00:00Z",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z"
}

result = evaluate(expression, context)
print(result)  # → True (within date range)
```

> ⚠️ **Security Warning**: Never directly concatenate untrusted strings into SQL queries. Always use safe parameterization. CEL expressions should validate data, not construct raw SQL.

**→ [Full Query Filters Guide](how-to-guides/dynamic-query-filters.md) | [API Reference](reference/python-api.md)**

---

## ⚠️ Error Handling {#error-handling}

**Perfect for:** Production systems, user-facing applications, API development

Handle edge cases gracefully and provide meaningful error messages to users.

### What You'll Learn
- Defensive expression patterns
- Null safety techniques
- Context validation strategies
- Error recovery patterns
- User-friendly error messages

### Key Recipes

**Safe property access:**
```python
from cel import evaluate

# Safely check nested properties
expression = 'has(user.profile) && user.profile.verified'

# Test with complete data
context = {"user": {"profile": {"verified": True}}}
result = evaluate(expression, context)
print(result)  # → True

# Test with missing profile (won't error)
context = {"user": {"email": "test@example.com"}}
result = evaluate(expression, context)
print(result)  # → False (safe fallback)
```

**Null coalescing patterns:**
```python
expression = 'has(user.display_name) ? user.display_name : user.email'
context = {
    "user": {
        "email": "alice@company.com"
        # display_name is missing
    }
}

result = evaluate(expression, context)
print(result)  # → "alice@company.com" (fallback to email)
```

> ⚠️ **Security Note**: Always validate context structure before evaluation. Use `has()` checks for optional fields to prevent runtime errors.

**→ [Full Error Handling Guide](how-to-guides/error-handling.md) | [API Reference](reference/python-api.md)**

---

## 🖥️ CLI Usage Recipes {#cli-recipes}

**Perfect for:** DevOps workflows, testing, automation scripts

Master the command-line interface for debugging, testing, and automation.

### What You'll Learn
- Interactive REPL usage
- Batch processing patterns
- Integration with shell scripts
- Testing and debugging workflows
- CI/CD pipeline integration

### Key Recipes

**Quick expression testing:**
```bash
# Simple expressions
cel '1 + 2 * 3'
# → 7

cel '"Hello " + "World"'
# → "Hello World"

# With context
cel 'user.age >= 21' --context '{"user": {"age": 25}}'
# → True
```

**Interactive debugging:**
```bash
# Start REPL for exploration
cel --interactive
# CEL> user.role == "admin"
# CEL> has(user.permissions)
# CEL> exit
```

**Pipeline integration:**
```bash
echo '{"user": "admin"}' | cel 'user == "admin"'
# → True
```

**→ [Full CLI Guide](how-to-guides/cli-recipes.md) | [CLI Reference](reference/cli-reference.md)**

---

## 🚀 Production Patterns {#production-patterns}

**Perfect for:** Enterprise systems, high-scale applications, production deployments

Learn battle-tested patterns for building robust, secure, and performant CEL applications.

### What You'll Learn
- Security best practices
- Performance optimization
- Monitoring and observability
- Testing strategies
- Deployment patterns

### Key Patterns

**Context validation pattern:**
```python
from cel import evaluate

def safe_evaluate(expression, context):
    # Validate context structure before evaluation
    if not isinstance(context, dict):
        raise ValueError("Context must be a dictionary")
    
    # Simple validation before evaluation
    if "user" not in context:
        return False
    return evaluate(expression, context)

# Example usage
result = safe_evaluate('user.role == "admin"', {"user": {"role": "admin"}})
print(result)  # → True
```

**Expression caching pattern:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_evaluation(expression, context_tuple):
    # Cache results for identical expression + context combinations
    # Convert tuple back to dict for evaluation
    context = dict(context_tuple)
    return evaluate(expression, context)

# Usage with hashable context
context = {"user_role": "admin", "resource_type": "document"}
result = get_cached_evaluation('user_role == "admin"', tuple(context.items()))
print(result)  # → True (cached on subsequent calls)
```

> ⚠️ **Security Best Practices**: 
> - Always validate context data structure
> - Use `has()` checks for optional fields
> - Never trust user-provided expressions without sandboxing
> - Monitor expression performance for DoS protection

**→ [Full Production Guide](how-to-guides/production-patterns-best-practices.md) | [API Reference](reference/python-api.md)**

---

## 🎓 Learning Path

**New to CEL?** Follow this recommended learning path:

1. **Start Here**: [Quick Start Guide](getting-started/quick-start.md) - Get up and running in 5 minutes
2. **Learn Fundamentals**: [CEL Language Basics](tutorials/cel-language-basics.md) - Master the syntax
3. **Practice**: [CLI Recipes](#cli-recipes) - Get comfortable with the tools
4. **Build**: [Business Logic](#data-transformation) - Implement your first real use case
5. **Secure**: [Error Handling](#error-handling) - Make it production-ready
6. **Scale**: [Production Patterns](#production-patterns) - Deploy with confidence

## 💡 Can't Find What You're Looking For?

- **Browse all tutorials**: [Learning CEL section](tutorials/thinking-in-cel.md)
- **Check the API**: [Python API Reference](reference/python-api.md)  
- **File an issue**: [GitHub Issues](https://github.com/hardbyte/python-common-expression-language/issues)
- **Join discussions**: [GitHub Discussions](https://github.com/hardbyte/python-common-expression-language/discussions)

---

**💡 Pro Tip**: Each guide includes copy-paste ready examples, real-world use cases, and links to related patterns. The examples are all tested and guaranteed to work with the current version.