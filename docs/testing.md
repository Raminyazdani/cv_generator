# CV Generator Test Suite Documentation

This document describes the comprehensive test suite for the CV Generator system.

## Test Categories

### 1. Round-Trip Tests (`tests/test_roundtrip.py`)

**Purpose:** Prove that import → export produces identical (or semantically equivalent) JSON.

These tests are the **ultimate proof** that the system works correctly. If round-trip tests pass, we guarantee no data loss.

**Test Classes:**
- `TestRoundTripIndividualFiles` - Tests each CV file independently
- `TestRoundTripBatch` - Tests all files together
- `TestRoundTripMultiLanguage` - Tests multi-language variant handling
- `TestRoundTripEdgeCases` - Tests boundary conditions
- `TestRoundTripWithVerifier` - Tests using the built-in verifier
- `TestRoundTripRegressions` - Tests for specific regression scenarios
- `TestRoundTripPerformance` - Performance benchmarks

### 2. Workflow Tests (`tests/test_workflows.py`)

**Purpose:** Simulate complete user actions through the system.

**Test Classes:**
- `TestImportWorkflow` - First import, add variant, update existing
- `TestExportWorkflow` - Single export, batch export, list available
- `TestErrorWorkflow` - Invalid JSON, missing config, collision handling
- `TestBatchWorkflow` - Batch import and export operations
- `TestDryRunWorkflow` - Dry-run mode validation

### 3. Section Tests (`tests/test_sections.py`)

**Purpose:** Verify each CV section handles correctly.

**Test Classes:**
- `TestBasicsSection` - Phone, location, pictures, labels
- `TestSkillsSection` - 3-level nesting, order preservation, tags
- `TestCertificationsSection` - Issuer grouping, nested certifications
- `TestPublicationsSection` - Authors, identifiers
- `TestLanguagesSection` - Proficiency, certifications
- `TestEducationSection` - End dates, tags
- `TestExperiencesSection` - Duration text
- `TestReferencesSection` - Multiple emails

### 4. Edge Case Tests (`tests/test_edge_cases.py`)

**Purpose:** Test boundary conditions and unusual inputs.

**Test Classes:**
- `TestNullHandling` - Explicit null values
- `TestEmptyHandling` - Empty arrays, strings, objects
- `TestTypePreservation` - Integers, floats, booleans
- `TestUnicodeHandling` - Persian, German, mixed scripts
- `TestLargeContent` - Long text, many items, deep structures
- `TestSpecialCharacters` - HTML entities, LaTeX content

### 5. Regression Tests (`tests/test_regression.py`)

**Purpose:** Prevent previously fixed bugs from recurring.

**Test Classes:**
- `TestKnownIssues` - Pictures capitalization, phone nesting, order preservation
- `TestMultiLanguageRegression` - Variant linking, i18n fields
- `TestTagSystemRegression` - Tag case normalization
- `TestImportExportCycleRegression` - Re-import, present end dates

## Running Tests

### All Tests
```bash
python -m pytest tests/ -v
```

### Round-Trip Only
```bash
python -m pytest tests/test_roundtrip.py -v
```

### With Coverage
```bash
python -m pytest tests/ --cov=src/cv_generator --cov-report=html
```

### Specific Test Class
```bash
python -m pytest tests/test_roundtrip.py::TestRoundTripIndividualFiles -v
```

## Self-Audit Tools

The `cv_generator.audit_cli` module provides command-line tools for manual verification.

### Verify Round-Trip
```bash
python -m cv_generator.audit_cli roundtrip-verify data/cvs/
```

### Verify Schema
```bash
python -m cv_generator.audit_cli schema-verify --db data/db/cv.db
```

### Verify Sync Status
```bash
python -m cv_generator.audit_cli sync-verify --db data/db/cv.db
```

### Full Audit
```bash
python -m cv_generator.audit_cli full-audit --output report.json
```

## CI/CD Integration

Tests run automatically on:
- Every push to `main`/`master`
- Every pull request

The CI workflow includes:
1. **Install Smoke Test** - Package installation on multiple OS/Python versions
2. **Lint** - Code style checks with ruff
3. **Documentation** - MkDocs build verification
4. **Test** - Full test suite with coverage
5. **Round-Trip Verification** - Dedicated round-trip, workflow, and regression tests

## Test Coverage Goals

- **Round-Trip Coverage**: All CV files in `data/cvs/` must pass round-trip
- **Section Coverage**: All CV sections must have dedicated tests
- **Edge Case Coverage**: All boundary conditions must be tested
- **Regression Coverage**: All known issues must have tests

## Test Data

### Primary Test Files
- `data/cvs/ramin.json` - English CV (config.ID: ramin_yazdani)
- `data/cvs/ramin_de.json` - German CV (config.ID: ramin_yazdani)
- `data/cvs/ramin_fa.json` - Persian CV (config.ID: ramin_yazdani)
- `data/cvs/mahsa.json` - Second person for multi-person tests

### Test Fixtures
Located in `tests/fixtures/`:
- `valid/` - Valid CV fixtures
- `invalid/` - Invalid CV fixtures for error testing
- `multilang/` - Multi-language fixtures
- `ramin/` - Ramin-specific fixtures

## Verification Approach

### Round-Trip Fidelity
The `ExportVerifier` class compares exported data against original JSON:
- Structural comparison (same keys, same nesting)
- Value comparison with type awareness
- Order tracking for arrays
- Optional leniency for extra null keys and key ordering

### Leniency Options
The verifier supports these leniency modes:
- `ignore_order=True` - JSON objects are unordered by spec
- `ignore_whitespace=True` - Ignore string whitespace differences
- `ignore_type_key_order=True` - Treat type_key as sets
- `ignore_extra_null_keys=True` - Extra null values don't lose information

## Writing New Tests

When adding new tests:

1. **Use appropriate fixtures** - Use `fresh_db` for isolated tests
2. **Test both import and export** - Verify the full cycle
3. **Check database state** - Verify correct records are created
4. **Test edge cases** - Don't just test happy paths
5. **Add regression tests** - When fixing bugs, add tests to prevent recurrence

### Example Test
```python
def test_feature_works(self, fresh_db, tmp_path):
    """Descriptive test name explaining what is tested."""
    # 1. Create test data
    json_path = tmp_path / "test.json"
    cv_data = {...}
    with open(json_path, "w") as f:
        json.dump(cv_data, f)
    
    # 2. Import
    importer = CVImporter(fresh_db)
    result = importer.import_file(json_path)
    assert result.success
    
    # 3. Export
    exporter = CVExporter(fresh_db)
    exported = exporter.export("test_id", "en")
    
    # 4. Verify
    assert exported["field"] == cv_data["field"]
```
