# CEL Specification Compliance

This document tracks the compliance of this Python CEL implementation with the [Common Expression Language (CEL) specification](https://github.com/google/cel-spec).

## Summary

- **Implementation**: Based on [`cel`](https://crates.io/crates/cel) v0.11.0 Rust crate (formerly cel-interpreter)
- **Estimated Compliance**: ~80% of CEL specification features.
- **Test Coverage**: 300+ tests across 15+ test files including comprehensive CLI testing and upstream improvement detection

## 🚨 Missing Features & Severity Overview

| **Feature** | **Severity** | **Impact** | **Workaround Available** | **Upstream Priority** |
|-------------|--------------|------------|--------------------------|----------------------|
| **OR operator behavior** | 🔴 **HIGH** | Returns original values instead of booleans | Use explicit boolean conversion | **CRITICAL** |
| **String utility functions** | 🟡 **MEDIUM** | Limited string processing capabilities | Use Python context functions | **HIGH** |
| **Type introspection (`type()`)** | 🟡 **MEDIUM** | No runtime type checking | Use Python type checking | **HIGH** |
| **Mixed int/uint arithmetic** | 🟡 **MEDIUM** | Manual type conversion needed | Use explicit casting | **MEDIUM** |
| **Mixed-type arithmetic in macros** | 🟡 **MEDIUM** | Type coercion issues in collections | Ensure type consistency | **MEDIUM** |
| **Bytes concatenation** | 🟢 **LOW** | Cannot concatenate byte arrays | Convert through string | **LOW** |
| **Math functions (`ceil`, `floor`)** | 🟢 **LOW** | No mathematical utilities | Use Python context functions | **LOW** |
| **Optional values** | 🟢 **LOW** | No optional chaining syntax | Use `has()` checks | **FUTURE** |

**Legend**: 🔴 High Impact | 🟡 Medium Impact | 🟢 Low Impact


## Python Type Mappings

📖 **See the complete [Type System documentation](python-api.md#type-system)** for detailed CEL ↔ Python type mappings, map type constraints, and examples.

This implementation correctly follows the CEL specification where maps can have heterogeneous values at runtime while maintaining key type restrictions.

### Arithmetic Operations

| CEL Operation | Result Type | Example | Python Result |
|---------------|-------------|---------|---------------|
| `int + int` | `int` | `1 + 2` | `3` |
| `uint + uint` | `int` | `1u + 2u` | `3` |
| `double + double` | `float` | `1.5 + 2.5` | `4.0` |
| `int + double` | `float` | `1 + 2.0` | `3.0` |
| `double + int` | `float` | `1.5 + 2` | `3.5` |
| `int / int` | `int` | `10 / 2` | `5` |
| `uint % uint` | `int` | `10u % 3u` | `1` |
| `string + string` | `str` | `"hello" + " world"` | `"hello world"` |

#### ✨ Enhanced Mixed-Type Arithmetic

**Ergonomic Improvement**: This library automatically promotes integers to floats when an expression involves float literals or float variables in the context. This provides intuitive behavior for mixed-type arithmetic while preserving integer-only operations.

**Examples of automatic promotion:**
```cel
2 * 3.14        // Automatically treated as 2.0 * 3.14 → 6.28
age * 1.5       // If age=30, treated as 30.0 * 1.5 → 45.0  
score + 0.5     // If score=85, treated as 85.0 + 0.5 → 85.5
```

**Integer operations remain intact:**
```cel
arr[2]          // List indexing still uses integers
age / 10        // If age=30, stays as 30 / 10 → 3 (integer division)
count + 1       // If count=5, stays as 5 + 1 → 6
```

**Technical Implementation**: The underlying Rust code (`preprocess_expression_for_mixed_arithmetic_always`) analyzes expressions and automatically promotes integers to floats when float context is detected, ensuring seamless mixed-type arithmetic without explicit casting.

**Benefits:**
- **Intuitive**: `2 * 3.14` works as expected without requiring `double(2) * 3.14`
- **Safe**: Preserves integer semantics for operations that require them
- **Compatible**: Maintains CEL specification compliance while improving ergonomics

### Logical Operations

| CEL Operation | CEL Spec Result | Our Result | Python Result | Notes |
|---------------|-----------------|------------|---------------|-------|
| `true && false` | `bool` (false) | `bool` | `False` | ✅ Correct |
| `true \|\| false` | `bool` (true) | `bool` | `True` | ✅ Correct |
| `!true` | `bool` (false) | `bool` | `False` | ✅ Correct |
| `42 \|\| false` | `bool` (true) | `int` | `42` | ⚠️ **Behavioral Difference**: Returns original truthy value (JavaScript-like) |
| `0 && true` | `bool` (false) | `bool` | `False` | ✅ Correct (0 is falsy) |
| `'' && true` | `bool` (false) | `bool` | `False` | ✅ Correct (empty string falsy) |

## Working Features

### ✅ Core Data Types
- **Integers**: Full support for 64-bit signed integers (`int`)
- **Unsigned Integers**: Support for 64-bit unsigned integers (`uint`) with `u` suffix
- **Floats**: IEEE 64-bit double precision floating-point  
- **Booleans**: Standard true/false values
- **Strings**: Unicode string support with concatenation
- **Bytes**: Byte sequence support (no concatenation)
- **Null**: Proper null handling as `None`
- **Lists**: Ordered collections with indexing and size operations
- **Maps**: Key-value dictionaries with restricted key types (int, uint, bool, string) and mixed value types (fully CEL compliant)
- **Timestamps**: Full datetime support with timezone awareness
- **Durations**: Time span support via timedelta

### ✅ Operators

#### Arithmetic Operators
- `+` (addition) - Integers, floats, strings
- `-` (subtraction) - Integers, floats  
- `*` (multiplication) - Integers, floats
- `/` (division) - Integers, floats
- `%` (remainder/modulo) - Integers only

#### Comparison Operators  
- `==` (equal) - All types
- `!=` (not equal) - All types
- `<`, `>`, `<=`, `>=` - Numbers, strings (lexicographic)

#### Logical Operators
- `&&` (logical AND) - With short-circuit evaluation
- `||` (logical OR) - With short-circuit evaluation
- `!` (logical NOT) - Boolean negation

#### Other Operators
- `?:` (ternary conditional) - Conditional expressions
- `[]` (indexing) - Lists, maps, strings
- `.` (member access) - Object property access

### ✅ Built-in Functions

| Function | Signature | Purpose | Python Result | Status |
|----------|-----------|---------|---------------|---------|
| `size()` | `size(collection) -> int` | Get collection/string length | `int` | ✅ Working |
| `string()` | `string(value) -> string` | Convert to string | `str` | ✅ Working |
| `bytes()` | `bytes(value) -> bytes` | Convert to bytes | `bytes` | ✅ Working |
| `int()` | `int(value) -> int` | Convert to signed integer | `int` | ✅ Working |
| `uint()` | `uint(value) -> uint` | Convert to unsigned integer | `int` | ✅ Working |
| `double()` | `double(value) -> double` | Convert to double | `float` | ✅ Working |
| `timestamp()` | `timestamp(string) -> timestamp` | Parse timestamp | `datetime.datetime` | ✅ Working |
| `duration()` | `duration(string) -> duration` | Parse duration | `datetime.timedelta` | ✅ Working |
| `has()` | `has(field) -> bool` | Check field presence | `bool` | ✅ Working |
| `matches()` | `string.matches(pattern) -> bool` | Regex matching | `bool` | ✅ Working |
| `min()` | `min(list) -> value` | Find minimum value | Various | ✅ Working |
| `max()` | `max(list) -> value` | Find maximum value | Various | ✅ Working |

### ✅ String Operations
- **contains()**: `"hello".contains("ell")` → `True`
- **startsWith()**: `"hello".startsWith("he")` → `True`
- **endsWith()**: `"hello".endsWith("lo")` → `True`
- **matches()**: `"hello world".matches(".*world")` → `True`
- **String concatenation**: `"hello" + " world"` → `"hello world"`
- **String indexing**: `"hello"[1]` → `"e"`  
- **String size**: `size("hello")` → `5`

### ✅ Collection Macros
- **all()**: `[1,2,3].all(x, x > 0)` → `True`
- **exists()**: `[1,2,3].exists(x, x == 2)` → `True`
- **filter()**: `[1,2,3].filter(x, x > 1)` → `[2.0, 3.0]` (with type coercion)
- **map()**: Limited due to type system restrictions ⚠️ **PARTIAL** (requires type-compatible operations)

### ✅ Python Integration
- **Automatic type conversion**: Seamless Python ↔ CEL type mapping
- **Context variables**: Access Python objects in expressions
- **Custom functions**: Call Python functions from CEL expressions
- **Error handling**: Proper exception propagation
- **Performance**: Efficient evaluation for frequent operations

---

## 👩‍💻 For Developers Using This Library

This section focuses on what you need to know to use CEL effectively in your applications.

### ⚠️ Critical Behavioral Issues You Must Know

!!! warning "Critical Safety Issue: OR Operator Behavior"
    
    **This implementation has a significant behavioral difference from the CEL specification that can impact safety and predictability.**
    
    #### OR Operator Returns Original Values (Not Booleans)
    - **CEL Spec**: `42 || false` should return `true` (boolean)
    - **Our Implementation**: Returns `42` (original integer value)
    - **Impact**: **HIGH** - This can lead to unexpected behavior and logic errors
    
    **Examples of problematic behavior:**
    ```python
from cel import evaluate

# CEL Spec: should return boolean true/false
# Our implementation: returns original values
result = evaluate("42 || false")  # → 42 (not True as expected)
result = evaluate("0 || 'default'")  # → 'default' (not False as expected)

# This can break conditional logic:
try:
    if evaluate("user.age || 0", {"user": {"age": 25}}):  # → 25 (truthy value)
        # This condition may behave unexpectedly
        pass
except Exception:
    # Handle undefined variable case
    pass
    ```
    
    **Mitigation strategies:**
    1. **Explicit boolean conversion**: Use `!!` or explicit comparisons
    2. **Avoid relying on return values** of `||` and `&&` operations
    3. **Test thoroughly** when migrating from other CEL implementations

### 🔧 Safe Patterns & Workarounds

#### String Processing Workarounds
```python
from cel import Context, evaluate

# Since lowerAscii(), upperAscii(), indexOf() are missing:
context = Context()
context.add_function("lower", str.lower)
context.add_function("upper", str.upper) 
context.add_function("find", str.find)

# Add variables to the context
context.add_variable("name", "ALICE")
context.add_variable("text", "hello world")

# Use Python functions in CEL expressions
result = evaluate('lower(name)', context)  # → "alice"
result = evaluate('find(text, "world")', context)  # → 6
```

#### Type Safety Best Practices
```python
from cel import evaluate

# ✅ SAFE: Explicit type conversions for mixed arithmetic
result = evaluate("int(value) + 1", {"value": "42"})  # → 43

# ⚠️ RISKY: Mixed int/uint arithmetic - use explicit conversion
# evaluate("1 + 2u")  # This will fail
result = evaluate("1 + int(2u)")  # → 3 (safe alternative)

# ✅ SAFE: Use has() checks for optional fields
safe_expr = 'has(user.profile) && user.profile.verified'
result = evaluate(safe_expr, {"user": {}})  # → False (graceful handling)
```

#### Production-Safe Error Handling
```python
from cel import evaluate

def safe_evaluate(expression, context):
    """Wrapper for production CEL evaluation with proper error handling."""
    try:
        return evaluate(expression, context)
    except ValueError as e:
        # Parse/syntax errors - log and return safe default
        print(f"CEL syntax error: {e}")
        return False  # Fail-safe default
    except RuntimeError as e:
        # Undefined variables/functions - log and return safe default
        print(f"CEL runtime error: {e}")
        return False  # Fail-safe default
    except TypeError as e:
        # Type mismatches - log and return safe default
        print(f"CEL type error: {e}")
        return False  # Fail-safe default

# Usage in access control (always fail-safe)
policy_expr = "user.verified && user.role == 'admin'"
user_context = {"user": {"verified": True, "role": "admin"}}
access_granted = safe_evaluate(policy_expr, user_context)
```

### 📚 What Works Reliably

Use these features with confidence in production:

- **Core data types**: int, float, bool, string, bytes, lists, maps
- **Arithmetic**: `+`, `-`, `*`, `/`, `%` (watch mixed types)
- **Comparisons**: `==`, `!=`, `<`, `>`, `<=`, `>=`
- **Logical operations**: `&&`, `!` (avoid `||` return values)
- **String operations**: `contains()`, `startsWith()`, `endsWith()`, `matches()`
- **Collection operations**: `size()`, `has()`, indexing with `[]`
- **Macros**: `all()`, `exists()`, `filter()` (ensure type consistency)
- **Type conversions**: `string()`, `int()`, `double()`, `bytes()`
- **Date/time**: `timestamp()`, `duration()` with proper ISO formats

---

## 🔧 For Maintainers & Contributors

This section covers upstream work, detection strategies, and contribution opportunities.

### Known Issues & Missing Features

### ❌ Actually Missing CEL Specification Features

#### 1. String Utility Functions (Upstream Priority: HIGH)
- **Status**: Not implemented in cel v0.11.0
- **Detection**: ✅ Comprehensive detection for all missing functions
- **Missing functions**:
  - `lowerAscii()` - lowercase conversion
  - `upperAscii()` - uppercase conversion  
  - `indexOf(substring)` - find position in strings
  - `lastIndexOf(substring)` - find last occurrence
  - `substring(start, end)` - extract substring
  - `replace(old, new)` - replace substrings
  - `split(delimiter)` - split into list
  - `join(delimiter, list)` - join list to string

**Example of missing functionality**:
```cel
// Should work but doesn't:
"Hello".lowerAscii()               // case conversion
"hello world".indexOf("world")    // substring search  
"hello,world".split(",")          // string splitting
```

**Impact**: Medium - useful for string processing
**Recommendation**: Contribute to cel crate upstream

#### 2. Mixed Signed/Unsigned Integer Arithmetic  
- **Status**: Partially supported  
- **Detection**: ✅ Comprehensive detection for mixed operations
- **CEL Spec**: Supports both `int` and `uint` types with `u` suffix (`1u`, `42u`)
- **Our Implementation**: 
  - ✅ Unsigned literals work: `1u`, `42u` → Python `int`
  - ✅ Pure unsigned arithmetic: `1u + 2u` → `3`
  - ❌ Mixed arithmetic fails: `1 + 2u` throws "Unsupported binary operator"
- **Workaround**: Use explicit conversion: `uint(1) + 2u` or `int(2u) + 1`
- **Impact**: Medium - requires careful type management in expressions

#### 3. Type Introspection Function (Upstream Priority: HIGH)
- **Status**: Not implemented in cel v0.11.0, but foundation exists
- **Detection**: ✅ Full detection with expected behavior tests
- **Missing function**: `type(value) -> string`
- **CEL Spec**: Should return runtime type as string
- **Example**: `type(42)` should return `"int"`
- **Our Implementation**: Throws "Undeclared reference to 'type'"
- **Recent Progress**: Upstream has introduced comprehensive type system infrastructure
- **Impact**: Medium - useful for dynamic type checking
- **Recommendation**: This function may be available in future releases

#### 4. Mixed-Type Arithmetic in Macros (Upstream Priority: MEDIUM)
- **Status**: Type coercion issues in collection operations
- **Problem**: `[1,2,3].map(x, x * 2)` fails with "Unsupported binary operator 'mul': Int(1), Float(2.0)"
- **Impact**: Medium - affects advanced collection processing
- **Workaround**: Ensure type consistency in macro expressions
- **Recommendation**: Better type coercion in cel crate

#### 5. Bytes Concatenation (Upstream Priority: LOW)
- **Status**: Not implemented in cel v0.11.0
- **CEL Spec**: `b'hello' + b'world'` should return `b'helloworld'`
- **Our Implementation**: Throws "Unsupported binary operator" error
- **Workaround**: `bytes(string(part1) + string(part2))`
- **Impact**: Low - rarely used in practice

#### 6. Advanced Built-ins (Upstream Priority: LOW)
- **Detection**: ✅ Full detection for all missing functions
**Missing functions**:
- Math: `ceil()`, `floor()`, `round()` - Mathematical functions
- Collection: Enhanced `in` operator behaviors
- URL/IP: `isURL()`, `isIP()` - Validation functions (available in some CEL implementations)

#### 7. Optional Values (Future Feature)
- **Detection**: ✅ Full detection with expected behavior tests
**Missing features**:
- `optional.of(value)` - create optional
- `optional.orValue(default)` - unwrap with default  
- `?` suffix for optional chaining

**Recent Progress**: Upstream has introduced optional type infrastructure, suggesting these features may be implemented in future releases.

### ⚠️ Behavioral Differences  

#### 1. OR Operator Behavior (CRITICAL ISSUE)
- **Detection**: ✅ We monitor for when this behavior gets fixed upstream
- **Status**: JavaScript-like behavior instead of CEL spec compliance
- **Upstream Priority**: **CRITICAL** - This affects specification conformance

#### 2. Type Coercion in Logical Operations  
- **Our Implementation**: Performs Python-like truthiness evaluation
- **CEL Spec**: May have different rules for type coercion
- **Example**: Empty strings, zero values treated as falsy
- **Impact**: Low - generally intuitive behavior


## 🔮 Future Improvements

The underlying cel-rust implementation continues to evolve with improvements that will benefit this Python wrapper:

### **Enhanced Type System**
- **Type Introspection**: Infrastructure being developed for the missing `type()` function
- **Better Type Checking**: More precise type information and operation support detection
- **Optional Types**: Foundation exists for safer null handling with optional values
- **Improved Error Messages**: Enhanced type information in error reporting

### **Potential Future Features**
```cel
// May be available in future releases
type(42)          // → "int" 
type("hello")     // → "string"
type([1, 2, 3])   // → "list"

// Optional value handling
optional.of(value)           // Create optional value
value.orValue(default)       // Unwrap with default
field?.subfield?.property    // Optional chaining
```

### **Development Benefits**
- **Backward Compatibility**: All improvements maintain API stability
- **Transparent Upgrades**: New features will be additive, not breaking
- **Better Standard Library**: Infrastructure exists for implementing missing string functions
- **CEL Spec Alignment**: Closer alignment with official CEL specification

## Performance Characteristics

### Strengths
- **Expression parsing**: Efficiently handled by Rust cel crate
- **Type conversion**: Optimized Python ↔ Rust boundaries
- **Memory usage**: Reasonable for typical use cases
- **Evaluation speed**: Microsecond-level evaluation times

### Tested Performance Areas
- Large list/dict conversions: Handles 10,000+ elements
- Nested structure traversal: Deep object access
- String processing: Unicode-safe operations
- Mixed-type arithmetic: Efficient numeric operations

## Error Handling

| Feature | Status | Python Behavior | Notes |
| --- | --- | --- | --- |
| Parse errors | ✅ Supported | Raises `ValueError` | All syntax errors handled gracefully |
| Runtime errors | ✅ Supported | Raises `RuntimeError` | Undefined variables/functions, function execution errors |
| Type errors | ✅ Supported | Raises `TypeError` | Type mismatch detection |
| Undefined variables | ✅ Supported | Raises `RuntimeError` | Clear error messages |

### Parser Error Handling ✅

All malformed syntax is now handled gracefully with proper Python exceptions:

**Malformed syntax that raises `ValueError`:**
- Unclosed quotes: `'timestamp("2024-01-01T00:00:00Z")`
- Mixed quotes: `"hello'` or `'hello"`
- Unmatched brackets/parentheses in complex expressions

**Examples of safe error handling:**
```python
from cel import evaluate

# All of these now raise clean ValueError exceptions:
try:
    evaluate("'unclosed quote", {})
except ValueError as e:
    print(f"Parse error: {e}")

try:
    evaluate('"mixed quotes\'', {})
except ValueError as e:
    print(f"Parse error: {e}")
```

**Consistent Behavior:**
Both the CLI tool and the core `evaluate()` function now handle all malformed input consistently by raising appropriate Python exceptions instead of panicking.

## Test Coverage Analysis

### Test Distribution (164 total tests)

| Category | File | Test Count | Coverage Level |
|----------|------|------------|----------------|
| Basic Operations | test_basics.py | 42 | ✅ Comprehensive |
| Arithmetic | test_arithmetic.py | 31 | ✅ Comprehensive |
| Type Conversion | test_types.py | 23 | ✅ Comprehensive |
| Datetime | test_datetime.py | 25 | ✅ Comprehensive |
| Context | test_context.py | 11 | ✅ Good |
| Logical Operators | test_logical_operators.py | 12 | ✅ Good |
| Parser Errors | test_parser_errors.py | 10 | ✅ Good |
| Performance | test_performance_verification.py | 6 | ✅ Basic |
| Documentation | test_documentation.py | 10 | ✅ Good |
| Functions | test_functions.py | 2 | ⚠️ Minimal |
| Edge Cases | test_edge_cases.py | 1 | ⚠️ Minimal |

### Coverage Gaps
- **String method testing**: Limited to basic operations
- **Parser error recovery**: All malformed input now handled gracefully
- **Boundary value testing**: Some edge cases not covered
- **Unicode/encoding edge cases**: Basic coverage only

### 🎯 Upstream Contribution Priorities

#### High Priority (Ready for Contribution)
1. **String utility functions** - ✅ **Detection Ready**
   - Functions: `lowerAscii`, `upperAscii`, `indexOf`, `lastIndexOf`, `substring`, `replace`, `split`, `join`
   - Impact: **MEDIUM** - Widely used in string processing applications
   - Contribution path: cel crate standard library expansion

2. **OR operator CEL spec compliance** - ✅ **Detection Ready**  
   - Issue: Returns original values instead of booleans
   - Impact: **HIGH** - Breaks specification conformance
   - Contribution path: Core logical operation fixes

3. **Type introspection function** - ✅ **Detection Ready**
   - Function: `type()` for runtime type checking  
   - Impact: **MEDIUM** - Useful for dynamic expressions
   - Contribution path: Leverage existing type system infrastructure

#### Medium Priority (Development Needed)
4. **Mixed-type arithmetic in macros** - ✅ **Detection Ready**
   - Issue: Type coercion problems in collection operations
   - Impact: **MEDIUM** - Affects advanced collection processing
   - Contribution path: Macro type system improvements

5. **Mixed int/uint arithmetic**
   - Issue: `1 + 2u` operations fail
   - Impact: **MEDIUM** - Requires careful type management
   - Contribution path: Arithmetic type coercion enhancements

#### Low Priority (Future Features)
6. **Math functions** - ✅ **Detection Ready**
   - Functions: `ceil`, `floor`, `round`
   - Impact: **LOW** - Can be implemented via Python context
   - Contribution path: Standard library expansion

7. **Optional value handling** - ✅ **Detection Ready** 
   - Features: `optional.of()`, `.orValue()`, `?` chaining
   - Impact: **LOW** - Alternative patterns exist
   - Contribution path: Type system extensions

### 🔧 Local Improvement Opportunities  

#### High Impact (Python Library)
1. **Enhanced error handling** - Better Python exception mapping and messages
2. **Performance benchmarking** - Systematic performance testing and optimization  
3. **Comprehensive testing** - Cover newly discovered working features

#### Medium Impact (Documentation & Tooling)
4. **Local utility functions** - Implement missing string functions via Python context
5. **Migration guides** - Help users transition from other CEL implementations
6. **Best practices documentation** - Safe patterns and workarounds

### 🎬 Immediate Actions for Contributors

1. ✅ **Monitoring system active** - All issues have upstream detection
2. 🔄 **Priority: OR operator fix** - Most critical specification compliance issue  
3. 📝 **Priority: String utilities** - High-value, lower-risk contribution opportunity
4. 🚀 **Engage upstream** - Discuss contribution strategy with cel crate maintainers

## Contributing

When adding new features or fixing compliance issues:

1. **Check CEL specification** at https://github.com/google/cel-spec
2. **Add comprehensive tests** for both positive and negative cases
3. **Document behavior** especially if it differs from spec
4. **Update this compliance document** with changes
5. **Consider upstream contributions** to cel crate

## Related Resources

- **CEL Specification**: https://github.com/google/cel-spec
- **cel crate**: https://crates.io/crates/cel  
- **CEL Language Definition**: https://github.com/google/cel-spec/blob/master/doc/langdef.md
- **CEL Homepage**: https://cel.dev/