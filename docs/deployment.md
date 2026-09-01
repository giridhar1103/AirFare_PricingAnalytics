# Deployment contract

## Targets

- Web application: `https://giriworks.com/farelab/`
- Decision-brief API: `https://api.giriworks.com/farelab-ai/`

The analytical application is a static build. Heavy data processing happens offline and the browser receives a compact, versioned JSON artifact. The optional AI decision brief runs in one isolated FastAPI service on loopback port 8010.

## Isolation rules

- The Vite base path remains `/farelab/`.
- Port 8010 is dedicated to FareLab and binds only to `127.0.0.1`.
- The existing services on ports 8000, 8001, 8002, and 4200 are not changed or restarted.
- Nginx exposes only the `/farelab-ai/` location and applies existing per-IP rate limits.
- The Anthropic key is read from a server-side environment file and never enters the web build.
- The API accepts a published route identifier and bounded scenario fields. It does not accept free-form user prompts.

## Static build

```bash
cd web
npm ci
npm run test
npm run build
```

The output is `web/dist`. The build script creates a physical `index.html` for each application route so direct refreshes work under the nested base path without rewriting data or asset requests.

## Data promotion

```bash
make warehouse
make elasticity market-share iv-sensitivity forecast
make export
make check
```

Final verification rejects fixture mode, missing source vintages, rejected elasticity fields in route records, invalid intervals, missing action coverage, and an overview payload above 500 KB.

## API installation

```bash
python3 -m venv .venv-api
.venv-api/bin/pip install 'anthropic>=0.97,<1' 'fastapi>=0.116,<1' \
  'pydantic>=2.11,<3' 'uvicorn[standard]>=0.35,<1'
sudo install -m 0600 /path/to/farelab-ai.env /etc/farelab-ai.env
sudo cp deploy/farelab-ai.service /etc/systemd/system/farelab-ai.service
sudo systemctl daemon-reload
sudo systemctl enable --now farelab-ai.service
```

The service runs with a read-only view of the host filesystem, a private temporary directory, no new privileges, and restricted address families. Validate it locally before changing Nginx:

```bash
curl http://127.0.0.1:8010/health
```

Insert `deploy/farelab-ai.nginx.conf` as a location in the existing `api.giriworks.com` server block. Then run `nginx -t` before reloading Nginx. Verify the public health endpoint and CORS response from `https://giriworks.com`.

## AI evaluation

Run deterministic cases before deployment:

```bash
.venv-api/bin/python evals/run_ai_evals.py
```

After the public endpoint is healthy, run the live evaluation:

```bash
.venv-api/bin/python evals/run_ai_evals.py \
  --endpoint https://api.giriworks.com/farelab-ai \
  --output evals/results/latest.json
```

The release requires full policy, grounding, and prohibited-claim compliance. Live p95 latency must remain below eight seconds for the release case set.

## Verified release bundle

Build a checksummed deployment archive without touching the portfolio repository:

```bash
make release-bundle
```

This creates ignored local output at `artifacts/farelab-static.tar.gz`. The archive contains a single `farelab/` directory plus `release-manifest.json`, which records every file size and SHA-256 checksum.

## Portfolio integration

Copy the verified FareLab build into:

```text
/root/MyWebsiteHostGit/client/public/farelab/
```

The host build copies `client/public` into `dist-pages`. The generated physical route files support paths such as `/farelab/models` and `/farelab/scenario` while the existing portfolio fallback remains unchanged.

Before publication:

1. Validate the release manifest in a temporary directory.
2. Replace only the files under `client/public/farelab`.
3. Run `npm run build:pages` in `MyWebsiteHostGit`.
4. Verify FareLab data, assets, and every physical route entry.
5. Smoke test the portfolio home, credit-risk, GitHub analytics, job scanner, and FareLab routes.
6. Publish through the existing Cloudflare Pages workflow.

## Rollback

The static rollback restores only the prior `client/public/farelab` files. The API rollback removes the `/farelab-ai/` Nginx location after a successful `nginx -t`, stops and disables `farelab-ai.service`, and leaves all pre-existing services untouched.
