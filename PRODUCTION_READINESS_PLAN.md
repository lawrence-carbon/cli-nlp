# Production Readiness Plan: QTC (Query to Command)

**Version:** 0.4.0 → 1.0.0  
**Date:** 2025-01-27  
**Status:** Implementation Plan  
**Goal:** Make QTC production-ready across all dimensions: dev-friendly, geek-friendly, bug-free, robust, and fast

---

## Executive Summary

This plan addresses production readiness gaps identified through multi-agent analysis. The work is organized into 4 phases over an estimated 6-8 weeks, prioritizing critical reliability and robustness improvements before feature enhancements.

**Key Metrics:**
- **Current Test Coverage:** 79% → **Target:** 85%+
- **Current Error Handling:** Basic → **Target:** Comprehensive with retry logic
- **Current Observability:** None → **Target:** Structured logging + metrics
- **Current Performance:** Unmeasured → **Target:** Benchmarked and optimized

---

## Phase 1: Critical Reliability & Error Handling (Weeks 1-2)

**Priority:** 🔴 **CRITICAL**  
**Goal:** Eliminate silent failures, add comprehensive error handling, and ensure graceful degradation

### 1.1 Implement Structured Logging

**Problem:** No logging infrastructure exists. Errors are only printed to console, making debugging and production monitoring impossible.

**Implementation:**

```python
# cli_nlp/logger.py (NEW FILE)
"""Structured logging configuration for CLI-NLP."""

import logging
import sys
from pathlib import Path
from typing import Any

from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    verbose: bool = False,
) -> logging.Logger:
    """
    Set up structured logging with Rich console handler and optional file handler.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        verbose: Enable DEBUG level logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("cli_nlp")
    logger.setLevel(logging.DEBUG if verbose else getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Rich console handler for beautiful output
    console_handler = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_path=True,
        markup=True,
    )
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # File handler for persistent logs
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
```

**Tasks:**
- [ ] Create `cli_nlp/logger.py` with structured logging setup
- [ ] Add `--verbose` / `-v` flag to CLI for debug logging
- [ ] Add `--log-file` option to write logs to file
- [ ] Replace all `console.print()` error messages with `logger.error()`
- [ ] Add logging to all managers (ConfigManager, CacheManager, etc.)
- [ ] Add request/response logging for API calls (with sensitive data redaction)
- [ ] Update tests to verify logging behavior

**Acceptance Criteria:**
- Logging works in both console and file modes
- Sensitive data (API keys) is redacted in logs
- Log levels work correctly (DEBUG, INFO, WARNING, ERROR)
- Tests verify logging behavior

**Files to Modify:**
- `cli_nlp/logger.py` (NEW)
- `cli_nlp/cli.py` (add logging flags)
- `cli_nlp/command_runner.py` (add logging)
- `cli_nlp/config_manager.py` (add logging)
- `cli_nlp/cache_manager.py` (add logging)
- All other manager files

---

### 1.2 Add Retry Logic with Exponential Backoff

**Problem:** No retry logic for API calls. Network failures or transient errors cause immediate failures.

**Implementation:**

```python
# cli_nlp/retry.py (NEW FILE)
"""Retry logic with exponential backoff for API calls."""

import time
from functools import wraps
from typing import Any, Callable, TypeVar

from cli_nlp.logger import setup_logging

logger = setup_logging()
T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions


def retry_with_backoff(config: RetryConfig | None = None):
    """
    Decorator for retrying functions with exponential backoff.
    
    Usage:
        @retry_with_backoff(RetryConfig(max_attempts=3))
        def api_call():
            ...
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            delay = config.initial_delay
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt == config.max_attempts:
                        logger.error(
                            f"Failed after {config.max_attempts} attempts: {e}",
                            exc_info=True,
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * config.exponential_base, config.max_delay)
            
            # Should never reach here, but type checker needs it
            raise last_exception  # type: ignore
            
        return wrapper
    return decorator
```

**Tasks:**
- [ ] Create `cli_nlp/retry.py` with retry decorator
- [ ] Apply retry logic to `litellm.completion()` calls
- [ ] Add retry configuration to config file
- [ ] Add tests for retry behavior
- [ ] Document retry behavior in README

**Acceptance Criteria:**
- API calls retry on transient failures
- Exponential backoff works correctly
- Max attempts respected
- Logs show retry attempts
- Tests verify retry behavior

**Files to Modify:**
- `cli_nlp/retry.py` (NEW)
- `cli_nlp/command_runner.py` (apply retry decorator)
- `cli_nlp/config_manager.py` (add retry config)
- `tests/test_retry.py` (NEW)

---

### 1.3 Comprehensive Error Handling

**Problem:** Silent failures, unclear error messages, no recovery paths.

**Implementation:**

```python
# cli_nlp/exceptions.py (NEW FILE)
"""Custom exceptions for CLI-NLP."""

class QTCError(Exception):
    """Base exception for all QTC errors."""
    pass


class ConfigurationError(QTCError):
    """Configuration-related errors."""
    pass


class APIError(QTCError):
    """API-related errors."""
    pass


class CacheError(QTCError):
    """Cache-related errors."""
    pass


class CommandExecutionError(QTCError):
    """Command execution errors."""
    pass


class ValidationError(QTCError):
    """Input validation errors."""
    pass
```

**Tasks:**
- [ ] Create `cli_nlp/exceptions.py` with custom exceptions
- [ ] Replace silent failures with proper exceptions
- [ ] Add user-friendly error messages
- [ ] Add error recovery suggestions
- [ ] Update all error handling to use custom exceptions
- [ ] Add error handling tests

**Acceptance Criteria:**
- All errors have clear, actionable messages
- No silent failures
- Errors include recovery suggestions
- Tests cover error scenarios

**Files to Modify:**
- `cli_nlp/exceptions.py` (NEW)
- `cli_nlp/cache_manager.py` (fix silent failures)
- `cli_nlp/config_manager.py` (add validation)
- `cli_nlp/command_runner.py` (improve error handling)
- All manager files

---

### 1.4 Input Validation

**Problem:** No validation of user inputs, config files, or API responses.

**Implementation:**

```python
# cli_nlp/validation.py (NEW FILE)
"""Input validation utilities."""

from cli_nlp.exceptions import ValidationError


def validate_query(query: str) -> str:
    """
    Validate user query input.
    
    Args:
        query: User query string
        
    Returns:
        Validated and normalized query
        
    Raises:
        ValidationError: If query is invalid
    """
    if not query or not isinstance(query, str):
        raise ValidationError("Query must be a non-empty string")
    
    query = query.strip()
    
    if not query:
        raise ValidationError("Query cannot be empty")
    
    if len(query) > 10000:  # Reasonable limit
        raise ValidationError(
            f"Query too long ({len(query)} chars). Maximum length: 10000 characters"
        )
    
    return query


def validate_config(config: dict) -> dict:
    """
    Validate configuration structure.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Validated configuration
        
    Raises:
        ValidationError: If config is invalid
    """
    # Implementation here
    return config
```

**Tasks:**
- [ ] Create `cli_nlp/validation.py`
- [ ] Add query validation
- [ ] Add config validation
- [ ] Add API response validation
- [ ] Add validation tests

**Acceptance Criteria:**
- All inputs validated before processing
- Clear validation error messages
- Tests cover validation scenarios

**Files to Modify:**
- `cli_nlp/validation.py` (NEW)
- `cli_nlp/cli.py` (add validation)
- `cli_nlp/config_manager.py` (add validation)
- `cli_nlp/command_runner.py` (add validation)

---

## Phase 2: Testing & Quality Assurance (Weeks 3-4)

**Priority:** 🟠 **HIGH**  
**Goal:** Increase test coverage to 85%+, add integration tests, and improve test quality

### 2.1 Increase Test Coverage

**Current:** 79% coverage  
**Target:** 85%+ coverage

**Tasks:**
- [ ] Identify uncovered code paths (use coverage report)
- [ ] Add tests for error scenarios
- [ ] Add tests for edge cases
- [ ] Add tests for validation logic
- [ ] Add tests for retry logic
- [ ] Add tests for logging
- [ ] Add property-based tests for complex logic

**Focus Areas:**
- Error handling paths (currently low coverage)
- Edge cases (empty inputs, malformed data)
- Concurrent access scenarios
- File I/O error scenarios

**Acceptance Criteria:**
- Coverage ≥ 85%
- All error paths tested
- Edge cases covered
- Integration tests added

**Files to Create/Modify:**
- `tests/test_error_handling.py` (NEW)
- `tests/test_validation.py` (NEW)
- `tests/test_retry.py` (NEW)
- `tests/test_logging.py` (NEW)
- `tests/test_integration.py` (NEW)
- All existing test files (expand coverage)

---

### 2.2 Integration Tests

**Problem:** No end-to-end integration tests.

**Tasks:**
- [ ] Create integration test suite
- [ ] Test full command generation flow
- [ ] Test multi-provider switching
- [ ] Test cache invalidation
- [ ] Test history persistence
- [ ] Test error recovery scenarios

**Acceptance Criteria:**
- Integration tests cover critical paths
- Tests run in CI/CD
- Tests verify real-world scenarios

**Files to Create:**
- `tests/integration/` (NEW DIRECTORY)
- `tests/integration/test_full_flow.py`
- `tests/integration/test_provider_switching.py`
- `tests/integration/test_cache_integration.py`

---

### 2.3 Performance Benchmarks

**Problem:** No performance measurements or benchmarks.

**Implementation:**

```python
# tests/benchmarks/benchmark_api_calls.py (NEW FILE)
"""Performance benchmarks for API calls."""

import time
from cli_nlp.command_runner import CommandRunner
from cli_nlp.config_manager import ConfigManager


def benchmark_command_generation():
    """Benchmark command generation performance."""
    config = ConfigManager()
    runner = CommandRunner(config)
    
    queries = [
        "list python files",
        "show disk usage",
        "find large files",
    ]
    
    results = []
    for query in queries:
        start = time.time()
        response = runner.generate_command(query)
        elapsed = time.time() - start
        results.append({
            "query": query,
            "time": elapsed,
            "cached": False,
        })
    
    return results
```

**Tasks:**
- [ ] Create benchmark suite
- [ ] Benchmark API call performance
- [ ] Benchmark cache performance
- [ ] Benchmark command execution
- [ ] Add performance regression tests
- [ ] Document performance characteristics

**Acceptance Criteria:**
- Benchmarks exist for critical operations
- Performance regressions detected
- Performance documented

**Files to Create:**
- `tests/benchmarks/` (NEW DIRECTORY)
- `tests/benchmarks/benchmark_api_calls.py`
- `tests/benchmarks/benchmark_cache.py`
- `tests/benchmarks/benchmark_execution.py`

---

## Phase 3: Developer & Geek Experience (Weeks 5-6)

**Priority:** 🟡 **MEDIUM**  
**Goal:** Improve developer experience, add geek-friendly features, enhance documentation

### 3.1 Developer-Friendly Features

**Tasks:**
- [ ] Add `--verbose` / `-v` flag for debug output
- [ ] Add `--dry-run` flag to preview commands without execution
- [ ] Add `--json` output format for scripting
- [ ] Add `--log-file` option for persistent logs
- [ ] Add `--version` flag showing version info
- [ ] Add `--debug` flag for detailed debugging info

**Implementation:**

```python
# cli_nlp/cli.py additions
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Preview command without executing')
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--version', is_flag=True, help='Show version information')
@click.option('--debug', is_flag=True, help='Enable debug mode')
```

**Acceptance Criteria:**
- All flags work correctly
- JSON output is valid and parseable
- Dry-run shows what would happen
- Verbose mode provides useful debug info

**Files to Modify:**
- `cli_nlp/cli.py`
- `cli_nlp/command_runner.py`
- `cli_nlp/utils.py`

---

### 3.2 Geek-Friendly Features

**Tasks:**
- [ ] Add metrics collection (`qtc metrics`)
- [ ] Add performance stats (`qtc stats`)
- [ ] Add API usage tracking
- [ ] Add cache hit rate display
- [ ] Add command execution time tracking
- [ ] Add provider performance comparison

**Implementation:**

```python
# cli_nlp/metrics.py (NEW FILE)
"""Metrics collection and reporting."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json


@dataclass
class Metrics:
    """Metrics data structure."""
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    execution_time_avg: float = 0.0
    errors: int = 0
    last_updated: datetime | None = None


class MetricsCollector:
    """Collect and report metrics."""
    
    def __init__(self):
        self.metrics_path = self._get_metrics_path()
        self._metrics = self._load_metrics()
    
    def record_query(self, cached: bool, execution_time: float):
        """Record a query execution."""
        self._metrics.total_queries += 1
        if cached:
            self._metrics.cache_hits += 1
        else:
            self._metrics.cache_misses += 1
            self._metrics.api_calls += 1
        # Update average execution time
        # ...
        self._save_metrics()
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        return {
            "total_queries": self._metrics.total_queries,
            "cache_hit_rate": (
                self._metrics.cache_hits / self._metrics.total_queries
                if self._metrics.total_queries > 0
                else 0.0
            ),
            "api_calls": self._metrics.api_calls,
            "avg_execution_time": self._metrics.execution_time_avg,
        }
```

**Acceptance Criteria:**
- Metrics collected accurately
- Stats command shows useful information
- Performance data available

**Files to Create:**
- `cli_nlp/metrics.py` (NEW)
- `cli_nlp/cli.py` (add metrics commands)

---

### 3.3 Documentation Improvements

**Tasks:**
- [ ] Create API documentation
- [ ] Add architecture documentation
- [ ] Create troubleshooting guide
- [ ] Add developer onboarding guide
- [ ] Improve inline code documentation
- [ ] Add code examples to docstrings
- [ ] Create migration guides

**Files to Create:**
- `docs/` (NEW DIRECTORY)
- `docs/API.md` - API reference
- `docs/ARCHITECTURE.md` - Architecture decisions
- `docs/TROUBLESHOOTING.md` - Troubleshooting guide
- `docs/DEVELOPMENT.md` - Developer guide
- `docs/MIGRATION.md` - Migration guides

**Acceptance Criteria:**
- All public APIs documented
- Architecture decisions documented
- Troubleshooting guide covers common issues
- Developer guide enables new contributors

---

## Phase 4: Performance & Optimization (Weeks 7-8)

**Priority:** 🟡 **MEDIUM**  
**Goal:** Optimize performance, add caching improvements, ensure scalability

### 4.1 Performance Optimization

**Tasks:**
- [ ] Profile code to identify bottlenecks
- [ ] Optimize cache operations
- [ ] Optimize file I/O
- [ ] Add connection pooling for API calls
- [ ] Optimize context building
- [ ] Add async support for batch operations

**Acceptance Criteria:**
- Performance improved by 20%+
- Bottlenecks identified and fixed
- Benchmarks show improvement

**Files to Modify:**
- `cli_nlp/cache_manager.py` (optimize)
- `cli_nlp/command_runner.py` (optimize)
- `cli_nlp/context_manager.py` (optimize)

---

### 4.2 Advanced Caching

**Tasks:**
- [ ] Add cache warming
- [ ] Add cache compression
- [ ] Add cache size limits
- [ ] Add cache eviction policies
- [ ] Add cache statistics

**Acceptance Criteria:**
- Cache performance improved
- Memory usage optimized
- Cache hit rate increased

**Files to Modify:**
- `cli_nlp/cache_manager.py`

---

### 4.3 Security Audit

**Tasks:**
- [ ] Security audit of codebase
- [ ] Review API key handling
- [ ] Review command execution safety
- [ ] Add input sanitization
- [ ] Review file permissions
- [ ] Add security documentation

**Acceptance Criteria:**
- No security vulnerabilities
- Security best practices followed
- Security documentation complete

**Files to Create:**
- `docs/SECURITY.md` (enhance existing)
- Security audit report

---

## Implementation Checklist

### Phase 1: Critical Reliability (Weeks 1-2)
- [ ] **Week 1:**
  - [ ] Day 1-2: Implement structured logging
  - [ ] Day 3-4: Add retry logic with exponential backoff
  - [ ] Day 5: Add comprehensive error handling
  
- [ ] **Week 2:**
  - [ ] Day 1-2: Add input validation
  - [ ] Day 3-4: Fix silent failures
  - [ ] Day 5: Testing and bug fixes

### Phase 2: Testing & QA (Weeks 3-4)
- [ ] **Week 3:**
  - [ ] Day 1-3: Increase test coverage to 85%+
  - [ ] Day 4-5: Add integration tests
  
- [ ] **Week 4:**
  - [ ] Day 1-2: Add performance benchmarks
  - [ ] Day 3-5: Test improvements and bug fixes

### Phase 3: Developer Experience (Weeks 5-6)
- [ ] **Week 5:**
  - [ ] Day 1-2: Add developer-friendly flags
  - [ ] Day 3-4: Add geek-friendly features
  - [ ] Day 5: Testing
  
- [ ] **Week 6:**
  - [ ] Day 1-3: Documentation improvements
  - [ ] Day 4-5: Review and polish

### Phase 4: Performance & Optimization (Weeks 7-8)
- [ ] **Week 7:**
  - [ ] Day 1-2: Performance profiling
  - [ ] Day 3-4: Performance optimization
  - [ ] Day 5: Advanced caching
  
- [ ] **Week 8:**
  - [ ] Day 1-2: Security audit
  - [ ] Day 3-4: Final testing
  - [ ] Day 5: Release preparation

---

## Success Criteria

### Must Have (Phase 1)
- ✅ Structured logging implemented
- ✅ Retry logic with exponential backoff
- ✅ Comprehensive error handling
- ✅ Input validation
- ✅ No silent failures

### Should Have (Phase 2)
- ✅ Test coverage ≥ 85%
- ✅ Integration tests added
- ✅ Performance benchmarks

### Nice to Have (Phases 3-4)
- ✅ Developer-friendly features
- ✅ Geek-friendly features
- ✅ Performance optimizations
- ✅ Security audit complete

---

## Risk Mitigation

### Risks:
1. **Scope Creep:** Phases 3-4 may expand beyond timeline
   - **Mitigation:** Strict prioritization, defer non-critical features

2. **Breaking Changes:** Improvements may break existing functionality
   - **Mitigation:** Comprehensive testing, gradual rollout

3. **Performance Regression:** New features may slow down the tool
   - **Mitigation:** Continuous benchmarking, performance tests

4. **API Changes:** LLM provider APIs may change
   - **Mitigation:** Abstract provider interface, version pinning

---

## Metrics & Monitoring

### Key Metrics to Track:
- **Reliability:** Error rate, retry success rate
- **Performance:** Average response time, cache hit rate
- **Quality:** Test coverage, bug count
- **Usage:** Commands generated, API calls made
- **Developer Experience:** Time to contribute, documentation completeness

### Monitoring:
- Structured logs for error tracking
- Metrics collection for performance monitoring
- Test coverage reports
- Performance benchmarks

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize tasks** based on business needs
3. **Create GitHub issues** for each task
4. **Set up project board** for tracking
5. **Begin Phase 1 implementation**

---

## Appendix: Code Examples

### Example: Comprehensive Error Handling

```python
# cli_nlp/command_runner.py (excerpt)
from cli_nlp.exceptions import APIError, ValidationError
from cli_nlp.logger import logger
from cli_nlp.retry import retry_with_backoff, RetryConfig
from cli_nlp.validation import validate_query

def generate_command(self, query: str, ...) -> CommandResponse:
    """Generate command with comprehensive error handling."""
    try:
        # Validate input
        query = validate_query(query)
        
        # Check cache
        if use_cache:
            cached = self.cache_manager.get(query, model=model)
            if cached:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached
        
        # Generate command with retry
        @retry_with_backoff(RetryConfig(max_attempts=3))
        def _call_api():
            return self._generate_with_api(query, model, ...)
        
        response = _call_api()
        
        # Cache result
        if use_cache:
            self.cache_manager.set(query, response, model=model)
        
        return response
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise
    except APIError as e:
        logger.error(f"API error: {e}", exc_info=True)
        raise APIError(
            f"Failed to generate command: {e}. "
            "Please check your API key and network connection."
        )
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        raise QTCError(f"An unexpected error occurred: {e}")
```

---

**Document Status:** Ready for Implementation  
**Last Updated:** 2025-01-27  
**Next Review:** After Phase 1 completion
