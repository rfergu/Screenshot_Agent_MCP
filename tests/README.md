# Test Suite Documentation

## Test Categories

### 1. Unit Tests
Fast tests that don't require external dependencies.

**Files:**
- `test_config.py` - Configuration loading
- `test_logger.py` - Logging utilities
- `test_local_mode.py::TestMessageConversion` - Message format conversion

**Run:** `pytest tests/ -m "not smoke and not integration and not performance"`

### 2. Integration Tests
Tests that require dependencies but skip gracefully if not available.

**Files:**
- `test_integration.py` - OCR, vision, batch processing workflows
- `test_local_mode.py::TestLocalModeIntegration` - Local mode with AI Foundry server

**Behavior:** Skip with warning if dependencies aren't available

**Run:** `pytest tests/ -m integration`

### 3. Smoke Tests 🔥
**Critical:** Tests that FAIL if local environment isn't configured correctly.

**Files:**
- `test_smoke_local.py` - End-to-end local mode verification

**Requirements:**
```bash
# AI Foundry CLI
brew install azure/ai-foundry/foundry

# Phi-4 model
foundry model get phi-4

# Server running
foundry run phi-4
```

**Behavior:** FAIL with helpful error if environment is misconfigured

**Run:**
```bash
# Run only smoke tests
pytest tests/ -m smoke

# Run all tests INCLUDING smoke
pytest tests/

# Run all tests EXCLUDING smoke (default for CI)
pytest tests/ -m "not smoke"
```

### 4. Performance Tests
Benchmarking tests that verify performance targets.

**Files:**
- `test_performance.py` - OCR/vision speed, batch scaling

**Run:** `pytest tests/ -m performance`

## Quick Reference

```bash
# Run everything except smoke tests (safe default)
pytest tests/ -m "not smoke"

# Run only smoke tests (when you have local server running)
pytest tests/ -m smoke

# Run all tests including smoke (assumes full local setup)
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_smoke_local.py

# Run specific test
pytest tests/test_smoke_local.py::TestLocalModeSmoke::test_simple_chat_completion
```

## CI/CD Recommendations

### GitHub Actions / CI Pipeline
```yaml
# Exclude smoke tests in CI (no local server)
pytest tests/ -m "not smoke"
```

### Pre-commit Hook
```bash
# Quick sanity check (unit tests only)
pytest tests/ -m "not smoke and not integration and not performance" --tb=short
```

### Local Development
```bash
# After setting up AI Foundry local server
foundry run phi-4  # In separate terminal
pytest tests/      # Run all tests including smoke
```

## Test Markers

Configured in `pytest.ini`:

- `@pytest.mark.smoke` - Fails if environment isn't set up
- `@pytest.mark.integration` - Skips if dependencies unavailable
- `@pytest.mark.performance` - Benchmarking tests
- `@pytest.mark.asyncio` - Async test (handled by pytest-asyncio)

## When Tests Fail

### Smoke Test Failure
```
FAILED test_smoke_local.py::test_local_server_is_running
AssertionError: AI Foundry server is not running!
  Start with: foundry run phi-4
```

**Fix:** Start the local server or skip smoke tests:
```bash
pytest tests/ -m "not smoke"
```

### Integration Test Skipped
```
SKIPPED test_local_mode.py::test_simple_chat_query
Reason: AI Foundry server not running
```

**This is normal** - integration tests skip gracefully. To run them:
```bash
foundry run phi-4  # Start server
pytest tests/ -m integration
```

## Test Coverage Goals

- Unit tests: >90% coverage
- Integration tests: All major workflows
- Smoke tests: All critical paths for local mode
- Performance tests: All NFR requirements from spec

## Adding New Tests

### For Unit Tests
```python
def test_my_feature():
    """Test description."""
    assert my_function() == expected_value
```

### For Integration Tests (skip if unavailable)
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_integration():
    """Test description."""
    if not dependency_available():
        pytest.skip("Dependency not available")

    result = await my_async_function()
    assert result is not None
```

### For Smoke Tests (fail if unavailable)
```python
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_my_critical_path():
    """SMOKE TEST: Test description."""
    assert dependency_available(), (
        "Dependency not configured!\n"
        "Setup instructions: ...\n"
        "Or skip with: pytest -m 'not smoke'"
    )

    result = await my_async_function()
    assert result is not None
```
