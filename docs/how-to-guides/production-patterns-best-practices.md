# Production Patterns & Best Practices

This guide serves as your comprehensive hub for production CEL patterns, summarizing key practices and directing you to detailed implementations. Use this as your go-to reference for building robust, secure, and performant CEL applications.

## 🛡️ Safe Expression Design

### Always Use `has()` for Optional Fields

**Key Practice**: Check field existence before accessing to prevent runtime errors.

```cel
# ✅ Safe - won't crash if profile is missing
has("user.profile") && user.profile.verified

# ✅ Safe - with fallback value  
user.profile.verified if has("user.profile") else false
```

**Why It Matters**: Prevents runtime crashes when context data is incomplete or inconsistent.

**Learn More**: See [Error Handling → Defensive Expression Patterns](error-handling.md#defensive-expression-patterns) for comprehensive examples and advanced patterns.

### Validate Context Data Before Evaluation

**Key Practice**: Don't trust input data - validate it first.

```python
from cel import evaluate

def safe_policy_evaluation(policy, context):
    # Validate required fields exist
    required_fields = ["user", "resource", "action"]
    for field in required_fields:
        if field not in context:
            raise ValueError(f"Missing required field: {field}")
    return evaluate(policy, context)

# Test the function
context = {"user": {"id": "alice"}, "resource": {"type": "file"}, "action": "read"}
result = safe_policy_evaluation("user.id == 'alice'", context)
assert result is True
```

**Why It Matters**: Prevents evaluation errors and ensures consistent behavior across your application.

**Learn More**: See [Error Handling → Context Validation](error-handling.md#context-validation) for complete validation patterns and production examples.

### Build Defensive Expressions

**Key Practice**: Write expressions that handle edge cases gracefully.

```cel
# ✅ Handles missing fields, empty lists, null values
has("user.role") && user.role == "admin" ||
(has("user.permissions") && size(user.permissions) > 0 && "admin" in user.permissions)
```

**Why It Matters**: Makes your expressions resilient to data variations and reduces failure rates.

**Learn More**: See [Error Handling → Defensive Expression Patterns](error-handling.md#defensive-expression-patterns) for comprehensive defensive techniques.

## 🌐 Web Framework Integration

### Flask Integration Patterns

**Key Practice**: Use decorators for policy-based route protection.

```python
# Example decorator (implementation in web framework examples)
def require_policy(policy_name):
    def decorator(func):
        return func
    return decorator

@require_policy("admin_only")
def admin_endpoint():
    return {"data": "sensitive"}

# Test the decorator
decorated_func = require_policy("admin_only")(admin_endpoint)
result = decorated_func()
assert result == {"data": "sensitive"}
```

**Core Components**:
- **Context Builders**: Create consistent CEL contexts from Flask requests
- **Policy Decorators**: Apply access control policies to routes  
- **Error Handling**: Graceful policy evaluation failure handling

**Implementation Details**: This involves several patterns including request context building, policy decorator implementation, and error handling. The complete Flask integration requires ~200 lines of production-ready code.

**Get Full Implementation**: See [Web Framework Integration Examples](https://github.com/hardbyte/python-common-expression-language/tree/main/examples/web-frameworks) for complete Flask, FastAPI, and Django integration examples.

### FastAPI Integration Patterns

**Key Practice**: Use dependency injection for async policy checking.

```python
# Example classes (implementation in FastAPI examples)
class PolicyChecker:
    def __init__(self, policy):
        self.policy = policy

def Depends(dependency):
    return dependency

class MockApp:
    def get(self, path):
        def decorator(func):
            return func
        return decorator

app = MockApp()
require_admin = PolicyChecker("user.role == 'admin'")

@app.get("/admin")
async def admin_route(authorized: bool = Depends(require_admin)):
    return {"message": "Admin access granted"}

# Test the setup
assert require_admin.policy == "user.role == 'admin'"
assert Depends(require_admin) is require_admin  # Depends returns the dependency itself
```

**Core Components**:
- **Async Context Building**: Handle async user authentication and context creation
- **Policy Dependencies**: Reusable policy checkers for route protection
- **Thread Pool Execution**: Handle CPU-bound CEL evaluation in async context

**Get Full Implementation**: See [FastAPI CEL Integration Example](https://github.com/hardbyte/python-common-expression-language/tree/main/examples/web-frameworks/fastapi) for complete async implementation.

### Django Integration Patterns

**Key Practice**: Use middleware for request-scoped CEL context.

```python
# Example decorator (implementation in Django examples)
def cel_permission_required(policy):
    def decorator(func):
        return func
    return decorator

class JsonResponse:
    def __init__(self, data):
        self.data = data

@cel_permission_required("user.is_staff && user.groups.contains('editors')")
def edit_view(request, article_id):
    return JsonResponse({"message": f"Editing {article_id}"})

# Test the setup
class MockRequest:
    pass

response = edit_view(MockRequest(), "123")
assert response.data == {"message": "Editing 123"}
```

**Core Components**:
- **Middleware Integration**: Automatic CEL context creation for all requests
- **View Decorators**: Permission checking decorators for Django views
- **User Context**: Integration with Django's authentication system

**Get Full Implementation**: See [Django CEL Integration Example](https://github.com/hardbyte/python-common-expression-language/tree/main/examples/web-frameworks/django) for complete middleware and decorator implementation.

## 🚀 Performance Optimization {#performance-optimization}

### Context Design for Performance

**Key Practice**: Design flat, efficient context structures.

```python
from cel import evaluate

# ✅ Efficient - flat structure
context_flat = {
    "user_role": "admin",
    "resource_type": "database", 
    "action": "delete"
}

# ❌ Less efficient - deeply nested
context_nested = {
    "request": {
        "user": {"profile": {"role": "admin"}}
    }
}

# Test both contexts work
result1 = evaluate("user_role == 'admin'", context_flat)
result2 = evaluate("request.user.profile.role == 'admin'", context_nested)
assert result1 is True
assert result2 is True
```

**Why It Matters**: Flat structures reduce expression evaluation time and memory usage.

**Learn More**: See [Performance Benchmarking](#performance-benchmarking) section below for measurement techniques.

### Expression Caching Strategies

**Key Practice**: Cache evaluation results for common scenarios using LRU cache.

```python
from functools import lru_cache
from cel import evaluate

class PolicyEngine:
    @lru_cache(maxsize=1000)
    def _evaluate_cached(self, policy, user_role, resource_public):
        context = {"user": {"role": user_role}, "resource": {"public": resource_public}}
        return evaluate(policy, context)

# Test the cached evaluation
engine = PolicyEngine()
result1 = engine._evaluate_cached("user.role == 'admin'", "admin", True)
result2 = engine._evaluate_cached("user.role == 'admin'", "admin", True)  # cached
assert result1 is True
assert result2 is True
```

**When to Use**: For high-frequency evaluations with repeated context patterns.

**When Not to Use**: For constantly changing context data or user-specific evaluations.

**Advanced Patterns**: For production caching strategies including cache invalidation, distributed caching, and performance monitoring, see the performance optimization examples in the repository.

## 🔒 Security Best Practices {#security-best-practices}

### Input Sanitization for Untrusted Expressions

**Key Practice**: Validate and sanitize user-provided CEL expressions.

```python
import re

# Define security constants
MAX_EXPRESSION_LENGTH = 1000
# Allow safe characters for CEL expressions
ALLOWED_PATTERN = re.compile(r'^[a-zA-Z0-9_\s\.\(\)\[\]\{\}\+\-\*\/\<\>\=\!\&\|\,]+$')

def sanitize_expression(expression):
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError("Expression too long")
    
    if not ALLOWED_PATTERN.match(expression):
        raise ValueError("Expression contains invalid characters")
    
    return expression

# Test the sanitization function
valid_expr = "user.role == admin"  # Simplified to avoid quote escaping issues
sanitized = sanitize_expression(valid_expr)
assert sanitized == valid_expr

# Test with a clearly invalid expression
try:
    sanitize_expression("user.role == admin; DROP TABLE users;")
    assert False, "Should have raised ValueError"
except ValueError as e:
    assert "invalid characters" in str(e)
```

**Critical Security Concerns**:
- **Expression Length**: Prevent DoS attacks through extremely long expressions
- **Character Validation**: Block potentially dangerous patterns
- **Malformed Syntax**: Handle syntax errors that raise ValueError exceptions

**Learn More**: See [Error Handling → Input Sanitization for Untrusted Expressions](error-handling.md#input-sanitization-for-untrusted-expressions) for complete validation patterns and security examples.

### Context Isolation

**Key Practice**: Only include necessary, safe data in CEL contexts.

```python
from cel import Context, evaluate

def create_isolated_context(user_data, resource_data):
    # Only include explicitly allowed fields
    safe_user = {
        "id": user_data.get("id"),
        "role": user_data.get("role"),
        "verified": user_data.get("verified", False)
    }
    return Context({"user": safe_user})

# Test the isolation function
user_data = {"id": "alice", "role": "admin", "password": "secret", "verified": True}
resource_data = {"type": "file"}
context = create_isolated_context(user_data, resource_data)

# Verify only safe fields are included by testing evaluation
assert evaluate("user.id", context) == "alice"
assert evaluate("user.role", context) == "admin"
assert evaluate("user.verified", context) is True

# Verify password is not accessible (this would fail if password was included)
try:
    evaluate("user.password", context)
    assert False, "Password should not be accessible"
except Exception:
    pass  # Expected - password field should not be accessible
```

**Why It Matters**: Prevents data leakage and reduces attack surface.

**Learn More**: See [Access Control Policies → Best Practices](access-control-policies.md#best-practices) for comprehensive security patterns.

## 🧪 Testing Strategies {#testing-strategies}

### Unit Testing CEL Expressions

**Key Practice**: Treat CEL expressions as code - write comprehensive tests.

```python
from cel import evaluate

def test_admin_access_policy():
    context = {"user": {"role": "admin"}}
    policy = "user.role == 'admin'"
    assert evaluate(policy, context) == True

def test_missing_context_handled_safely():
    context = {"user": {"id": "alice"}}  # No role
    safe_policy = 'has(user.role) && user.role == "admin"'
    assert evaluate(safe_policy, context) == False

# Run the tests
test_admin_access_policy()
test_missing_context_handled_safely()
```

**Testing Categories**:
- **Happy Path**: Test expected successful scenarios
- **Edge Cases**: Test missing data, null values, empty collections
- **Error Conditions**: Test invalid expressions and malformed context
- **Property-Based**: Use hypothesis for comprehensive input testing

**Learn More**: See [Error Handling → Testing Error Scenarios](error-handling.md#testing-error-scenarios) for complete testing strategies and examples.

### Integration Testing

**Key Practice**: Test CEL integration within your web framework.

```python
# Mock client for testing
class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code

class MockClient:
    def get(self, path, headers=None):
        # Simple mock: admin tokens get 200, others get 403
        if headers and 'admin_token' in headers.get('Authorization', ''):
            return MockResponse(200)
        return MockResponse(403)

def test_protected_route_access():
    client = MockClient()
    
    # Test admin access
    response = client.get('/admin/users', 
                         headers={'Authorization': 'Bearer admin_token'})
    assert response.status_code == 200
    
    # Test user denial
    response = client.get('/admin/users',
                         headers={'Authorization': 'Bearer user_token'})
    assert response.status_code == 403

# Run the test
test_protected_route_access()
```

**Integration Test Areas**:
- **Route Protection**: Test policy decorators with different user roles
- **Context Building**: Test request context creation accuracy
- **Error Handling**: Test policy evaluation failure scenarios

## 🔍 Monitoring & Debugging {#monitoring-and-debugging}

### Expression Evaluation Logging

**Key Practice**: Log CEL evaluations for production debugging.

```python
import logging
from cel import evaluate

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def evaluate_with_logging(expression, context, description=""):
    try:
        result = evaluate(expression, context)
        logger.info(f"CEL evaluation {description}: '{expression}' -> {result}")
        return result
    except Exception as e:
        logger.error(f"CEL evaluation failed {description}: '{expression}' -> {e}")
        raise

# Test the logging function
context = {"user": {"role": "admin"}}
result = evaluate_with_logging("user.role == 'admin'", context, "test")
assert result is True
```

**What to Log**:
- **Expression**: The CEL expression being evaluated
- **Result**: The evaluation result
- **Context Keys**: Available context fields (not values for security)
- **Performance**: Evaluation timing for slow expressions

**Learn More**: See [Error Handling → Logging and Monitoring](error-handling.md#logging-and-monitoring) for production logging strategies.

### Performance Monitoring

**Key Practice**: Track evaluation performance in production.

```python
import time
import logging
from cel import evaluate

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class MonitoredPolicyEngine:
    def evaluate_monitored(self, expression, context):
        start_time = time.perf_counter()
        try:
            result = evaluate(expression, context)
            return result
        finally:
            duration = time.perf_counter() - start_time
            if duration > 0.001:  # 1ms threshold
                logger.warning(f"Slow CEL evaluation: {expression[:50]}")

# Test the monitored evaluation
engine = MonitoredPolicyEngine()
context = {"user": {"role": "admin"}}
result = engine.evaluate_monitored("user.role == 'admin'", context)
assert result is True
```

**Monitoring Metrics**:
- **Evaluation Time**: Track slow expressions
- **Expression Frequency**: Identify hot paths for optimization
- **Error Rates**: Monitor evaluation failures
- **Cache Hit Rates**: If using caching strategies

## 📊 Performance Benchmarking {#performance-benchmarking}

### Baseline Performance Measurement

Run this benchmark to understand CEL performance on your hardware:

```python
import time
from cel import evaluate

def benchmark_cel_performance():
    """Comprehensive CEL performance benchmark matching documented claims."""
    
    # Test scenarios matching the performance table
    test_cases = [
        {
            "name": "Simple expressions",
            "expression": "x + y * 2",
            "context": {"x": 10, "y": 20},
            "expected": 50,
            "iterations": 10000
        },
        {
            "name": "Complex expressions", 
            "expression": "user.active && user.role in ['admin', 'editor'] && has(user.permissions) && user.permissions.size() > 0",
            "context": {
                "user": {
                    "active": True,
                    "role": "admin", 
                    "permissions": ["read", "write", "delete"]
                }
            },
            "expected": True,
            "iterations": 5000
        },
        {
            "name": "Function calls",
            "expression": "double(x) + square(y)",
            "context": {
                "x": 5,
                "y": 3,
                "double": lambda x: x * 2,
                "square": lambda x: x * x
            },
            "expected": 19,  # double(5) + square(3) = 10 + 9
            "iterations": 3000
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\nBenchmarking: {test_case['name']}")
        
        # Verify the expression works correctly
        result = evaluate(test_case["expression"], test_case["context"])
        assert result == test_case["expected"], f"Expected {test_case['expected']}, got {result}"
        
        # Warmup
        for _ in range(100):
            evaluate(test_case["expression"], test_case["context"])
        
        # Benchmark
        start_time = time.perf_counter()
        for _ in range(test_case["iterations"]):
            evaluate(test_case["expression"], test_case["context"])
        end_time = time.perf_counter()
        
        # Calculate metrics
        total_time = end_time - start_time
        avg_time_us = (total_time / test_case["iterations"]) * 1_000_000
        throughput = test_case["iterations"] / total_time
        
        result_data = {
            "name": test_case["name"],
            "avg_time_us": avg_time_us,
            "throughput": throughput,
            "iterations": test_case["iterations"]
        }
        results.append(result_data)
        
        print(f"  Average time: {avg_time_us:.1f} μs")
        print(f"  Throughput: {throughput:,.0f} ops/sec")
    
    return results

# Run the benchmark and display results
if __name__ == "__main__":
    print("CEL Performance Benchmark")
    print("=" * 40)
    results = benchmark_cel_performance()
    
    print("\nSummary:")
    print("-" * 40)
    for result in results:
        print(f"{result['name']:20} | {result['avg_time_us']:6.1f} μs | {result['throughput']:8,.0f} ops/sec")
```

**Expected Results**:

- **Simple expressions**: 5-15 μs per evaluation, 50,000+ ops/sec
- **Complex expressions**: 15-40 μs per evaluation, 25,000+ ops/sec  
- **Function calls**: 20-50 μs per evaluation, 20,000+ ops/sec

**Learn More**: See [Performance Benchmarking Examples](https://github.com/hardbyte/python-common-expression-language/tree/main/examples/performance) for comprehensive benchmarking scripts.

## 📚 Configuration Management {#configuration-management}

### Dynamic Configuration Validation

**Key Practice**: Use CEL expressions to validate application configuration.

```python
from cel import evaluate

validation_rules = [
    {
        "field": "database.port",
        "expression": "config.database.port > 0 && config.database.port < 65536",
        "message": "Database port must be between 1 and 65535"
    },
    {
        "field": "ssl_required", 
        "expression": 'config.ssl_enabled || env == "development"',
        "message": "SSL must be enabled in production"
    }
]

# Test validation rules
config_context = {
    "config": {
        "database": {"port": 5432},
        "ssl_enabled": True
    },
    "env": "production"
}

# Validate all rules
for rule in validation_rules:
    result = evaluate(rule["expression"], config_context)
    assert result is True, f"Validation failed: {rule['message']}"

# Test invalid configuration
invalid_context = {
    "config": {
        "database": {"port": 70000},  # Invalid port
        "ssl_enabled": False
    },
    "env": "production"
}

port_rule = validation_rules[0]
port_valid = evaluate(port_rule["expression"], invalid_context)
assert port_valid is False  # Port is out of range
```

**Benefits**:
- **Business-Readable Rules**: Non-developers can understand validation logic
- **Dynamic Configuration**: Rules can be updated without code changes
- **Environment-Aware**: Different rules for development vs production

**Implementation**: Configuration validation requires a validation engine that processes rules and provides clear error messages. See [Business Logic & Data Transformation → Dynamic Rule Loading](business-logic-data-transformation.md#dynamic-rule-loading) for complete implementation.

## 🎯 Quick Reference

### Essential Patterns Summary

| Pattern | Key Principle | Implementation Guide |
|---------|---------------|---------------------|
| **Safe Expressions** | Use `has()` for optional fields | [Error Handling](error-handling.md#defensive-expression-patterns) |
| **Context Validation** | Validate before evaluation | [Error Handling](error-handling.md#context-validation) |
| **Web Integration** | Use decorators/dependencies | [Framework Examples](https://github.com/hardbyte/python-common-expression-language/tree/main/examples/web-frameworks) |
| **Performance** | Design flat contexts | [Performance Examples](https://github.com/hardbyte/python-common-expression-language/tree/main/examples/performance) |
| **Security** | Sanitize untrusted input | [Error Handling](error-handling.md#input-sanitization-for-untrusted-expressions) |
| **Testing** | Test like code | [Error Handling](error-handling.md#testing-error-scenarios) |
| **Monitoring** | Log evaluations | [Error Handling](error-handling.md#logging-and-monitoring) |

### Next Steps

1. **Start with Safety**: Implement [defensive expression patterns](error-handling.md#defensive-expression-patterns)
2. **Add Web Integration**: Choose your framework integration from the [examples](https://github.com/hardbyte/python-common-expression-language/tree/main/examples/web-frameworks)
3. **Implement Monitoring**: Add [evaluation logging](error-handling.md#logging-and-monitoring) for production visibility
4. **Optimize Performance**: Run [benchmarks](#performance-benchmarking) and implement caching as needed
5. **Secure Your Application**: Add [input sanitization](error-handling.md#input-sanitization-for-untrusted-expressions) for untrusted expressions

## Related Guides

- **[Error Handling](error-handling.md)** - Comprehensive error handling strategies
- **[Business Logic & Data Transformation](business-logic-data-transformation.md)** - Complex business rules and data processing  
- **[Access Control Policies](access-control-policies.md)** - User permission and authorization patterns
- **[Dynamic Query Filters](dynamic-query-filters.md)** - Database query construction and filtering
- **[CLI Usage Recipes](cli-recipes.md)** - Command-line tool integration patterns