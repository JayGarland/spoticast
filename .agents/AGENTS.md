# Resonova Project-Scoped Rules

## Test Suite Execution
- **Variety and Episode Tests**: Do NOT execute `tests/test_variety_episodes.py` directly as a standalone script or in a manner that invokes `_run_tests()` recursively. 
- To run these tests safely and avoid infinite recursion, run the module-level test runner or execute it with a python inline command that targets only the necessary assertions:
  ```powershell
  uv run python -c "import tests.test_variety_episodes as t; t._run_tests()"
  ```
  Note that this will trigger recursive runs because of a recursive call in `_test_no_taste_unchanged()`. If you need to debug specific functionality, run the individual test functions directly.
