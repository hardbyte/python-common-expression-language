# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Updated

- Updated cel-rust from 0.12.0 to 0.13.0.

### Added

- `Context.set_variable_resolver(callback)` exposes cel 0.13's `VariableResolver` trait to Python. The callback receives a variable name and returns the value (or `None` to fall through to variables registered with `add_variable`). Useful for backing a CEL context with on-demand sources (database lookups, lazily-loaded config files, etc.) without materializing the full set of variables upfront. Exceptions raised by the resolver are logged and treated as "not handled".
- Idiomatic Python exception mapping for several CEL runtime errors that previously fell through to `ValueError`:
  - Arithmetic overflow → `OverflowError` (e.g. `9223372036854775807 + 1`, including the new overflow-safe int math in cel 0.13).
  - Division by zero / modulo by zero → `ZeroDivisionError`.
  - List index out of bounds → `IndexError`.
  - Missing map key (e.g. `{"a": 1}.b`) → `KeyError`.

### Changed

- **Behaviour change** (cel 0.13): bytes concatenation with `+` now works per the CEL spec (`b'hello' + b'world'` returns `b'helloworld'`). Previously raised `TypeError`.
- **Behaviour change** (cel 0.13): logical `&&` and `||` are now "err-resilient" per CEL spec — `X && false` short-circuits to `false` and `X || true` short-circuits to `true` even when `X` is not a boolean. Conversely, `false || X` and `true && X` now raise `TypeError` when `X` is not boolean (previously `false || X` returned `X`).
- **Error mapping**: more operations now route through CEL's `NoSuchOverload` (e.g. `1 + 2u`, `1 * 2u`, indexing into a string). These map to `TypeError` with a generic message listing common causes and conversion functions (`int(x)`, `uint(x)`, `double(x)`). The previous type-specific messages (e.g. "Cannot mix signed and unsigned integers") are still produced for the operand orderings cel-rust dispatches via `UnsupportedBinaryOperator`. Tests asserting on specific message text may need updating.
- **Behaviour change** (cel 0.13): no implicit type coercion on map index access; indexing into a string now raises `TypeError` (`NoSuchOverload`) per CEL spec.
- **Behaviour change** (cel 0.13): integer arithmetic overflow now raises `OverflowError` instead of silently wrapping. Affects `+`, `-`, `*` on both `int` and `uint` at the type's bounds.

### Performance

- Microbenchmarks comparing cel 0.13 vs 0.12 (release build, taking the min of 3 runs per scenario):

  | Scenario              | compile  | compiled execute | evaluate |
  |-----------------------|---------:|-----------------:|---------:|
  | `x + y * 2`           |   +2.8%  |          +8.4%   |   +3.3%  |
  | `greet + ' ' + name`  |  +23.0%  |          +4.3%   |   +0.5%  |
  | `size(items)` (1k)    |   ~0%    |         +63.4%   |  +53.2%  |
  | map field access      |   −7.1%  |          +8.3%   |   +6.5%  |
  | custom Python fn      |   +1.4%  |          +6.7%   |   −1.9%  |

  Most scenarios are within ~10% of 0.12; the `size(items)` regression on a 1000-element list is cel 0.13's dyn-Val refactor adding per-element boxing overhead at the Python→CEL boundary. Smaller lists are not noticeably affected.

## [0.5.6] - 2026-02-07

### Fixed

- Mapping conversion now respects dict subclasses and custom `Mapping` implementations, preserving `__getitem__` behavior for member access (issue #22)

## [0.5.5] - 2026-02-07

### Added

- `compile()` API and `Program.execute()` for reuse and performance
- `OptionalValue` wrapper to expose CEL optional values in Python
- Compile vs execute benchmark script (`examples/performance/compile_execute_benchmark.py`)

### Updated

- Updated cel-rust from 0.11.6 to 0.12.0

### Changed

- Documentation: pre-compilation guidance and OptionalValue examples

## [0.5.4] - 2025-10-23

### Updated

- Updated cel-rust from 0.11.4 to 0.11.6
- Updated PyO3 from 0.25.1 to 0.27.1

### Changed

- Reduced logging verbosity
## [0.5.3] - 2025-10-14

- Added new `cel.stdlib` module with Python implementations of CEL functions missing from upstream cel-rust.
- CLI automatically includes all stdlib functions
- Minor removed warning level logging in cel crate

## [0.5.2] - 2025-09-12

### 🚨 Breaking Changes

- **Python evaluation mode removed**: The library now operates exclusively in strict CEL mode
  - **Removed**: `EvaluationMode.PYTHON` and all automatic integer-to-float promotion
  - **Removed**: `mode` parameter from `evaluate()` function
  - **Removed**: `--mode` CLI option
  - **Behavior change**: Mixed arithmetic like `1 + 2.5` now raises `TypeError` instead of automatically promoting to `3.5`
  - **Migration**: Use explicit type conversion (e.g., `double(1) + 2.5`) for mixed arithmetic
  - **Rationale**: Eliminates complex AST preprocessing that was breaking `has()` short-circuiting and other CEL functions

### 🐛 Fixed

- **CEL function short-circuiting**: Fixed issue where `has()` and other CEL functions failed due to AST preprocessing interference
- **String literal corruption**: Eliminated string literal modification that occurred during integer promotion preprocessing

### Updated

- Updated cel crate from v0.11.0 to v0.11.1
- Updated documentation to reflect strict CEL mode operation
- Updated tests to work with strict CEL mode only
- Removed complex preprocessing logic

## [0.5.1] - 2025-08-11

### ✨ Added

- **EvaluationMode enum**: Control type handling behavior in CEL expressions *(deprecated and removed in later version)*
  - `EvaluationMode.PYTHON` (default for Python API): Python-friendly type promotions *(removed)*
  - `EvaluationMode.STRICT` (default for CLI): Strict CEL type rules with no coercion *(now the only mode)*
- **Type checking support**: Added complete type stub files (`.pyi`) for PyO3 extension


## [0.5.0] - 2025-08-08

### 🚨 Breaking Changes (Rust API only)
- Upgraded `cel` crate (formerly `cel-interpreter`) 0.10.0 → 0.11.0:
  - Function registration now uses `IntoFunction` trait.
  - Python integration updated to use `Arguments` extractor for variadic args.
  - Imports renamed from `cel_interpreter::` to `cel::`.
  - **No changes to Python API** – all existing code continues to work.

### ✨ Changed
- Internal: Refactored Python integration to match new CEL API.
- Updated dependencies:
  - pyo3: 0.25.0 → 0.25.1
  - pyo3-log: 0.12.1 → 0.12.4

### 🗒 Maintainer Notes
- Prepared for upcoming CEL Rust features:
  - Enhanced type system & introspection
  - `type()` function support
  - Optional value handling

## [0.4.1] - 2025-08-02

### ✨ Added
- **Automatic type coercion** for mixed int/float arithmetic *(deprecated and removed in later version)*:
  - Float literals automatically promote integer literals to floats.
  - Context variables containing floats trigger int → float promotion.
  - Preserves array indexing with integers (e.g., `list[2]` stays integer).
- **Enhanced error handling**:
  - Parser panics now caught with `std::panic::catch_unwind`.
  - Invalid expressions return a `ValueError` instead of crashing Python.

### 🐛 Fixed
- Mixed-type arithmetic now works in expressions like:
  - `3.14 * 2`
  - `2 + 3.14`
  - `value * 2` (where `value` is float)
- Parser panics from `cel-interpreter` handled gracefully with proper error messages.
- Updated to latest PyO3 APIs to remove deprecation warnings.

### ⚠ Known Issues
- **Bytes concatenation** (`b'hello' + b'world'`) unsupported in cel-interpreter 0.10.0.
  - **Spec requires**: should work.
  - **Current**: returns `"Unsupported binary operator 'add'"`.
  - **Workaround**: `bytes(string(part1) + string(part2))`.
  - **Status**: Missing feature in cel-interpreter, not in our wrapper.

### 📦 Dependencies
- cel-interpreter: 0.9.0 → 0.10.0 (breaking changes internally)
- log: 0.4.22 → 0.4.27
- chrono: 0.4.38 → 0.4.41
- pyo3: 0.22.6 → 0.25.0 (major API upgrade to `IntoPyObject`)
- pyo3-log: 0.11.0 → 0.12.1 (compatible with PyO3 0.25.0)

### 🗒 Maintainer Notes
- **PyO3 migration**: moved from deprecated `IntoPy` to new `IntoPyObject` API.
- New conversion system improves error handling and type safety.
- All 120 tests pass on current dependency set.
