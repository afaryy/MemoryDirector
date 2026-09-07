mock_provider "google" {}

run "creates_public_api_and_web_services_from_immutable_images" {
  command = plan

  variables {
    project_id   = "memory-director-sandbox-505708"
    region       = "australia-southeast1"
    name_prefix  = "memory-director-sandbox"
    api_image    = "example.invalid/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    web_image    = "example.invalid/web@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    service      = "all"
    api_base_url = null
  }

  assert {
    condition     = output.runtime_service_account_email == "memory-director-runtime@memory-director-sandbox-505708.iam.gserviceaccount.com"
    error_message = "Both app services must use the no-key runtime identity."
  }

  assert {
    condition     = output.service == "all"
    error_message = "The default app foundation state must manage both services."
  }

  assert {
    condition     = startswith(output.api_image, "example.invalid/api@sha256:") && startswith(output.web_image, "example.invalid/web@sha256:")
    error_message = "App services must be configured with immutable image references."
  }

  assert {
    condition     = output.api_memory == "2Gi"
    error_message = "The API needs enough memory for ffmpeg media rendering."
  }

  assert {
    condition     = output.api_media_bucket == "memory-director-sandbox-505708-media"
    error_message = "The API must use the globally unique media bucket derived from the GCP project ID."
  }
}

run "uses_load_balancer_ingress_when_public_ingress_is_disabled" {
  command = plan

  variables {
    project_id     = "memory-director-sandbox"
    region         = "australia-southeast1"
    name_prefix    = "memory-director-sandbox"
    api_image      = "example.invalid/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    web_image      = "example.invalid/web@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    service        = "all"
    public_ingress = false
  }

  assert {
    condition     = output.api_ingress == "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" && output.web_ingress == "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
    error_message = "Locked services must accept traffic only through the load balancer."
  }
}

run "injects_only_the_validated_agent_engine_resource_into_the_api" {
  command = plan

  variables {
    project_id            = "memory-director-505708"
    region                = "australia-southeast1"
    name_prefix           = "memory-director-sandbox"
    api_image             = "example.invalid/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    web_image             = "unused"
    service               = "api"
    agent_engine_resource = "projects/192915586401/locations/australia-southeast1/reasoningEngines/123"
  }

  assert {
    condition     = output.api_environment_variables.MEMORY_FILM_PLANNER_RESOURCE == "projects/192915586401/locations/australia-southeast1/reasoningEngines/123"
    error_message = "The API must receive the smoke-tested Agent Engine resource through Terraform."
  }
}

run "enforces_bounded_api_runtime_and_injects_reviewed_quota_policy" {
  command = plan

  variables {
    project_id  = "memory-director-505708"
    region      = "australia-southeast1"
    name_prefix = "memory-director-sandbox"
    api_image   = "example.invalid/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    web_image   = "example.invalid/web@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    service     = "all"
    runtime_limits = {
      api_min_instances   = 0
      api_max_instances   = 3
      api_concurrency     = 4
      api_timeout_seconds = 900
      web_min_instances   = 0
      web_max_instances   = 2
      web_concurrency     = 80
    }
    application_limits = {
      max_film_duration_seconds  = 60
      max_media_items            = 15
      max_upload_file_mb         = 250
      max_request_text_chars     = 2000
      global_daily_film_hard_max = 100
    }
    quotas = {
      visitor_daily_film_limit          = 5
      ip_daily_film_limit               = 10
      ip_max_concurrent_films           = 2
      global_daily_film_limit           = 30
      global_max_concurrent_films       = 6
      visitor_daily_original_song_limit = 3
      global_daily_original_song_limit  = 20
    }
  }

  assert {
    condition     = output.api_max_instances == 3 && output.api_concurrency == 4 && output.web_max_instances == 2
    error_message = "Cloud Run must use the reviewed API and web scaling boundaries."
  }

  assert {
    condition     = output.api_environment_variables.QUOTA_ENABLED == "true" && output.api_environment_variables.GLOBAL_DAILY_FILM_LIMIT == "30" && output.api_environment_variables.GLOBAL_DAILY_FILM_HARD_MAX == "100"
    error_message = "The API must receive the reviewed quota policy through Terraform."
  }

  assert {
    condition     = output.api_environment_variables.QUOTA_FIRESTORE_DATABASE == "(default)" && output.api_environment_variables.MAX_MEDIA_ITEMS == "15"
    error_message = "The API must use Firestore quota state and common application ceilings."
  }
}
