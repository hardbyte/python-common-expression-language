# CEL Language Basics

**Complete syntax reference for CEL expressions** - Bookmark this page for fast lookups!

This comprehensive guide covers all CEL syntax, operators, and built-in functions. Whether you're just starting with [Quick Start](../getting-started/quick-start.md) or building advanced applications, you'll find the syntax patterns you need here.

> **Tutorial Learning Path:** If you're following the tutorial sequence, this reference complements [Your First Integration](your-first-integration.md) and [Extending CEL](extending-cel.md). Use it to look up syntax as you build practical applications.

> **How to Use This Guide:** Skim through for an overview, then return as a reference when writing expressions. Each section includes practical examples you can test immediately.

## What's Supported

Python CEL implements a comprehensive subset of the CEL specification:

✅ **Core CEL Types**: Integers (signed/unsigned), floats, booleans, strings, bytes, lists, maps, null  
✅ **Arithmetic Operations**: `+`, `-`, `*`, `/`, `%` (strict type matching required)  
✅ **Comparison Operations**: `==`, `!=`, `<`, `>`, `<=`, `>=`  
✅ **Logical Operations**: `&&`, `||`, `!` with short-circuit evaluation  
✅ **String Operations**: Concatenation, indexing, `startsWith()`, `endsWith()`, `contains()`, `size()`  
✅ **Collection Operations**: List/map indexing, `size()`, `.all()`, `.exists()`, `.filter()`  
✅ **Datetime Support**: `timestamp()` and `duration()` functions with arithmetic  
✅ **Member Access**: Dot notation, bracket notation, safe access patterns  
✅ **Ternary Operator**: `condition ? true_value : false_value`  
✅ **Type Functions**: `has()`, conversion functions  
✅ **Python Integration**: Custom functions, Python ↔ CEL type conversion  

See the [CEL specification](https://github.com/google/cel-spec) for the language reference.

## Literals

### Numbers
```cel
42          // Integer
42u         // Unsigned integer  
3.14        // Double/float
-17         // Negative numbers
1e6         // Scientific notation (1,000,000)
```

### Strings
```cel
"hello"           // Basic string
'single quotes'   // Alternative syntax
"with \"quotes\"" // Escaped quotes
"multi\nline"     // Escape sequences
```

### Booleans & Null
```cel
true        // Boolean true
false       // Boolean false
null        // Null value
```

### Lists
```cel
[]                    // Empty list
[1, 2, 3]            // Number list
["a", "b", "c"]      // String list
[1, "mixed", true]   // Mixed types
[1, [2, 3], 4]       // Nested lists
```

### Maps
```cel
{}                           // Empty map
{"name": "Alice"}           // Single entry
{"x": 1, "y": 2}           // Multiple entries
{"user": {"id": 123}}      // Nested maps
```

## Operators

### Arithmetic
```cel
1 + 2       // Addition → 3
5 - 3       // Subtraction → 2
4 * 2       // Multiplication → 8
10 / 3      // Division → 3.333...
10 % 3      // Modulo → 1
-5          // Negation → -5
```

### Comparison
```cel
1 == 1      // Equal → true
1 != 2      // Not equal → true
3 < 5       // Less than → true
5 <= 5      // Less than or equal → true
7 > 3       // Greater than → true
7 >= 7      // Greater than or equal → true
```

### Logical
```cel
true && false    // AND → false
true || false    // OR → true
!true           // NOT → false

// Short-circuit evaluation
false && expensive_function()  // expensive_function() not called
true || expensive_function()   // expensive_function() not called
```

### String Operations
```cel
"hello" + " world"           // Concatenation → "hello world"
"hello"[0]                   // Indexing → "h"
"hello".size()               // Length → 5
"hello".startsWith("he")     // Prefix check → true
"hello".endsWith("lo")       // Suffix check → true
"hello".contains("ell")      // Substring check → true
```

### List Operations
```cel
[1, 2, 3][0]        // Indexing → 1
[1, 2, 3].size()    // Length → 3
1 in [1, 2, 3]      // Membership → true
[1, 2] + [3, 4]     // Concatenation → [1, 2, 3, 4]
```

### Map Operations
```cel
{"x": 1, "y": 2}.x           // Member access → 1
{"x": 1, "y": 2}["x"]        // Bracket access → 1
"x" in {"x": 1, "y": 2}      // Key membership → true
{"x": 1}.size()              // Size → 1
```

## Control Flow

### Ternary Operator
```cel
condition ? value_if_true : value_if_false

// Examples
age >= 18 ? "adult" : "minor"
user.role == "admin" ? "full_access" : "limited_access"
score > 90 ? "A" : score > 80 ? "B" : "C"  // Nested ternary
```

## Built-in Functions

### Type Checking & Conversion
```cel
string(42)         // Convert to string → "42"
int("42")          // Convert to int → 42
double(42)         // Convert to double → 42.0
size("hello")      // Size/length → 5
has(obj.field)     // Field existence → true/false
```

### Date & Time
```cel
// Create timestamps
timestamp("2024-01-01T00:00:00Z")           // From ISO string
timestamp("2024-01-01T00:00:00-05:00")      // With timezone

// Create durations  
duration("1h")        // 1 hour
duration("30m")       // 30 minutes
duration("1h30m")     // 1 hour 30 minutes
duration("45s")       // 45 seconds
duration("2h30m15s")  // Combined

// Arithmetic with time
timestamp("2024-01-01T12:00:00Z") + duration("2h")  // Add duration
timestamp("2024-01-01T14:00:00Z") - duration("1h")  // Subtract duration
```

### Collection Functions
```cel
// Check all items meet condition
[1, 2, 3].all(x, x > 0)           // → true

// Check any item meets condition  
[1, 2, 3].exists(x, x == 2)       // → true

// Filter items by condition
[1, 2, 3, 4].filter(x, x > 2)     // → [3, 4]

// Transform items (limited support)
[1, 2, 3].map(x, x * 2)           // May have type restrictions
```

## Member Access

### Dot Notation
```cel
user.name               // Simple field access
user.profile.verified   // Nested field access
request.headers.accept  // Deep nesting
```

### Bracket Notation
```cel
user["name"]            // String key
user[field_name]        // Variable key
list[0]                 // Index access
list[index]             // Variable index
```

### Safe Access Patterns
```cel
// Check existence before access
has(user.profile) && user.profile.verified

// Use get() with defaults
user.get("age", 0) > 18

// Handle optional fields
has(config.feature) ? config.feature.enabled : false
```

## Common Patterns

### Validation
```cel
// Email validation pattern
email.contains("@") && email.endsWith(".com")

// Range validation
age >= 0 && age <= 120

// Required field validation
has(user.name) && user.name != ""

// Numeric validation 
has(user.age) && user.age > 0
```

### Permission Checking
```cel
// Role-based access
user.role == "admin"

// Multi-role access  
user.role in ["admin", "moderator"]

// Permission-based access
"write" in user.permissions

// Combined conditions
user.verified && user.role == "admin"
```

### Business Rules
```cel
// Pricing rules
base_price * (premium_customer ? 0.9 : 1.0)

// Feature flags
user.beta_tester && feature_flags.new_ui_enabled

// Content filtering
post.public || post.author == user.id

// Time-based rules
hour >= 9 && hour <= 17  // Business hours
```

### Data Filtering
```cel
// Filter active users
users.filter(u, u.active)

// Find admin users
users.filter(u, u.role == "admin") 

// Complex filtering
orders.filter(o, o.total > 100 && o.status == "paid")

// Multi-condition existence check
users.exists(u, u.role == "admin" && u.verified)
```

## Advanced Features

### Regular Expressions (Limited)
```cel
// Basic string matching (use startsWith, endsWith, contains instead)
email.contains("@") && email.endsWith(".com")
```

### Map Construction
```cel
// Note: Direct map construction syntax may be limited
// Use context variables for complex maps
{"status": active ? "enabled" : "disabled"}
```

### List Construction  
```cel
// Dynamic lists from filtering
users.filter(u, u.active).map(u, u.name)  // Names of active users
```

## Type System Notes

### Supported Types
- **int**: 64-bit signed integers
- **uint**: 64-bit unsigned integers  
- **double**: 64-bit floating point
- **string**: UTF-8 strings
- **bool**: true/false
- **list**: Ordered collections
- **map**: Key-value mappings
- **null**: Null/none value
- **timestamp**: Date/time values
- **duration**: Time intervals
- **bytes**: Binary data

### Type Conversion Rules
```cel
// Mixed-type arithmetic requires explicit conversion
1 + 2.0         // ❌ FAILS - Use double(1) + 2.0 → 3.0
double(1) + 2.0  // ✅ Works - Explicit conversion → 3.0
"result: " + string(42)  // ✅ Works - Explicit conversion required

// Comparison rules
1 == 1.0        // true (numeric equality)
"1" == 1        // false (no automatic string conversion)
```

### Key Restrictions
- **Map keys**: Must be int, uint, bool, or string
- **Mixed arithmetic**: Requires explicit type conversion (e.g., `double(1) + 2.0`)
- **Function calls**: Limited to built-ins and registered functions
- **Loops**: Not supported (use collection macros instead)

## Quick Reference Card

| Category | Examples |
|----------|----------|
| **Literals** | `42`, `"hello"`, `true`, `[1,2,3]`, `{"x":1}` |
| **Arithmetic** | `+`, `-`, `*`, `/`, `%` |
| **Comparison** | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| **Logical** | `&&`, `\|\|`, `!` |
| **Access** | `obj.field`, `obj["key"]`, `list[0]` |
| **Ternary** | `condition ? true_val : false_val` |
| **Collections** | `.all()`, `.exists()`, `.filter()`, `.size()` |
| **Strings** | `.startsWith()`, `.endsWith()`, `.contains()` |
| **Time** | `timestamp()`, `duration()` |
| **Safety** | `has()`, `.get()` |

## Next Steps

Now that you've learned the complete CEL syntax, choose your next path based on your goals:

**🎯 Start Building Applications:**
- **[Your First Integration](your-first-integration.md)** - Put these concepts into Python code with Context objects and custom functions
- **[Extending CEL](extending-cel.md)** - Add custom Python functions to create domain-specific expressions

**📚 Understand CEL Philosophy:**
- **[Thinking in CEL](thinking-in-cel.md)** - Core concepts, design principles, and when to use CEL

**🛠️ Solve Specific Problems:**
- **[Access Control Policies](../how-to-guides/access-control-policies.md)** - Build permission systems
- **[Business Logic & Data Transformation](../how-to-guides/business-logic-data-transformation.md)** - Implement configurable business rules
- **[Error Handling](../how-to-guides/error-handling.md)** - Exception types and safe-evaluation patterns

**📖 Reference Material:**
- **[Python API Reference](../reference/python-api.md)** - Complete Python API documentation
- **[CEL specification](https://github.com/google/cel-spec)** - The official CEL spec

**💡 Pro Tip:** If you're new to CEL, we recommend: **Language Basics → [Your First Integration](your-first-integration.md) → [Access Control Policies](../how-to-guides/access-control-policies.md)**

Remember: CEL is **non-Turing complete** by design. No loops, no function definitions, no side effects. This makes it safe, predictable, and perfect for configuration, policies, and business rules!