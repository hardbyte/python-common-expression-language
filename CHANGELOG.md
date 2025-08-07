# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING**: Updated `cel` crate (formerly `cel-interpreter`) from 0.10.0 to 0.11.0
  - Crate renamed from `cel-interpreter` to `cel` upstream
  - API changes to function registration system using `IntoFunction` trait
  - Python function integration now uses `Arguments` extractor for variadic argument handling
  - All imports updated from `cel_interpreter::` to `::cel::`

### Dependencies Updated
- cel-interpreter → cel: 0.10.0 → 0.11.0 (crate renamed, major API breaking changes)
  - New function registration system using `IntoFunction` trait
  - Improved extractors system with `Arguments`, `This`, and `Identifier`
  - Better error handling and performance improvements
- pyo3: 0.25.0 → 0.25.1 (latest stable)
- pyo3-log: 0.12.1 → 0.12.4 (latest compatible version)

### Notes
- **CEL v0.11.0 Integration**: Updated to new `IntoFunction` trait system while maintaining full Python API compatibility
  - All Python functions still work identically from user perspective
  - Internal implementation now uses `Arguments` extractor for better performance
  - No breaking changes to Python API - all existing code continues to work
- **Future-Proofing**: Analysis of upcoming cel-rust changes shows exciting developments:
  - Enhanced type system infrastructure for better type introspection
  - Foundation for `type()` function (currently missing from CEL spec compliance)
  - Optional value infrastructure for safer null handling
  - All future changes maintain backward compatibility with our wrapper
- **Build Status**: All 287 tests pass with current dependency versions

## [0.4.1] - 2025-08-02

### Added
- **Automatic Type Coercion**: Intelligent preprocessing of expressions to handle mixed int/float arithmetic
  - Expressions with float literals automatically convert integer literals to floats
  - Context variables containing floats trigger integer-to-float promotion for compatibility
  - Preserves array indexing with integers (e.g., `list[2]` remains as integer)
- **Enhanced Error Handling**: Added panic handling with `std::panic::catch_unwind` for parser errors
  - Invalid expressions now return proper ValueError instead of crashing the Python process
  - Graceful handling of upstream parser panics from cel-interpreter

### Changed
- Updated `cel-interpreter` from 0.9.0 to 0.10.0

### Fixed
- **Mixed-type arithmetic compatibility**: Expressions like `3.14 * 2`, `2 + 3.14`, `value * 2` (where value is float) now work as expected
- **Parser panic handling**: Implemented `std::panic::catch_unwind` to gracefully handle upstream parser panics
  - Users get proper error messages instead of application crashes
- Fixed deprecation warnings by updating to compatible PyO3 APIs

### Known Issues
- **Bytes Concatenation**: cel-interpreter 0.10.0 does not implement bytes concatenation with `+` operator
  - **CEL specification requires**: `b'hello' + b'world'` should work  
  - **Current behavior**: Returns "Unsupported binary operator 'add'" error
  - **Workaround**: Use `bytes(string(part1) + string(part2))` for concatenation
  - **Status**: This is a missing feature in the cel-interpreter crate, not a design limitation

### Dependencies Updated
- cel-interpreter: 0.9.0 → 0.10.0 (major version update with breaking changes)
- log: 0.4.22 → 0.4.27
- chrono: 0.4.38 → 0.4.41
- pyo3: 0.22.6 → 0.25.0 (major API upgrade with IntoPyObject migration)
- pyo3-log: 0.11.0 → 0.12.1 (compatible with pyo3 0.25.0)

### Notes
- **PyO3 0.25.0 Migration**: Migrated from deprecated `IntoPy` trait to new `IntoPyObject` API
- **API Improvements**: New conversion system provides better error handling and type safety
- **Build Status**: All 120 tests pass with current dependency versions

