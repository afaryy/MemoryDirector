#!/usr/bin/env bash
set -euo pipefail

component_directory="${1:?usage: migrate-consent-writer-invoker-state.sh COMPONENT_DIRECTORY}"
legacy_address='module.platform.module.consent_event_writer[0].module.service.google_cloud_run_v2_service_iam_member.invoker_members["0"]'

# The authoritative binding adopts the existing remote grant. Removing the
# former additive member from state prevents Terraform from deleting that grant
# after the new binding is created.
state_listing="$(terraform -chdir="$component_directory" state list)"
if grep -Fqx "$legacy_address" <<<"$state_listing"; then
  terraform -chdir="$component_directory" state rm "$legacy_address"
fi
