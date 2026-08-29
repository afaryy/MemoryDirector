# Public edge operations

`public-edge` is the Memory Director public entry component. It creates the
global external HTTPS load balancer, a fixed IPv4 address, serverless NEGs for
the API and web Cloud Run services, managed TLS for `memorydirector.com` and
`www.memorydirector.com`, and DNS-only Cloudflare records. It never manages
the domain registration.

## One-time prerequisites

1. In the GitHub `sandbox` environment, create the secret
   `CLOUDFLARE_API_TOKEN`. The token is restricted to the
   `memorydirector.com` zone with `Zone:DNS:Edit` and `Zone:Read` only.
2. Keep `public_edge` in
   `infra/terraform/projects/config/memory-director.json` accurate. The zone
   ID is non-sensitive; the token must not be stored in this file.
3. Apply the bootstrap identity root once after the related PR is merged, so
   the Terraform WIF identity receives the approved Compute roles.

## Provision

From **Actions → Public domain control** (the
`.github/workflows/public-domain-control.yml` workflow), run `provision`. The
workflow only accepts a commit reachable from `main` and uses the isolated state
prefix `memory-director/sandbox/public-edge`.

Provision deliberately leaves direct Cloud Run ingress unchanged. Copy the
reported address and certificate resource into deployment evidence. Google
managed certificates remain in provisioning state until the DNS-only A and
CNAME records are visible; wait for certificate activation before testing.

Run these checks after it becomes active:

```bash
curl --fail --location https://memorydirector.com/
curl --fail --location https://memorydirector.com/api/health
curl --fail --location --head https://www.memorydirector.com/
```

The last command must show a permanent redirect to `memorydirector.com`.

## Lockdown

Run `lockdown` only after both HTTPS checks succeed. The workflow repeats the
checks, then applies `public_ingress=false` separately to the existing API and
web Terraform state roots. Cloud Run then accepts ingress only through Google
Cloud Load Balancing, while `memorydirector.com` remains the public origin.

If the custom domain is unavailable, do not run lockdown. Before lockdown,
direct `.run.app` URLs stay available for safe recovery.

## Rollback

To restore direct Cloud Run ingress after a failed lockdown, run the normal
Terraform workflow for each app state root with `public_ingress=true`, retaining
the existing immutable image references. Do not destroy bootstrap state,
identity, or application components as a substitute for rollback.

## Destroy

`destroy` requires the exact confirmation `DESTROY_PUBLIC_EDGE`. It removes
only Google public-edge resources and the Cloudflare DNS records. It does not
delete the `memorydirector.com` registration, state bucket, WIF identity,
Cloud Run services, Artifact Registry images, or ClickHouse resources.
