# Access Control Policies

Define application authorization rules as CEL expressions instead of hard-coding `if`/`else` chains. The result is a tidy, auditable, side-effect-free policy that's easy to test and modify without redeploying.

## The shape of a policy

Pass the user, resource, and action into a context dict; encode the rules as one CEL expression.

```python
from cel import evaluate

policy = """
    user.role == "admin" ||
    (resource.owner == user.id && user.verified) ||
    (action == "read" && resource.public)
"""

def authorize(user, resource, action):
    return evaluate(policy, {
        "user": user,
        "resource": resource,
        "action": action,
    })

assert authorize(
    {"id": "alice", "role": "user", "verified": True},
    {"id": "doc1", "owner": "alice", "public": False},
    "write",
) is True

assert authorize(
    {"id": "bob", "role": "guest", "verified": False},
    {"id": "doc2", "owner": "alice", "public": True},
    "read",
) is True
```

## Role hierarchy

Translate role names to numeric levels in the context so the policy can compare them directly:

```python
from cel import evaluate

ROLE_LEVELS = {"guest": 0, "user": 1, "member": 2, "manager": 3, "admin": 4}

policy = """
    user.level >= 4 ||
    (action == "read" && resource.public) ||
    (action in ["read", "write"] && resource.owner == user.id) ||
    (action == "read" && user.id in resource.collaborators)
"""

def authorize(user, resource, action):
    enriched_user = {**user, "level": ROLE_LEVELS.get(user["role"], 0)}
    return evaluate(policy, {
        "user": enriched_user,
        "resource": resource,
        "action": action,
    })

assert authorize(
    {"id": "alice", "role": "manager"},
    {"id": "doc1", "owner": "bob", "public": False, "collaborators": ["alice"]},
    "read",
) is True
```

## Time-based access

Inject the current hour into the context and compare it in the expression. Keep the time computation in Python — it's not the policy's concern.

```python
from datetime import datetime
from cel import evaluate

policy = """
    user.role == "admin" ||
    (user.schedule == "always") ||
    (user.schedule == "business" && hour >= 9 && hour <= 17) ||
    (user.schedule == "extended" && hour >= 6 && hour <= 22)
"""

def authorize(user, *, now=None):
    now = now or datetime.now()
    return evaluate(policy, {"user": user, "hour": now.hour})

assert authorize({"role": "user", "schedule": "business"}, now=datetime(2026, 1, 1, 14)) is True
assert authorize({"role": "user", "schedule": "business"}, now=datetime(2026, 1, 1, 22)) is False
assert authorize({"role": "admin", "schedule": "business"}, now=datetime(2026, 1, 1, 3)) is True
```

## Per-resource policies

When different resource types need different rules, look up the policy by type:

```python
from cel import evaluate

POLICIES = {
    "document": """
        user.role == "admin" ||
        resource.owner == user.id ||
        (resource.public && action == "read") ||
        (user.id in resource.collaborators && action in ["read", "comment"])
    """,
    "database": """
        user.role == "admin" ||
        (user.role == "developer" && action in ["read", "write"]) ||
        (user.role == "analyst" && action == "read")
    """,
    "system": """
        user.role == "admin" ||
        (user.role == "operator" && action in ["read", "restart"]) ||
        (user.role == "monitor" && action == "read")
    """,
}

def authorize(user, resource, action):
    policy = POLICIES.get(resource.get("type"), POLICIES["document"])
    return evaluate(policy, {"user": user, "resource": resource, "action": action})

assert authorize(
    {"role": "developer", "id": "d1"},
    {"type": "database", "name": "prod"},
    "write",
) is True

assert authorize(
    {"role": "analyst", "id": "a1"},
    {"type": "database", "name": "prod"},
    "write",
) is False
```

## Pre-compile hot-path policies

If you evaluate the same policy many times per request, compile it once at startup:

```python
from cel import compile

policy = '''
    user.role == "admin" ||
    (resource.owner == user.id && user.verified) ||
    (action == "read" && resource.public)
'''
program = compile(policy)

# Then on each call:
allowed = program.execute({
    "user": {"id": "alice", "role": "user", "verified": True},
    "resource": {"id": "doc1", "owner": "alice", "public": False},
    "action": "write",
})
assert allowed is True
```

## Why CEL fits

- **Readable.** Non-engineer stakeholders can audit the rules.
- **Testable.** Each clause is a pure expression; test it the same way you'd test a function.
- **Safe.** No loops, no side effects, no `eval()`. The expression can't break out of the sandbox.
- **Versioned cleanly.** Policy text fits in a Git diff or a config row.

## Related topics

- [Business Logic & Data Transformation](business-logic-data-transformation.md) — broader rule-engine patterns.
- [Error Handling](error-handling.md) — exception types and safe-evaluation patterns.
