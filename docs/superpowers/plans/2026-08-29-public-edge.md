# Public Edge Implementation Plan

**Goal:** Deliver a safe custom-domain entry point for Memory Director.

**Spec:** `docs/superpowers/specs/2026-08-29-public-edge-design.md`

## Delivered tasks

- [x] Extend non-sensitive project configuration with the validated public-edge
  domain, Cloudflare Zone ID, and `/api` prefix.
- [x] Add testable Cloud Run ingress control and build deployed web images with
  a same-origin `/api` endpoint.
- [x] Implement the reusable serverless-NEG Global External Application Load
  Balancer module, Google-managed TLS, HTTP/HTTPS redirects, and DNS-only
  Cloudflare records.
- [x] Add an isolated component state root and the explicitly approved Compute
  roles to bootstrap identity.
- [x] Add a dispatch-only `public-domain-control.yml` workflow with provision,
  lockdown, and confirmed destroy modes.
- [x] Document provisioning, verification, lockdown, rollback, and safe destroy.

## Verification recorded before review

- API: 43 pytest tests passed.
- Web: 16 Vitest tests passed and a production Next.js build passed.
- Terraform: app foundation (2), public-edge foundation (1), and bootstrap IAM
  (1) tests passed; app and public-edge components validated.
- Configuration validator: 6 tests passed.
- Terraform formatting and TFLint completed locally. Trivy is intentionally
  left to the existing GitHub Actions check because it is not installed locally.

## Remaining external operations

1. Merge the reviewed PR and let the normal application deployment publish the
   same-origin web image.
2. Apply bootstrap identity once with the approved roles.
3. Dispatch `provision`, wait for the managed certificate, and record real
   HTTPS smoke-test evidence.
4. Dispatch `lockdown` only after the real checks pass.
