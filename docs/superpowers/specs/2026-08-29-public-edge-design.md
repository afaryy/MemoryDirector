# Public edge design

## Purpose

Make `memorydirector.com` the supported public entry point for Memory Director
while retaining a safe and reversible Cloud Run rollout.

## Boundaries

- `bootstrap/state` owns the state backend and is never destroyed by a daily workflow.
- `bootstrap/identity` owns WIF and the Terraform operator's approved GCP roles.
- `components/platform` and `components/app` own application resources.
- `components/public-edge` owns only the global external load balancer, managed
  certificate, serverless NEGs, and Cloudflare DNS records. Its state prefix is
  `memory-director/sandbox/public-edge`.

The component never manages the domain registration, GCS backend, WIF, Cloud
Run service creation, images, or ClickHouse resources.

## Public routing

The apex domain reaches the web Cloud Run service through a serverless NEG. The
same origin's `/api/*` paths reach the API serverless NEG after `/api` is
removed, so FastAPI retains its existing route names. `www` permanently
redirects to the apex; HTTP redirects to HTTPS. Both DNS records are initially
Cloudflare DNS-only so Google can issue the managed certificate.

## Controlled rollout

`provision` creates and reports the edge while Cloud Run remains directly
reachable. The operator waits for managed TLS activation and validates both the
apex page and `/api/health`. Only `lockdown` performs those checks again and
changes the existing API and web services to
`INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`.

The normal `destroy` path removes edge resources and DNS records only. It
requires `DESTROY_PUBLIC_EDGE`; it cannot delete the domain registration or
bootstrap foundations.

## Secrets and evidence

`CLOUDFLARE_API_TOKEN` exists only in GitHub's `sandbox` environment and has
only `Zone:DNS:Edit` and `Zone:Read` for `memorydirector.com`. The Zone ID is a
non-sensitive JSON configuration value. The workflow records the edge IP,
certificate resource, and smoke-test outcome; no documentation may claim live
DNS, certificate, or smoke-test success before the manually dispatched
workflow produces it.
