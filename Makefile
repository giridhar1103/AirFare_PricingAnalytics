.PHONY: test policy web-install web-dev web-test web-build web-e2e warehouse-spike warehouse elasticity market-share iv-sensitivity forecast export release-verify release-bundle host-preflight check

test:
	python3 -m unittest discover -s tests -v

policy:
	python3 -m unittest tests.test_repository_policy -v

web-install:
	cd web && npm install

web-dev:
	cd web && npm run dev

web-test:
	cd web && npm run test

web-build:
	cd web && npm run build

web-e2e:
	cd web && npm run test:e2e

warehouse-spike:
	duckdb data/processed/farelab_spike.duckdb -init sql/build_2024_spike.sql -c "select count(*) as mart_rows from mart_route_carrier_quarter;"

warehouse:
	python3 -m pipeline.farelab.warehouse --start-year 2017 --end-year 2025 --download

elasticity:
	.venv/bin/python -m pipeline.farelab.elasticity

market-share:
	.venv/bin/python -m pipeline.farelab.market_share

iv-sensitivity:
	.venv/bin/python -m pipeline.farelab.iv_sensitivity

forecast:
	.venv/bin/python -m pipeline.farelab.forecast

export:
	.venv/bin/python -m pipeline.farelab.export_web

release-verify:
	python3 -m pipeline.farelab.release verify

release-bundle: web-build release-verify
	python3 -m pipeline.farelab.release bundle

host-preflight:
	python3 -m pipeline.farelab.release host-preflight

check: test web-test web-build release-verify
