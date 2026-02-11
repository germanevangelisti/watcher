# Watcher Agent - Test Suite

Comprehensive test suite for the Watcher Agent 4-layer architecture (PDS, DIA, KAA, OEx).

## 📋 Overview

This test suite validates:
- **PDS Layer**: Portal Data Scrapers (Provincial, Municipal, National)
- **DIA Layer**: Data Integration Adapters & Embeddings
- **KAA Layer**: Knowledge AI Agents (KBA, RAGA, Document Intelligence)
- **OEx Layer**: Output Execution (Alerts, Reports, API Gateway)
- **Integration**: Cross-layer flows
- **E2E**: Complete pipeline workflows

## 📁 Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests per layer
│   ├── test_pds_scrapers.py
│   ├── test_dia_adapters.py
│   ├── test_embedding_service.py
│   ├── test_kaa_agents.py
│   └── test_oex_outputs.py
├── integration/             # Integration tests between layers
│   ├── test_pds_dia_flow.py
│   ├── test_dia_kaa_flow.py
│   ├── test_kaa_oex_flow.py
│   └── test_api_gateway.py
├── e2e/                     # End-to-end pipeline tests
│   └── test_full_pipeline.py
└── fixtures/                # Test data and samples
    └── sample_documents/
```

## 🚀 Quick Start

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/

# By layer marker
pytest -m pds tests/      # PDS layer tests
pytest -m dia tests/      # DIA layer tests
pytest -m kaa tests/      # KAA layer tests
pytest -m oex tests/      # OEx layer tests
```

### Run with Coverage

```bash
pytest --cov=watcher-monolith/backend/app --cov=agents --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```

## 🎯 Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.pds` - PDS layer tests
- `@pytest.mark.dia` - DIA layer tests
- `@pytest.mark.kaa` - KAA layer tests
- `@pytest.mark.oex` - OEx layer tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow running tests (>1s)

### Filter by Markers

```bash
# Run only fast tests (exclude slow)
pytest -m "not slow" tests/

# Run only integration tests
pytest -m integration tests/

# Run PDS and DIA tests
pytest -m "pds or dia" tests/
```

## 📊 Test Statistics

| Category | File | Tests | Priority |
|----------|------|-------|----------|
| **Unit - PDS** | `test_pds_scrapers.py` | 15 | High |
| **Unit - DIA** | `test_dia_adapters.py` | 14 | High |
| **Unit - DIA** | `test_embedding_service.py` | 15 | High |
| **Unit - KAA** | `test_kaa_agents.py` | 13 | Medium |
| **Unit - OEx** | `test_oex_outputs.py` | 17 | Medium |
| **Integration** | 4 files | 10 | High |
| **E2E** | `test_full_pipeline.py` | 6 | High |
| **TOTAL** | 11 files | **~90 tests** | |

## 🧪 Test Fixtures

Common fixtures available in `conftest.py`:

### Database
- `mock_db_session` - Mock database session
- `mock_async_session` - Mock async session

### Scrapers
- `sample_scraper_config` - Scraper configuration
- `sample_scraper_result` - Sample scraper result
- `mock_http_client` - Mock HTTP client for testing downloads

### Adapters
- `sample_bulletin_data` - Raw bulletin data
- `sample_document_schema` - Normalized document schema

### Embeddings
- `mock_embedding_service` - Mock embedding service
- `sample_text_for_chunking` - Text for chunking tests

### Agents
- `sample_agent_task` - Agent task factory
- `mock_kba_agent` - Mock Knowledge Base Agent
- `mock_raga_agent` - Mock RAG Agent

### Outputs
- `sample_alert_data` - Alert data
- `sample_report_data` - Report data

### File System
- `temp_output_dir` - Temporary directory for tests
- `sample_pdf_path` - Sample PDF file

## 🔧 Configuration

### pytest.ini

Key configuration:
- Async mode: `auto`
- Coverage reports: HTML, XML, Terminal
- Test discovery: `tests/` directory
- Output: Verbose with short tracebacks

### Requirements

See `requirements-test.txt` for all testing dependencies:
- pytest >= 7.4.0
- pytest-asyncio >= 0.21.0
- pytest-cov >= 4.1.0
- pytest-mock >= 3.11.0
- httpx >= 0.24.0

## 📈 Coverage Goals

| Layer | Target Coverage |
|-------|----------------|
| PDS   | ≥ 80% |
| DIA   | ≥ 80% |
| KAA   | ≥ 70% |
| OEx   | ≥ 80% |
| **Overall** | **≥ 75%** |

## 🐛 Debugging Tests

### Run Single Test

```bash
pytest tests/unit/test_pds_scrapers.py::test_provincial_scraper_init -v
```

### Enable Debug Output

```bash
pytest tests/ -v -s  # -s shows print statements
```

### Run with PDB on Failure

```bash
pytest tests/ --pdb
```

### Run Last Failed Tests

```bash
pytest --lf tests/
```

## ⚡ Performance

### Expected Run Times

- Unit tests: ~30-60 seconds
- Integration tests: ~20-30 seconds
- E2E tests: ~30-45 seconds
- **Total**: < 2 minutes

### Running Fast Tests Only

```bash
pytest -m "not slow" tests/
```

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Tests
  run: |
    pip install -r requirements-test.txt
    pytest tests/ --cov --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## 📝 Writing New Tests

### Test Naming Convention

- `test_<component>_<action>()` for unit tests
- `test_<flow>_<scenario>()` for integration tests
- `test_<pipeline>_e2e()` for end-to-end tests

### Example Unit Test

```python
@pytest.mark.pds
def test_scraper_initialization():
    """Test scraper initializes correctly."""
    scraper = create_provincial_scraper()
    assert scraper is not None
    assert scraper.config.scraper_type == ScraperType.PROVINCIAL
```

### Example Integration Test

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_scraper_to_adapter_flow():
    """Test complete PDS -> DIA flow."""
    # Download
    scraper_result = await scraper.download_single(...)
    
    # Adapt
    adapter_result = await adapter.adapt_document(...)
    
    # Verify
    assert adapter_result.success is True
```

## 🆘 Troubleshooting

### ChromaDB Not Available

Some embedding tests require ChromaDB. If not installed:
```bash
pip install chromadb
```

Or tests will be automatically skipped with `pytest.skip()`.

### Async Tests Failing

Ensure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

### Import Errors

Tests add backend and agents to Python path automatically. If issues persist:
```bash
export PYTHONPATH="${PYTHONPATH}:./watcher-monolith/backend:./agents"
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

## 🤝 Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass: `pytest tests/`
3. Check coverage: `pytest --cov`
4. Add appropriate markers (`@pytest.mark.pds`, etc.)
5. Update this README if adding new test categories

---

**Test Suite Version**: 1.0.0  
**Last Updated**: 2026-02-04  
**Maintained By**: Watcher Agent Development Team
