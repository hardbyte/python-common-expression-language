# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


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
- **Automatic type coercion** for mixed int/float arithmetic:
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

