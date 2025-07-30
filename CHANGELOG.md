# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Updated `cel-interpreter` from 0.9.0 to 0.10.0

### Added
- **Automatic Type Coercion**: Intelligent preprocessing of expressions to handle mixed int/float arithmetic
  - Expressions with float literals automatically convert integer literals to floats
  - Context variables containing floats trigger integer-to-float promotion for compatibility
  - Preserves array indexing with integers (e.g., `list[2]` remains as integer)
- **Enhanced Error Handling**: Added panic handling with `std::panic::catch_unwind` for parser errors
  - Invalid expressions now return proper ValueError instead of crashing the Python process
  - Graceful handling of upstream parser panics from cel-interpreter

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
- PyO3 and related crates: Updated to resolve deprecation warnings

