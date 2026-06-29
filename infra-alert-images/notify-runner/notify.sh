#!/usr/bin/env sh
set -eu

echo "[notify-runner] start failure notification"

if [ -z "${ALERT_RELAY_URL:-}" ]; then
  echo "[notify-runner] ALERT_RELAY_URL is not set. Skip alert."
  exit 0
fi

if [ -z "${ALERT_RELAY_TOKEN:-}" ]; then
  echo "[notify-runner] ALERT_RELAY_TOKEN is not set. Skip alert."
  exit 0
fi

ERROR_SUMMARY_FILE="${ERROR_SUMMARY_FILE:-ci_error_summary.txt}"
FOUND_SUMMARY_FILE=""

if [ -f "$ERROR_SUMMARY_FILE" ]; then
  FOUND_SUMMARY_FILE="$ERROR_SUMMARY_FILE"
else
  FOUND_SUMMARY_FILE="$(find . -type f \( -name 'ci_error_summary.txt' -o -name 'ci_error_summary*.txt' \) | sort | tail -n 1 || true)"
fi

if [ -n "${FOUND_SUMMARY_FILE:-}" ] && [ -f "$FOUND_SUMMARY_FILE" ]; then
  ERROR_SUMMARY="$(tail -n 80 "$FOUND_SUMMARY_FILE")"
else
  ERROR_SUMMARY="No error summary file found. Please check the GitLab job log."
fi

if [ -n "${ALERT_PLANE:-}" ]; then
  PLANE="$ALERT_PLANE"
else
  case "${CI_JOB_STAGE:-}" in
    build-base|security-scan)
      PLANE="private"
      ;;
    verify)
      PLANE="verify"
      ;;
    *)
      PLANE="hybrid"
      ;;
  esac
fi

jq -n \
  --arg project "${CI_PROJECT_NAME:-unknown}" \
  --arg project_path "${CI_PROJECT_PATH:-unknown}" \
  --arg pipeline_id "${CI_PIPELINE_ID:-unknown}" \
  --arg job_id "${CI_JOB_ID:-unknown}" \
  --arg job "${CI_JOB_NAME:-unknown}" \
  --arg stage "${CI_JOB_STAGE:-unknown}" \
  --arg status "failed" \
  --arg branch "${CI_COMMIT_REF_NAME:-unknown}" \
  --arg commit "${CI_COMMIT_SHORT_SHA:-unknown}" \
  --arg runner_description "${CI_RUNNER_DESCRIPTION:-unknown}" \
  --arg runner_tags "${CI_RUNNER_TAGS:-unknown}" \
  --arg server_url "${CI_SERVER_URL:-unknown}" \
  --arg pipeline_url "${CI_PIPELINE_URL:-unknown}" \
  --arg job_url "${CI_JOB_URL:-unknown}" \
  --arg created_at "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  --arg severity "critical" \
  --arg plane "$PLANE" \
  --arg error_summary "$ERROR_SUMMARY" \
  '{
    project: $project,
    project_path: $project_path,
    pipeline_id: $pipeline_id,
    job_id: $job_id,
    job: $job,
    stage: $stage,
    status: $status,
    branch: $branch,
    commit: $commit,
    runner_description: $runner_description,
    runner_tags: $runner_tags,
    server_url: $server_url,
    pipeline_url: $pipeline_url,
    job_url: $job_url,
    created_at: $created_at,
    severity: $severity,
    plane: $plane,
    error_summary: $error_summary
  }' > /tmp/alert-payload.json

echo "[notify-runner] send alert to relay: ${ALERT_RELAY_URL}"

curl -sS -X POST "$ALERT_RELAY_URL" \
  -H "Content-Type: application/json" \
  -H "X-Relay-Token: ${ALERT_RELAY_TOKEN}" \
  --data-binary @/tmp/alert-payload.json

echo
echo "[notify-runner] alert sent"
