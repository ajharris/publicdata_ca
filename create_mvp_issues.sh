#!/usr/bin/env bash
set -e

gh issue create \
  --title "Scaffold publicdata_ca package structure" \
  --label "mvp,chore" \
  --body "Create the publicdata_ca package skeleton (catalog, providers, resolvers, tests), add pyproject.toml, and ensure editable install works."

gh issue create \
  --title "Port Dataset catalog and manifest logic from notebook" \
  --label "mvp,feature" \
  --body "Move Dataset dataclass, dataset catalog, and build_run_manifest into importable modules without changing behavior."

gh issue create \
  --title "Implement shared HTTP helper with retries and headers" \
  --label "mvp,feature" \
  --body "Add retry_request helper with default headers, backoff, timeouts, and streaming support. Providers must use this."

gh issue create \
  --title "StatsCan provider: download full table CSV by PID" \
  --label "mvp,feature" \
  --body "Implement StatCan WDS CSV download including manifest parsing, zip extraction, skip-if-exists logic, and basic tests."

gh issue create \
  --title "CMHC landing-page resolver with ranking and validation" \
  --label "mvp,feature" \
  --body "Resolve real XLSX/CSV/ZIP URLs from CMHC landing pages by collecting candidates, ranking them, and rejecting HTML responses."

gh issue create \
  --title "CMHC provider: validated asset download" \
  --label "mvp,feature" \
  --body "Download CMHC assets once a direct URL is known. Reject HTML downloads and surface actionable errors."

gh issue create \
  --title "Add resolved URL caching for CMHC datasets" \
  --label "mvp,feature" \
  --body "Cache resolved CMHC direct URLs in a small JSON file to reduce churn and make refresh runs stable."

gh issue create \
  --title "Implement refresh runner equivalent to notebook automation" \
  --label "mvp,feature" \
  --body "Create a refresh function that iterates the dataset catalog, downloads missing files, and returns a run report DataFrame."

gh issue create \
  --title "Write provenance sidecar metadata for each download" \
  --label "mvp,feature" \
  --body "For each downloaded file, write a .meta.json with source URLs, timestamps, hashes, and content type."

gh issue create \
  --title "Add minimal CLI (publicdata refresh / manifest)" \
  --label "mvp,feature" \
  --body "Provide a CLI wrapper so the entire ingest can be run without notebooks."

gh issue create \
  --title "Tests: CMHC HTML fixtures and StatCan zip extraction" \
  --label "mvp,tests" \
  --body "Add offline tests for CMHC resolvers and StatsCan extraction using saved fixtures."

gh issue create \
  --title "README: quickstart, catalog design, CMHC failure modes" \
  --label "mvp,docs" \
  --body "Document installation, catalog usage, refresh workflow, and how to handle CMHC landing-page churn."
