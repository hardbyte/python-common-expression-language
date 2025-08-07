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
```cel
// Role-based access
user.role in ["admin", "editor"] && resource.type == "document"

// Time-sensitive access
user.permissions.includes("read") && now() < expires_at

// Multi-tenant authorization
user.tenant_id == resource.tenant_id && user.role != "guest"
```

**→ [Full Access Control Guide](how-to-guides/access-control-policies.md)**

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
```cel
// Validate email format
email.matches(r'^[^@]+@[^@]+\.[^@]+$') && size(email) <= 254

// Calculate pricing with business rules
base_price * (1 + tax_rate) * (customer.vip ? 0.9 : 1.0)

// Transform user data
{
  "name": user.first_name + " " + user.last_name,
  "can_vote": user.age >= 18,
  "tier": user.spend > 1000 ? "gold" : "silver"
}
```

**→ [Full Data Transformation Guide](how-to-guides/business-logic-data-transformation.md)**

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
```cel
// Multi-field search
(name.contains(query) || description.contains(query)) && status == "active"

// Date range filtering
created_at >= start_date && created_at <= end_date

// Hierarchical filtering
category.startsWith(user_category) && price <= budget
```

**→ [Full Query Filters Guide](how-to-guides/dynamic-query-filters.md)**

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
```cel
// Safe property access
has(user.profile) && user.profile.verified

// Null coalescing patterns
user.display_name if has(user.display_name) else user.email

// Validation with fallbacks
size(input) > 0 ? input.trim() : "default_value"
```

**→ [Full Error Handling Guide](how-to-guides/error-handling.md)**

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
```bash
# Test expressions interactively
cel --interactive

# Batch process with file input
cel --file expressions.cel --context data.json

# Pipeline integration
echo '{"user": "admin"}' | cel 'user == "admin"'
```

**→ [Full CLI Guide](how-to-guides/cli-recipes.md)**

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
- Always validate context data
- Use `has()` for optional fields
- Cache compiled expressions
- Implement proper error handling
- Monitor expression performance

**→ [Full Production Guide](how-to-guides/production-patterns-best-practices.md)**

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