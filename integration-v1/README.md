# PT HONGLU BAJA INDONESIA — FABRIKASI Integration V1.1

This folder adds Cloudflare Workers as the public gateway in front of the Google Apps Script integration engine.

## Architecture

`Asana / ClickUp / monday.com / Airtable -> Cloudflare Worker -> Google Apps Script -> Google Sheets`

`DATABASE MASTER` remains read-only. Cloudflare is the public gateway; Google Apps Script remains the orchestrator, queue processor, retry engine and audit layer.

## Environments

| Environment | Worker name | Purpose |
|---|---|---|
| DEV | `fabrikasi-integration-v1-dev` | initial pilot and smoke test |
| TEST | `fabrikasi-integration-v1-test` | promotion validation |
| PROD | `fabrikasi-integration-v1-prod` | production gateway |

Production contains a 5-minute cron definition, but the scheduled queue call remains disabled because `ENABLE_SCHEDULED_SYNC=false`. It must remain disabled until the 10-record pilot passes.

## Worker endpoints

- `GET /health` — Worker health without exposing secrets.
- `GET /origin-health` — Apps Script origin health; requires `Authorization: Bearer <CONTROL_TOKEN>`.
- `POST /control/process-queue` — process Apps Script sync queue; requires control bearer token.
- `POST /hook/asana`
- `POST /hook/clickup`
- `POST /hook/monday`
- `POST /hook/airtable`

The Worker handles the Asana `X-Hook-Secret` handshake and monday.com JSON challenge at the edge.

## Required GitHub Environments and Secrets

Create `integration-dev`, `integration-test`, and `integration-production` GitHub environments. Each environment requires:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `GAS_ORIGIN_URL`
- `GATEWAY_SHARED_SECRET`
- `CONTROL_TOKEN`

Secrets are synchronized into the target Worker before every deployment. No secret is committed to the repository.

## Apps Script

The Apps Script V1.1 package uses Script Property `CLOUDFLARE_GATEWAY_SECRET`. Its value must equal the Cloudflare Worker secret `GATEWAY_SHARED_SECRET`.

Apps Script API tokens remain Script Properties:

- `ASANA_TOKEN`
- `CLICKUP_TOKEN`
- `MONDAY_TOKEN`
- `AIRTABLE_TOKEN`
- `CLOUDFLARE_GATEWAY_SECRET`

## Pipeline behavior

- Push to branch `integration-v1-cloudflare-pipeline` automatically validates and deploys DEV.
- `workflow_dispatch` with `target=test` promotes the same source to TEST.
- `workflow_dispatch` with `target=production` promotes the same source to PROD.
- Production should not be promoted until the 10-record pilot writes valid external IDs into `INT_MASTER_MAP` for all enabled platforms.

## Production isolation

This V1 pipeline does not modify the existing fabrication production Worker. It deploys dedicated Worker names for the integration gateway.
