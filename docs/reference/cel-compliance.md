# CEL Specification Compliance

This document tracks the compliance of this Python CEL implementation with the [Common Expression Language (CEL) specification](https://github.com/google/cel-spec).

## Summary

- **Implementation**: Based on [`cel-interpreter`](https://crates.io/crates/cel-interpreter) v0.10.0 Rust crate
- **Estimated Compliance**: ~80% of CEL specification features.
- **Test Coverage**: 200+ tests across 12 test files including comprehensive CLI testing


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

## Known Issues & Missing Features

### ❌ Actually Missing CEL Specification Features

#### 1. String Utility Functions (Upstream Priority: HIGH)
- **Status**: Not implemented in cel-interpreter v0.10.0
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
**Recommendation**: Contribute to cel-interpreter upstream

#### 2. Mixed Signed/Unsigned Integer Arithmetic  
- **Status**: Partially supported  
- **CEL Spec**: Supports both `int` and `uint` types with `u` suffix (`1u`, `42u`)
- **Our Implementation**: 
  - ✅ Unsigned literals work: `1u`, `42u` → Python `int`
  - ✅ Pure unsigned arithmetic: `1u + 2u` → `3`
  - ❌ Mixed arithmetic fails: `1 + 2u` throws "Unsupported binary operator"
- **Workaround**: Use explicit conversion: `uint(1) + 2u` or `int(2u) + 1`
- **Impact**: Medium - requires careful type management in expressions

#### 3. Type Introspection Function (Upstream Priority: HIGH)
- **Status**: Not implemented in cel-interpreter v0.10.0
- **Missing function**: `type(value) -> string`
- **CEL Spec**: Should return runtime type as string
- **Example**: `type(42)` should return `"int"`
- **Our Implementation**: Throws "Undeclared reference to 'type'"
- **Impact**: Medium - useful for dynamic type checking
- **Recommendation**: Contribute to cel-interpreter upstream

#### 4. Mixed-Type Arithmetic in Macros (Upstream Priority: MEDIUM)
- **Status**: Type coercion issues in collection operations
- **Problem**: `[1,2,3].map(x, x * 2)` fails with "Unsupported binary operator 'mul': Int(1), Float(2.0)"
- **Impact**: Medium - affects advanced collection processing
- **Workaround**: Ensure type consistency in macro expressions
- **Recommendation**: Better type coercion in cel-interpreter

#### 5. Bytes Concatenation (Upstream Priority: LOW)
- **Status**: Not implemented in cel-interpreter v0.10.0
- **CEL Spec**: `b'hello' + b'world'` should return `b'helloworld'`
- **Our Implementation**: Throws "Unsupported binary operator" error
- **Workaround**: `bytes(string(part1) + string(part2))`
- **Impact**: Low - rarely used in practice

#### 6. Advanced Built-ins (Upstream Priority: LOW)
**Missing functions**:
- Math: `ceil()`, `floor()`, `round()` - Mathematical functions
- Collection: Enhanced `in` operator behaviors
- URL/IP: `isURL()`, `isIP()` - Validation functions (available in some CEL implementations)

#### 7. Optional Values (Future Feature)
**Missing features**:
- `optional.of(value)` - create optional
- `optional.orValue(default)` - unwrap with default
- `?` suffix for optional chaining

### ⚠️ Behavioral Differences

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
result = evaluate("42 || false")  # Returns 42, not True
result = evaluate("0 || 'default'")  # Returns 'default', not False

# This can break conditional logic:
try:
    if evaluate("user.age || 0", {"user": {"age": 25}}):  # Intended to check truthiness
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

#### 2. Type Coercion in Logical Operations  
- **Our Implementation**: Performs Python-like truthiness evaluation
- **CEL Spec**: May have different rules for type coercion
- **Example**: Empty strings, zero values treated as falsy
- **Impact**: Low - generally intuitive behavior


## Performance Characteristics

### Strengths
- **Expression parsing**: Efficiently handled by Rust cel-interpreter
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

## Recommendations

### High Priority (Upstream Contributions)
1. **String utility functions** (`lowerAscii`, `upperAscii`, `indexOf`, `lastIndexOf`, `substring`, `replace`, `split`, `join`)
2. **Type introspection function** (`type()` for runtime type checking)
3. **Better error messages** for unsupported operations
4. **Mixed-type arithmetic** improvements in macros

### Medium Priority (Local Improvements)
1. **Enhanced error handling** with better Python exception mapping
2. **Local utility functions** (can implement `lowerAscii`/`upperAscii` via Python context)
3. **Comprehensive testing** for newly discovered working features
4. **Performance benchmarking** of macro operations

### Low Priority (Future Features)
1. **Math functions** (`ceil`, `floor`, `round`) - contribute upstream
2. **Advanced validation functions** (`isURL`, `isIP`) - domain-specific
3. **Optional value handling** - future CEL specification feature

### Immediate Actions
1. ✅ **Update compliance documentation** with new findings
2. 🔄 **Implement better local error handling** (high impact, local solution)
3. 📝 **Add tests for newly discovered working features**
4. 🚀 **Consider upstream contributions** to cel-interpreter for missing string functions

## Contributing

When adding new features or fixing compliance issues:

1. **Check CEL specification** at https://github.com/google/cel-spec
2. **Add comprehensive tests** for both positive and negative cases
3. **Document behavior** especially if it differs from spec
4. **Update this compliance document** with changes
5. **Consider upstream contributions** to cel-interpreter crate

## Related Resources

- **CEL Specification**: https://github.com/google/cel-spec
- **cel-interpreter crate**: https://crates.io/crates/cel-interpreter  
- **CEL Language Definition**: https://github.com/google/cel-spec/blob/master/doc/langdef.md
- **CEL Homepage**: https://cel.dev/