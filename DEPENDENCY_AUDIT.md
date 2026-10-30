# Dependency audit — public package metadata

Audit date:2026-10-30. Tool:pip-audit2.10.1, explicit PyPI index, strict dependency collection, binary-only resolver inputs. The family union resolved 27 packages on Python3.12.11/Windows; the actual report contained zero known vulnerabilities and no skipped packages. One family audit covers related variants; this is not seven independent project installs.

Actual direct dependency names for this variant: Flask, Flask-SQLAlchemy, Flask-WTF, SQLAlchemy. Import aliases were mapped to their distribution names (for example PIL→Pillow, dotenv→python-dotenv). Local script modules were excluded from PyPI requirements. Conditional/dynamic imports and platform-specific dependency markers may need a separate resolver/audit on another environment.

For the audited Python3.12/Windows baseline, use the attached constraints file as constraints:

```powershell
python -m pip install -c constraints-audited-py312-windows.txt -r requirements.txt
```

The constraints contain the family union, so some entries are unused by this variant; constraints do not install those packages. Direct manifests are kept minimal. Unconstrained installation, another Python/platform, or future dependency changes can resolve different versions and must be audited separately. The snapshot pins package versions, not wheel hashes, native/vendored code or system tools.

No old pinned vulnerability was found in this audit; no security-patch or application-compatibility claim is invented. Missing direct dependency declarations were corrected. No project, real CV input, database, browser, send/login or production API was executed. A clean metadata audit is not a full runtime health result. LaTeX, fonts, browsers/drivers and other system tools are outside this Python advisory audit.

The cvgen union also includes the existing pyproject build/dev declarations. Setuptools and wheel were absent from the resolver output; their actual latest public PyPI versions were audited separately as exact direct metadata-only requirements (zero known findings). This does not establish their full isolated-build dependency closure. The CVgen-C build-tool snapshot is recorded separately; normal runtime constraints alone do not force isolated build-tool versions.
