# CLI Usage Recipes

Practical examples and recipes for using the `cel` command-line tool in real-world scenarios, from simple evaluations to complex integrations.

## Basic Usage Patterns

### Simple Expressions

```bash
# Simple arithmetic
cel '1 + 2'                          # 3
cel '10 * 3.14'                      # 31.4

# String operations
cel '"Hello " + "World"'             # Hello World
cel '"test".size()'                  # 4

# Boolean logic
cel 'true && false'                  # false
cel '5 > 3'                         # true

# Collections
cel '[1, 2, 3]'                     # [1, 2, 3]
cel '[1, 2, 3].size()'              # 3
cel '{"name": "Alice", "age": 30}'   # {"name": "Alice", "age": 30}
```

### Working with Context

```bash
# Inline context
cel 'name + " is " + string(age)' --context '{"name": "Alice", "age": 30}'
# Output: Alice is 30

# Context from file
echo '{"user": {"name": "Bob", "role": "admin"}}' > user.json
cel 'user.name + " (" + user.role + ")"' --context-file user.json
# Output: Bob (admin)

# Complex context
cel 'user.role == "admin" && "write" in permissions' \
  --context '{"user": {"role": "admin"}, "permissions": ["read", "write"]}'
# Output: true
```

## Pipeline and Data Processing

### JSON Processing with jq and CEL

```bash
# Process JSON with jq and CEL
echo '{"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 17}]}' | \
  jq '.users[]' | \
  while read -r user; do
    cel 'user.age >= 18 ? user.name + " (adult)" : user.name + " (minor)"' \
      --context "{\"user\": $user}"
  done

# Filter and transform data
curl -s https://api.github.com/users/octocat | \
  cel 'login + " has " + string(public_repos) + " repos"' \
    --context-file /dev/stdin
```

### Batch Processing

```bash
# Process multiple files
for config in configs/*.json; do
  echo "Validating $config..."
  if cel 'has("database.host") && database.host != ""' --context-file "$config" --exit-status; then
    echo "✓ $config is valid"
  else
    echo "✗ $config is invalid"
  fi
done

# Transform data files
ls data/*.json | while read -r file; do
  cel 'user.name + "," + user.email + "," + string(user.age)' \
    --context-file "$file" >> users.csv
done
```

## Validation and Testing

### Configuration Validation

```bash
# Database configuration validation
cel 'has("database.host") && database.host != ""' --context-file config.json
cel 'database.port > 0 && database.port < 65536' --context-file config.json
cel 'database.ssl == true' --context-file config.json

# Application configuration validation
cel 'env in ["development", "staging", "production"]' --context-file app.json
cel 'has("api_key") && api_key.size() >= 32' --context-file secrets.json
```

### Policy Testing

```bash
# Access control policies
cel 'user.role == "admin" || (resource.public && action == "read")' \
  --context '{"user": {"role": "user"}, "resource": {"public": true}, "action": "read"}'

# Business rules testing
cel 'user.age >= 18 && user.verified && user.country in ["US", "CA", "UK"]' \
  --context-file user_profile.json

# Exit status for scripting
if cel 'user.verified && user.role in ["admin", "moderator"]' \
   --context-file user.json --exit-status; then
  echo "User has required permissions"
else
  echo "Access denied"
fi
```

## Interactive Development

### Interactive Session Workflow

```bash
# Start interactive mode
cel -i

# Example session:
CEL> context {"user": {"name": "Alice", "role": "admin", "verified": true}}
Context updated: user

CEL> user.name
Alice

CEL> user.role == "admin"
true

CEL> user.verified && user.role in ["admin", "moderator"]
true

CEL> load permissions.json
Loaded context from permissions.json

CEL> "write" in permissions
true

CEL> history
1: user.name
2: user.role == "admin"
3: user.verified && user.role in ["admin", "moderator"]
4: "write" in permissions

CEL> exit
```

### Rapid Prototyping

```bash
# Test expressions quickly:
cel -i
CEL> context {"data": {"users": [{"name": "Alice", "active": true}, {"name": "Bob", "active": false}]}}
Context updated: data

CEL> data.users.filter(u, u.active).map(u, u.name)
["Alice"]

CEL> data.users.exists(u, u.name == "Bob")
true

CEL> data.users.all(u, has(u.active))
true
```

## Integration Patterns

### Shell Functions

Add to your `.bashrc` or `.zshrc`:

```bash
# Quick CEL evaluation
function cq() {
  cel "$1" --context-file ~/.cel/default_context.json
}

# CEL with context from environment
function ce() {
  local ctx="{\"USER\": \"$USER\", \"HOME\": \"$HOME\", \"PWD\": \"$PWD\"}"
  cel "$1" --context "$ctx"
}

# Policy check
function policy_check() {
  cel "$1" --context-file ~/.cel/policy_context.json --exit-status
}

# Usage examples:
cq 'user.role == "admin"'
ce 'USER == "alice"'
policy_check 'action == "deploy" && user.role in ["admin", "deployer"]'
```

### Git Hooks

Use in git hooks for policy enforcement:

```bash
#!/bin/bash
# pre-commit hook

# Check if commit should be allowed
commit_msg=$(git log -1 --pretty=format:"%s")
author=$(git log -1 --pretty=format:"%an")

context="{\"commit\": {\"message\": \"$commit_msg\", \"author\": \"$author\"}}"

if ! cel 'commit.message.size() > 10 && !commit.message.contains("WIP")' \
     --context "$context" --exit-status; then
  echo "Commit message too short or contains WIP"
  exit 1
fi

# Check file patterns
changed_files=$(git diff --cached --name-only)
if echo "$changed_files" | grep -q "\.py$"; then
  if ! cel 'commit.message.contains("python") || commit.message.contains("py")' \
       --context "$context" --exit-status; then
    echo "Python files changed but commit message doesn't mention Python"
    exit 1
  fi
fi
```

### CI/CD Integration

```bash
# In GitHub Actions / CI pipelines
#!/bin/bash

# Environment validation
cel 'env.NODE_ENV in ["development", "staging", "production"]' \
  --context "{\"env\": {\"NODE_ENV\": \"$NODE_ENV\"}}" \
  --exit-status || exit 1

# Deployment conditions
cel 'branch == "main" && tests_passed && security_scan_passed' \
  --context "{
    \"branch\": \"$GITHUB_REF_NAME\",
    \"tests_passed\": $TESTS_PASSED,
    \"security_scan_passed\": $SECURITY_SCAN_PASSED
  }" \
  --exit-status || exit 1

# Feature flag evaluation
cel 'env == "production" && feature_flags.new_ui_enabled' \
  --context-file deployment_config.json \
  --exit-status && echo "::set-output name=deploy_new_ui::true"
```

### Docker Integration

```dockerfile
FROM python:3.11-slim

# Install CEL
RUN pip install common-expression-language

# Use in health checks
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD cel 'timestamp() - start_time < duration("5m")' \
      --context "{\"start_time\": \"$(cat /app/start_time)\"}" \
      --exit-status

# Use in entrypoint scripts
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
# entrypoint.sh
#!/bin/bash

# Configuration validation before startup
if ! cel 'has("database.url") && has("redis.url")' \
     --context-file /app/config.json --exit-status; then
  echo "Missing required configuration"
  exit 1
fi

# Environment-specific startup logic
if cel 'env == "development"' --context-file /app/config.json --exit-status; then
  echo "Starting in development mode..."
  python -m app --debug
else
  echo "Starting in production mode..."
  gunicorn app:app
fi
```

## Configuration Management

### Configuration Files

Create `~/.cel/config.json` for default settings:

```json
{
  "default_context_file": "~/.cel/default_context.json",
  "history_size": 1000,
  "interactive": {
    "syntax_highlighting": true,
    "auto_completion": true,
    "vi_mode": false
  },
  "output": {
    "format": "auto",
    "compact": false,
    "color": true
  }
}
```

### Context Files

Store frequently used context in JSON files:

```json
// ~/.cel/contexts/development.json
{
  "env": "development",
  "debug": true,
  "api_url": "http://localhost:8080",
  "user": {
    "role": "developer",
    "permissions": ["read", "write", "debug"]
  }
}
```

```json
// ~/.cel/contexts/production.json
{
  "env": "production",
  "debug": false,
  "api_url": "https://api.example.com",
  "user": {
    "role": "service",
    "permissions": ["read"]
  }
}
```

Usage:
```bash
cel 'env == "development" && debug' --context-file ~/.cel/contexts/development.json
cel 'api_url.startsWith("https")' --context-file ~/.cel/contexts/production.json
```

### Environment Variables

```bash
# Set up environment for CEL
export CEL_CONFIG_DIR="$HOME/.config/cel"
export CEL_HISTORY_FILE="$HOME/.cel_history"
export CEL_DEFAULT_CONTEXT="$HOME/.cel/default_context.json"
export CEL_DEBUG=1

# Use in scripts
cel 'expression'  # Will automatically load default context and run in debug mode
```

## Performance Optimization

### Optimization Tips

1. **Use context files** for complex context instead of inline JSON
2. **Cache compiled expressions** when evaluating repeatedly
3. **Minimize context size** by including only necessary data
4. **Use specific field access** instead of passing large objects

```bash
# Faster - focused context
cel 'user.role == "admin"' --context '{"user": {"role": "admin"}}'

# Slower - large context
cel 'user.role == "admin"' --context-file large_user_object.json
```

### Benchmarking

```bash
# Time expression evaluation
time cel 'complex.expression.here' --context-file large_context.json

# Measure multiple evaluations
echo "Testing expression performance..."
time for i in {1..100}; do
  cel 'user.role == "admin"' --context-file user.json >/dev/null
done

# Compare different approaches
echo "Method 1: Inline context"
time for i in {1..50}; do
  cel 'user.verified' --context '{"user": {"verified": true}}' >/dev/null
done

echo "Method 2: Context file"
time for i in {1..50}; do
  cel 'user.verified' --context-file small_context.json >/dev/null
done
```

## Error Handling and Debugging

### Common Error Scenarios

```bash
# Syntax errors
$ cel '1 + + 2'
Error: Syntax error at position 4: unexpected token '+'

$ cel 'invalid syntax here'
Error: Parse error: expected expression

# Runtime errors
$ cel '1 / 0'
Error: Division by zero

$ cel 'unknown_variable + 1' --context '{}'
Error: Variable 'unknown_variable' not found

# Type errors
$ cel '"hello" + 42'
Error: Type mismatch: cannot add string and int

$ cel 'user.name.invalid_method()' --context '{"user": {"name": "Alice"}}'
Error: No such method 'invalid_method' on type string

# File errors
$ cel 'expression' --context-file nonexistent.json
Error: Cannot read context file: nonexistent.json (No such file or directory)

$ cel 'expression' --context-file invalid.json
Error: Invalid JSON in context file: invalid.json
```

### Debugging Techniques

```bash
# Use debug mode for detailed error information
cel --debug 'problematic.expression' --context-file context.json

# Use verbose mode to see what CEL is doing
cel --verbose 'expression' --context-file context.json

# Validate JSON files before using them
cat context.json | python -m json.tool

# Test expressions step by step in interactive mode:
cel -i
CEL> context {"user": {"name": "Alice"}}
Context updated: user

CEL> has(user)
true
CEL> has(user.name)
true
CEL> user.name
Alice
```

### Troubleshooting Recipes

#### Expression not evaluating as expected

**Problem**: Expression seems correct but doesn't evaluate as expected.

**Solution**: Check operator precedence and use parentheses:

```bash
# May not work as expected
cel 'a + b * c > d && e || f'

# Clearer with parentheses
cel '((a + (b * c)) > d && e) || f'
```

#### Context not loading

**Problem**: Context variables not available in expression.

**Solutions**:

```bash
# 1. Verify JSON syntax
cat context.json | python -m json.tool

# 2. Check file permissions
ls -la context.json

# 3. Use absolute paths
cel 'expression' --context-file "$(pwd)/context.json"

# 4. Test context loading in interactive mode
cel -i
CEL> load context.json
Loaded context from context.json

CEL> context
{"user": {"name": "Alice"}}
```

#### Type conversion issues

**Problem**: Type mismatches in expressions.

**Solution**: Use explicit type conversion:

```bash
# Instead of: age + "years"
cel 'string(age) + " years"' --context '{"age": 30}'

# Instead of: int_string > 10
cel 'int(int_string) > 10' --context '{"int_string": "15"}'

# Check types in interactive mode:
cel -i
CEL> context {"data": {"value": "123"}}
Context updated: data

CEL> typeof(data.value)
string
CEL> int(data.value)
123
```

## Advanced Recipes

### Complex Data Transformations

```bash
# Transform nested data structures
cel 'users.map(u, {
  "name": u.name,
  "email": u.email,
  "is_admin": u.role == "admin",
  "permissions_count": u.permissions.size()
})' --context-file users.json

# Filter and aggregate
cel 'products.filter(p, p.price > 100).map(p, p.price).fold(sum, 0, sum + item)' \
  --context-file products.json

# Nested filtering
cel 'departments.map(d, {
  "name": d.name,
  "active_employees": d.employees.filter(e, e.active).size()
})' --context-file company.json
```

### Policy Composition

```bash
# Base policies
base_policy='user.verified && user.active'
role_policy='user.role in ["admin", "moderator", "user"]'
time_policy='current_hour >= 9 && current_hour <= 17'

# Combine policies
cel "$base_policy && $role_policy && $time_policy" \
  --context-file user_context.json

# Environment-specific policies
if [[ "$ENV" == "production" ]]; then
  security_policy='user.mfa_enabled && user.last_login_days < 30'
else
  security_policy='true'  # Relaxed for dev/staging
fi

cel "$base_policy && $security_policy" --context-file user_context.json
```

For more advanced usage patterns, see the [Python API documentation](../reference/python-api.md) and other how-to guides in this section.