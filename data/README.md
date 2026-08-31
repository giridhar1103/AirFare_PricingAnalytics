# Data zones

- `fixtures`: deterministic local data used only to develop and test the interface
- `raw`: immutable source downloads and manifests
- `interim`: standardized source tables
- `processed`: governed analytical marts and browser exports

Raw and processed DOT data is not committed to Git. Every production artifact must include source period, checksum lineage, build timestamp, schema version, and `data_mode=dot_observed`.

The current interface fixture is deliberately labeled `development_fixture`. It exercises the full workflow but its values must not be cited as real market findings.
