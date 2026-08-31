# Deployment contract

## Target

FareLab is designed for `https://giriworks.com/farelab`.

The first production release is a static build. All heavy data processing happens offline and the browser receives compact, versioned JSON artifacts. This avoids introducing a new long-running process or consuming a port used by an existing application.

## Isolation rules

- FareLab develops in `/root/farelab-us-airline-pricing` only.
- No existing repository is modified during initial development.
- No system service, reverse-proxy file, firewall rule, or active port is changed without a separate deployment review.
- The Vite base path is `/farelab/`.
- The production build is tested locally before files are integrated into the portfolio host.

## Build

```bash
cd web
npm ci
npm run test
npm run build
```

The output is `web/dist`. Asset URLs must begin with `/farelab/` and client navigation must support direct refreshes through the host fallback configuration.

## Data promotion

Production data artifacts are built separately:

```bash
make warehouse
make elasticity market-share iv-sensitivity forecast
make export
make check
```

The final verification rejects fixture mode, missing source vintages, rejected elasticity fields in route records, invalid intervals, missing action coverage, and an overview payload above 500 KB.

## Verified release bundle

Build a checksummed deployment archive without touching the portfolio repository:

```bash
make release-bundle
```

This creates ignored local output at `artifacts/farelab-static.tar.gz`. The archive contains a single `farelab/` directory plus `release-manifest.json`, which records every file size and SHA-256 checksum. The current verified release contains 14 web files totaling about 1.06 MB before compression.

## Integration options

### Preferred initial integration

Copy the verified FareLab build into the portfolio site's public build under `farelab/`, then add only the minimal route fallback required by the existing static host. This keeps the analytical code in its own repository and avoids a new process.

The current portfolio uses Cloudflare Pages and copies `client/public` into `dist-pages`. The release therefore belongs at:

```text
/root/MyWebsiteHost/client/public/farelab/
```

The route rules must remain ordered from specific to general:

```text
/farelab/*    /farelab/index.html   200
/*            /index.html           200
```

The first rule supports direct refreshes such as `/farelab/models`. The second preserves the existing portfolio fallback. Static FareLab asset and data files remain available at their exact paths.

Before any live publication:

1. Retain a copy of any existing `client/public/farelab` directory.
2. Extract the verified bundle into a temporary directory and validate its manifest.
3. Replace only `client/public/farelab`.
4. Insert the FareLab redirect before the existing global fallback.
5. Run `npm run build:pages` in `MyWebsiteHost`.
6. Verify `dist-pages/farelab/index.html`, the referenced JavaScript and CSS, and `dist-pages/farelab/data/farelab-overview.json`.
7. Smoke test the existing home, credit-risk, GitHub analytics, and job-scanner paths from the same build.
8. Publish through the portfolio's existing Cloudflare Pages workflow.

No Node service, Docker container, firewall rule, reverse-proxy process, or new port is required.

The read-only host inspection is available as:

```bash
make host-preflight
```

It validates the Cloudflare Pages build command, public directory, existing fallback, target state, and whether any service or port change would be necessary. It never writes to `MyWebsiteHost`.

### Future API integration

An API is justified only if saved scenarios, authenticated analyst notes, scheduled model refreshes, or queries beyond precomputed artifacts become requirements. If added, it receives a dedicated service name, health check, resource limit, and deployment approval. It must not reuse an existing application port.

## Rollback

Deployment should be atomic and retain the prior static artifact. A rollback restores the previous `farelab/` artifact only. It does not touch the root portfolio build or other application routes.
