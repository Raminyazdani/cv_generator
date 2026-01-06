# Final Audit Report

> Generated: 2026-01-06T14:28:14.265412
> Audit Duration: 0:00:53.251536

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 7 |
| 🟠 HIGH | 1 |
| 🟡 MEDIUM | 2 |
| 🟢 LOW | 15 |
| **TOTAL** | **25** |

---

## Problems by Category


### Code Quality (11 problems)


---

#### [PROB-0006] 44 files with missing type hints

**Severity**: 🟢 LOW
**Category**: Code Quality > Type Hints

**Description**:
Some public functions lack return type annotations

**Reproduction Steps**:
   1. Check public functions for -> annotations

**Expected Behavior**:
All public functions have type hints

**Actual Behavior**:
44 files have functions without hints

**Affected Files**: N/A


---

#### [PROB-0007] File too long: cli.py (3127 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in cli.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
3127 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


---

#### [PROB-0008] File too long: importer_v2.py (1265 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in importer_v2.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
1265 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


---

#### [PROB-0009] File too long: crud.py (1338 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in crud.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
1338 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


---

#### [PROB-0010] File too long: ensure.py (1105 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in ensure.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
1105 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


---

#### [PROB-0011] File too long: web.py (2576 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in web.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
2576 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


---

#### [PROB-0012] File too long: exporter_v2.py (1217 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in exporter_v2.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
1217 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


---

#### [PROB-0013] File too long: variant_manager.py (1218 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in variant_manager.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
1218 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


---

#### [PROB-0014] File too long: person.py (1006 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in person.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
1006 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


---

#### [PROB-0015] File too long: db.py (2076 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in db.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
2076 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


---

#### [PROB-0016] File too long: migrate_to_v2.py (1363 lines)

**Severity**: 🟢 LOW
**Category**: Code Quality > File Length

**Description**:
Consider splitting into smaller modules

**Reproduction Steps**:
   1. Count lines in migrate_to_v2.py

**Expected Behavior**:
Files under 1000 lines

**Actual Behavior**:
1363 lines

**Affected Files**: N/A

**Suggested Fix**:
Consider refactoring into smaller modules


### Export Engine (1 problems)


---

#### [PROB-0001] No export templates found

**Severity**: 🟢 LOW
**Category**: Export Engine > Templates

**Description**:
Export templates directory is empty

**Reproduction Steps**:
   1. List files in export_templates/

**Expected Behavior**:
Template files exist

**Actual Behavior**:
No templates found

**Affected Files**: N/A


### File Structure (1 problems)


---

#### [PROB-0017] 134 temp/cache files in repo

**Severity**: 🟢 LOW
**Category**: File Structure > Temp Files

**Description**:
Temporary or cache files found in the repository

**Reproduction Steps**:
   1. Search for *.pyc, __pycache__, etc.

**Expected Behavior**:
No temp files in repository

**Actual Behavior**:
Found: __pycache__/generate_cv.cpython-312.pyc, scripts/__pycache__/find_duplicates.cpython-312.pyc, scripts/__pycache__/analyze_function_usage.cpython-312.pyc, scripts/__pycache__/code_audit.cpython-312.pyc, scripts/__pycache__/find_unused_imports.cpython-312.pyc...

**Affected Files**: N/A

**Suggested Fix**:
Add these patterns to .gitignore


### Performance (1 problems)


---

#### [PROB-0025] Potential N+1 query patterns in db.py

**Severity**: 🟢 LOW
**Category**: Performance > N+1 Queries

**Description**:
Found 18 loops with database queries nearby

**Reproduction Steps**:
   1. Review db.py for loops containing cursor.execute
   2. Consider batch queries where applicable

**Expected Behavior**:
Batch queries for better performance

**Actual Behavior**:
18 potential N+1 patterns

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/db.py

**Suggested Fix**:
Consider using batch queries or JOINs


### Security (7 problems)


---

#### [PROB-0018] Potential SQL injection in schema_validator.py

**Severity**: 🔴 CRITICAL
**Category**: Security > SQL Injection

**Description**:
SQL query uses string formatting instead of parameters

**Reproduction Steps**:
   1. Check SQL queries in schema_validator.py

**Expected Behavior**:
Parameterized queries (cursor.execute(sql, params))

**Actual Behavior**:
String formatting detected in SQL

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/schema_validator.py

**Suggested Fix**:
Use parameterized queries


---

#### [PROB-0019] Potential SQL injection in sync_engine.py

**Severity**: 🔴 CRITICAL
**Category**: Security > SQL Injection

**Description**:
SQL query uses string formatting instead of parameters

**Reproduction Steps**:
   1. Check SQL queries in sync_engine.py

**Expected Behavior**:
Parameterized queries (cursor.execute(sql, params))

**Actual Behavior**:
String formatting detected in SQL

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/sync_engine.py

**Suggested Fix**:
Use parameterized queries


---

#### [PROB-0020] Potential SQL injection in importer_v2.py

**Severity**: 🔴 CRITICAL
**Category**: Security > SQL Injection

**Description**:
SQL query uses string formatting instead of parameters

**Reproduction Steps**:
   1. Check SQL queries in importer_v2.py

**Expected Behavior**:
Parameterized queries (cursor.execute(sql, params))

**Actual Behavior**:
String formatting detected in SQL

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/importer_v2.py

**Suggested Fix**:
Use parameterized queries


---

#### [PROB-0021] Potential SQL injection in variant_manager.py

**Severity**: 🔴 CRITICAL
**Category**: Security > SQL Injection

**Description**:
SQL query uses string formatting instead of parameters

**Reproduction Steps**:
   1. Check SQL queries in variant_manager.py

**Expected Behavior**:
Parameterized queries (cursor.execute(sql, params))

**Actual Behavior**:
String formatting detected in SQL

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/variant_manager.py

**Suggested Fix**:
Use parameterized queries


---

#### [PROB-0022] Potential SQL injection in person.py

**Severity**: 🔴 CRITICAL
**Category**: Security > SQL Injection

**Description**:
SQL query uses string formatting instead of parameters

**Reproduction Steps**:
   1. Check SQL queries in person.py

**Expected Behavior**:
Parameterized queries (cursor.execute(sql, params))

**Actual Behavior**:
String formatting detected in SQL

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/person.py

**Suggested Fix**:
Use parameterized queries


---

#### [PROB-0023] Potential SQL injection in db.py

**Severity**: 🔴 CRITICAL
**Category**: Security > SQL Injection

**Description**:
SQL query uses string formatting instead of parameters

**Reproduction Steps**:
   1. Check SQL queries in db.py

**Expected Behavior**:
Parameterized queries (cursor.execute(sql, params))

**Actual Behavior**:
String formatting detected in SQL

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/db.py

**Suggested Fix**:
Use parameterized queries


---

#### [PROB-0024] Potential SQL injection in migrate_to_v2.py

**Severity**: 🔴 CRITICAL
**Category**: Security > SQL Injection

**Description**:
SQL query uses string formatting instead of parameters

**Reproduction Steps**:
   1. Check SQL queries in migrate_to_v2.py

**Expected Behavior**:
Parameterized queries (cursor.execute(sql, params))

**Actual Behavior**:
String formatting detected in SQL

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/migrations/migrate_to_v2.py

**Suggested Fix**:
Use parameterized queries


### Sync Engine (1 problems)


---

#### [PROB-0003] Missing function: get_sync_status

**Severity**: 🟡 MEDIUM
**Category**: Sync Engine > Missing Function

**Description**:
Function 'get_sync_status' not found in sync_engine.py

**Reproduction Steps**:
   1. Search for 'def get_sync_status' in sync_engine.py

**Expected Behavior**:
Function 'get_sync_status' is defined

**Actual Behavior**:
Function not found

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/sync_engine.py


### Test Suite (1 problems)


---

#### [PROB-0005] 4 test(s) failed

**Severity**: 🟠 HIGH
**Category**: Test Suite > Test Failures

**Description**:
Tests are failing in the test suite

**Reproduction Steps**:
   1. Run: pytest tests/ -v
   2. Check failed tests

**Expected Behavior**:
All tests pass

**Actual Behavior**:
Failed tests: tests/test_path_config.py::TestPathConfigAllPaths::test_templates_dir_error, tests/test_path_config.py::TestConfigFileParsing::test_config_file_with_expanduser, , 

**Affected Files**: N/A

**Error Message**:
```
tests/test_roundtrip.py:794
  /home/runner/work/cv_generator/cv_generator/tests/test_roundtrip.py:794: PytestUnknownMarkWarning: Unknown pytest.mark.slow - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.slow

tests/test_doctor.py::TestRunChecks::test_run_checks_includes_all_categories
tests/test_doctor.py::TestRunChecks::test_run_checks_includes_all_categories
tests/test_generator.py::TestGenerateCV::test_generate_cv_dry_run
tests/test_generator.py::TestGenerateCV::test_generate_cv_dry_run
tests/test_registry.py::TestHooksInGenerator::test_hooks_fire_during_generate_cv
tests/test_registry.py::TestHooksInGenerator::test_hooks_fire_during_generate_cv
  /usr/lib/python3/dist-packages/jinja2/lexer.py:655: DeprecationWarning: invalid escape sequence '\e'
    .decode("unicode-escape")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_path_config.py::TestPathConfigAllPaths::test_templates_dir_error - Failed: DID NOT RAISE <class 'FileNotFoundError'>
FAILED tests/test_path_config.py::TestConfigFileParsing::test_config_file_with_expanduser - AssertionError: assert PosixPath('/home/runner/my_cvs') == PosixPath('/tmp/pytest-of-runner/pytest-5/test_config_file_with_expandus0/home/my_cvs')
 +  where PosixPath('/home/runner/my_cvs') = PathConfig(\n  cvs_dir=/home/runner/my_cvs,\n  pics_dir=/tmp/pytest-of-runner/pytest-5/test_config_file_with_expandus0/home/.cvgen/pics,\n  db_path=/tmp/pytest-of-runner/pytest-5/test_config_file_with_expandus0/home/.cvgen/db/cv.db,\n  templates_dir=/home/runner/work/cv_generator/cv_generator/templates,\n  output_dir=/home/runner/work/cv_generator/cv_generator/output,\n  assets_dir=/home/runner/work/cv_generator/cv_generator/assets\n).cvs_dir
================= 2 failed, 1283 passed, 7 warnings in 51.67s ==================

```


### Variant Management (1 problems)


---

#### [PROB-0004] Missing function: list_variants

**Severity**: 🟡 MEDIUM
**Category**: Variant Management > Missing Function

**Description**:
Function 'list_variants' not found in variant_manager.py

**Reproduction Steps**:
   1. Search for 'def list_variants' in variant_manager.py

**Expected Behavior**:
Function 'list_variants' is defined

**Actual Behavior**:
Function not found

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/variant_manager.py


### Web UI (1 problems)


---

#### [PROB-0002] No error handlers found

**Severity**: 🟢 LOW
**Category**: Web UI > Error Handling

**Description**:
No @errorhandler decorators in web.py

**Reproduction Steps**:
   1. Search for 'errorhandler' in web.py

**Expected Behavior**:
Error handlers for 404, 500, etc.

**Actual Behavior**:
No error handlers found

**Affected Files**: /home/runner/work/cv_generator/cv_generator/src/cv_generator/web.py

**Suggested Fix**:
Add @app.errorhandler decorators


---

## Problem Index

| ID | Severity | Category | Title |
|----|----------|----------|-------|
| PROB-0001 | 🟢 LOW | Export Engine | No export templates found |
| PROB-0002 | 🟢 LOW | Web UI | No error handlers found |
| PROB-0003 | 🟡 MEDIUM | Sync Engine | Missing function: get_sync_status |
| PROB-0004 | 🟡 MEDIUM | Variant Management | Missing function: list_variants |
| PROB-0005 | 🟠 HIGH | Test Suite | 4 test(s) failed |
| PROB-0006 | 🟢 LOW | Code Quality | 44 files with missing type hints |
| PROB-0007 | 🟢 LOW | Code Quality | File too long: cli.py (3127 lines) |
| PROB-0008 | 🟢 LOW | Code Quality | File too long: importer_v2.py (1265 lines) |
| PROB-0009 | 🟢 LOW | Code Quality | File too long: crud.py (1338 lines) |
| PROB-0010 | 🟢 LOW | Code Quality | File too long: ensure.py (1105 lines) |
| PROB-0011 | 🟢 LOW | Code Quality | File too long: web.py (2576 lines) |
| PROB-0012 | 🟢 LOW | Code Quality | File too long: exporter_v2.py (1217 lines) |
| PROB-0013 | 🟢 LOW | Code Quality | File too long: variant_manager.py (1218 lines) |
| PROB-0014 | 🟢 LOW | Code Quality | File too long: person.py (1006 lines) |
| PROB-0015 | 🟢 LOW | Code Quality | File too long: db.py (2076 lines) |
| PROB-0016 | 🟢 LOW | Code Quality | File too long: migrate_to_v2.py (1363 lines) |
| PROB-0017 | 🟢 LOW | File Structure | 134 temp/cache files in repo |
| PROB-0018 | 🔴 CRITICAL | Security | Potential SQL injection in schema_validator.py |
| PROB-0019 | 🔴 CRITICAL | Security | Potential SQL injection in sync_engine.py |
| PROB-0020 | 🔴 CRITICAL | Security | Potential SQL injection in importer_v2.py |
| PROB-0021 | 🔴 CRITICAL | Security | Potential SQL injection in variant_manager.py |
| PROB-0022 | 🔴 CRITICAL | Security | Potential SQL injection in person.py |
| PROB-0023 | 🔴 CRITICAL | Security | Potential SQL injection in db.py |
| PROB-0024 | 🔴 CRITICAL | Security | Potential SQL injection in migrate_to_v2.py |
| PROB-0025 | 🟢 LOW | Performance | Potential N+1 query patterns in db.py |
