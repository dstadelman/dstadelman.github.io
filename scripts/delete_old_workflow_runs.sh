#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Delete old GitHub Actions workflow runs with the GitHub CLI.

By default this is a dry run. Pass --delete to actually remove runs.
The newest runs are kept separately for each workflow.

Usage:
  scripts/delete_old_workflow_runs.sh [options]

Options:
  -k, --keep COUNT       Number of newest runs to keep per workflow. Default: 1
  -R, --repo OWNER/REPO  Repository to clean. Default: current repository
  -w, --workflow NAME    Workflow file name or workflow ID to clean only one workflow
      --delete           Actually delete old runs
  -h, --help             Show this help text

Examples:
  scripts/delete_old_workflow_runs.sh
  scripts/delete_old_workflow_runs.sh --delete
  scripts/delete_old_workflow_runs.sh --keep 3 --delete
  scripts/delete_old_workflow_runs.sh --repo owner/repo --delete
  scripts/delete_old_workflow_runs.sh --workflow build.yml --delete
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

print_runs() {
  local line workflow_id id created_at name title branch

  printf '%-14s %-25s %-24s %-45s %s\n' "ID" "CREATED" "WORKFLOW" "TITLE" "BRANCH"
  printf '%-14s %-25s %-24s %-45s %s\n' "--" "-------" "--------" "-----" "------"

  for line in "$@"; do
    IFS=$'\t' read -r workflow_id id created_at name title branch <<<"$line"
    printf '%-14s %-25s %-24s %-45s %s\n' "$id" "$created_at" "$name" "$title" "$branch"
  done
}

keep=1
repo=""
workflow=""
delete=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -k|--keep)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      keep="$2"
      shift 2
      ;;
    -R|--repo)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      repo="$2"
      shift 2
      ;;
    -w|--workflow)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      workflow="$2"
      shift 2
      ;;
    --delete)
      delete=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

[[ "$keep" =~ ^[1-9][0-9]*$ ]] || die "--keep must be a positive integer"
command -v gh >/dev/null 2>&1 || die "gh is required but was not found in PATH"

endpoint_repo="repos/{owner}/{repo}"
if [[ -n "$repo" ]]; then
  endpoint_repo="repos/$repo"
fi

if [[ -n "$workflow" ]]; then
  endpoint="$endpoint_repo/actions/workflows/$workflow/runs?per_page=100"
else
  endpoint="$endpoint_repo/actions/runs?per_page=100"
fi

jq_filter='.workflow_runs[]? | [(.workflow_id | tostring), (.id | tostring), .created_at, (.name // ""), (.display_title // ""), (.head_branch // "")] | @tsv'
if ! runs_output="$(gh api --paginate "$endpoint" --jq "$jq_filter")"; then
  die "failed to fetch workflow runs"
fi

runs=()
if [[ -n "$runs_output" ]]; then
  mapfile -t runs < <(printf '%s\n' "$runs_output" | LC_ALL=C sort -t $'\t' -k3,3r -k2,2nr)
fi

run_count=${#runs[@]}
if [[ "$run_count" -eq 0 ]]; then
  echo "No workflow runs found."
  exit 0
fi

declare -A workflow_counts=()
kept_runs=()
delete_runs=()

for line in "${runs[@]}"; do
  IFS=$'\t' read -r workflow_id _id _created_at name _title _branch <<<"$line"
  workflow_key="${workflow_id:-unknown:$name}"
  workflow_count="${workflow_counts[$workflow_key]:-0}"

  if [[ "$workflow_count" -lt "$keep" ]]; then
    kept_runs+=("$line")
  else
    delete_runs+=("$line")
  fi

  workflow_counts[$workflow_key]=$((workflow_count + 1))
done

workflow_count=${#workflow_counts[@]}
echo "Found $run_count workflow run(s) across $workflow_count workflow(s). Keeping ${#kept_runs[@]}, deleting ${#delete_runs[@]}."
echo
echo "Keeping:"
print_runs "${kept_runs[@]}"

if [[ "${#delete_runs[@]}" -eq 0 ]]; then
  echo
  echo "There are no old workflow runs to delete."
  exit 0
fi

echo
echo "Old runs selected for deletion:"
print_runs "${delete_runs[@]}"

if [[ "$delete" -ne 1 ]]; then
  echo
  echo "Dry run only. Re-run with --delete to delete the selected workflow runs."
  exit 0
fi

for line in "${delete_runs[@]}"; do
  IFS=$'\t' read -r _workflow_id run_id _created_at _name title _branch <<<"$line"
  delete_args=(run delete "$run_id")

  if [[ -n "$repo" ]]; then
    delete_args+=(--repo "$repo")
  fi

  echo "Deleting workflow run $run_id: $title"
  gh "${delete_args[@]}"
done

echo "Deleted ${#delete_runs[@]} old workflow run(s)."
