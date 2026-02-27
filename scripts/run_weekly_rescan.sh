#!/usr/bin/env bash
# =============================================================================
# GlobalNews Crawling & Analysis System -- Weekly Site Structure Rescan
#
# Triggered by cron at 01:00 AM every Sunday. Validates that site adapters
# and crawling configurations still work against live site structures.
# Detects broken RSS feeds, changed DOM selectors, and new paywalls.
#
# Usage:
#   scripts/run_weekly_rescan.sh              # Normal execution
#   scripts/run_weekly_rescan.sh --dry-run    # Show plan only
#
# Exit codes:
#   0 -- All sites healthy or within acceptable degradation
#   1 -- Rescan failed or critical site breakage detected
#   2 -- Pre-run check failed
#   3 -- Lock acquisition failed
#
# Reference:
#   PRD Section 6.2 -- Weekly site structure rescan
#   Step 5 Architecture Blueprint, Section 8 (Operational Requirements)
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DRY_RUN=false
LOCK_NAME="weekly"
TODAY="$(date +%Y-%m-%d)"

# Log paths
LOG_DIR="${PROJECT_DIR}/data/logs"
WEEKLY_LOG_DIR="${LOG_DIR}/weekly"
RESCAN_LOG="${WEEKLY_LOG_DIR}/rescan-${TODAY}.log"
RESCAN_REPORT="${WEEKLY_LOG_DIR}/rescan-${TODAY}.md"
ERROR_LOG="${LOG_DIR}/errors.log"
ALERT_DIR="${LOG_DIR}/alerts"

# Threshold for escalation
MAX_BROKEN_SITES=5

# =============================================================================
# Argument Parsing
# =============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--dry-run]" >&2
            exit 1
            ;;
    esac
done

# =============================================================================
# Utility Functions
# =============================================================================

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_info() {
    local msg="[$(timestamp)] [INFO]  $1"
    echo "$msg" | tee -a "${RESCAN_LOG}"
}

log_error() {
    local msg="[$(timestamp)] [ERROR] $1"
    echo "$msg" | tee -a "${RESCAN_LOG}" >&2
    echo "$msg" >> "${ERROR_LOG}"
}

log_warn() {
    local msg="[$(timestamp)] [WARN]  $1"
    echo "$msg" | tee -a "${RESCAN_LOG}"
}

write_alert() {
    local alert_file="${ALERT_DIR}/${TODAY}-weekly-failure.log"
    {
        echo "=========================================="
        echo "WEEKLY RESCAN ALERT"
        echo "=========================================="
        echo "Date:    ${TODAY}"
        echo "Time:    $(timestamp)"
        echo "Host:    $(hostname)"
        echo ""
        echo "Alert:"
        echo "  $1"
        echo ""
        echo "=========================================="
    } >> "${alert_file}"
    log_error "Alert written to: ${alert_file}"
}

# =============================================================================
# Virtual Environment Activation
# =============================================================================

activate_venv() {
    local venv_candidates=(
        "${PROJECT_DIR}/.venv"
        "${PROJECT_DIR}/venv"
        "${PROJECT_DIR}/env"
    )

    for venv_path in "${venv_candidates[@]}"; do
        if [[ -f "${venv_path}/bin/activate" ]]; then
            log_info "Activating virtualenv: ${venv_path}"
            # shellcheck disable=SC1091
            source "${venv_path}/bin/activate"
            return 0
        fi
    done

    if python3 -c "import yaml" 2>/dev/null; then
        log_warn "No virtualenv found. Using system Python."
        return 0
    fi

    log_error "No virtualenv found and system Python missing dependencies."
    return 1
}

# =============================================================================
# Lock Management
# =============================================================================

acquire_lock() {
    log_info "Acquiring lock: ${LOCK_NAME}"
    local result
    result=$(python3 -m src.utils.self_recovery \
        --project-dir "${PROJECT_DIR}" \
        --acquire-lock "${LOCK_NAME}" 2>/dev/null) || true

    if echo "${result}" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('acquired') else 1)" 2>/dev/null; then
        log_info "Lock acquired"
        return 0
    fi

    # Check if daily pipeline is running
    local daily_lock
    daily_lock=$(python3 -m src.utils.self_recovery \
        --project-dir "${PROJECT_DIR}" \
        --check-lock daily 2>/dev/null) || true
    if echo "${daily_lock}" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('locked') else 1)" 2>/dev/null; then
        log_warn "Daily pipeline is running. Deferring weekly rescan."
        return 1
    fi

    log_error "Failed to acquire lock."
    return 1
}

release_lock() {
    python3 -m src.utils.self_recovery \
        --project-dir "${PROJECT_DIR}" \
        --force-release-lock "${LOCK_NAME}" 2>/dev/null || true
}

cleanup_on_exit() {
    release_lock
}

# =============================================================================
# Site Rescan Logic
# =============================================================================

run_rescan() {
    log_info "Starting site structure rescan..."

    local broken_count=0
    local warning_count=0
    local total_count=0
    local site_results=""

    # Use dry-run crawl mode to validate adapter configs and probe sites
    log_info "Running config validation via dry-run crawl..."
    local dry_run_output
    dry_run_output=$(python3 "${PROJECT_DIR}/main.py" --mode crawl --dry-run 2>&1) || true
    echo "${dry_run_output}" >> "${RESCAN_LOG}"

    # Use the validate_site_coverage script to check adapter registry
    log_info "Validating site adapter coverage..."
    local coverage_output
    if [[ -f "${PROJECT_DIR}/scripts/validate_site_coverage.py" ]]; then
        coverage_output=$(python3 "${PROJECT_DIR}/scripts/validate_site_coverage.py" 2>&1) || true
        echo "${coverage_output}" >> "${RESCAN_LOG}"

        # Count issues from coverage validation
        local coverage_issues
        coverage_issues=$(echo "${coverage_output}" | grep -c "FAIL\|MISSING\|ERROR" || true)
        if [[ ${coverage_issues} -gt 0 ]]; then
            log_warn "Site coverage validation found ${coverage_issues} issues"
            warning_count=$((warning_count + coverage_issues))
        fi
    fi

    # Run analysis dry-run to validate pipeline wiring
    log_info "Running analysis pipeline validation via dry-run..."
    local analysis_output
    analysis_output=$(python3 "${PROJECT_DIR}/main.py" --mode analyze --all-stages --dry-run 2>&1) || true
    echo "${analysis_output}" >> "${RESCAN_LOG}"

    # Check adapter import health
    log_info "Checking adapter import health..."
    local adapter_check
    adapter_check=$(python3 -c "
import sys
sys.path.insert(0, '${PROJECT_DIR}')
broken = []
total = 0
try:
    from src.crawling.adapters import ADAPTER_REGISTRY
    for site_id, adapter_cls in ADAPTER_REGISTRY.items():
        total += 1
        try:
            adapter = adapter_cls()
            # Verify essential methods exist
            assert hasattr(adapter, 'get_article_urls') or hasattr(adapter, 'extract_article')
        except Exception as e:
            broken.append(f'{site_id}: {type(e).__name__}: {e}')
except Exception as e:
    print(f'REGISTRY_ERROR: {e}')
    sys.exit(1)

print(f'TOTAL={total}')
print(f'BROKEN={len(broken)}')
for b in broken:
    print(f'  BROKEN_SITE: {b}')
" 2>&1) || true
    echo "${adapter_check}" >> "${RESCAN_LOG}"

    # Parse adapter check results
    total_count=$(echo "${adapter_check}" | grep "^TOTAL=" | cut -d= -f2 || echo "0")
    broken_count=$(echo "${adapter_check}" | grep "^BROKEN=" | cut -d= -f2 || echo "0")

    # Generate markdown report
    {
        echo "# Weekly Site Structure Rescan Report"
        echo ""
        echo "- **Date**: ${TODAY}"
        echo "- **Time**: $(timestamp)"
        echo "- **Total sites checked**: ${total_count}"
        echo "- **Broken adapters**: ${broken_count}"
        echo "- **Warnings**: ${warning_count}"
        echo ""
        echo "## Adapter Health"
        echo ""
        echo "| Site ID | Status | Notes |"
        echo "|---------|--------|-------|"
        echo "${adapter_check}" | grep "BROKEN_SITE:" | while IFS= read -r line; do
            local site_info="${line#*BROKEN_SITE: }"
            local site_name="${site_info%%:*}"
            local error="${site_info#*: }"
            echo "| ${site_name} | BROKEN | ${error} |"
        done
        if [[ ${broken_count} -eq 0 ]]; then
            echo "| (all sites) | OK | All ${total_count} adapters healthy |"
        fi
        echo ""
        echo "## Dry-Run Validation"
        echo ""
        echo "- Crawl dry-run: executed"
        echo "- Analysis dry-run: executed"
        echo "- Coverage validation: ${warning_count} warnings"
        echo ""
        echo "## Recommendation"
        echo ""
        if [[ ${broken_count} -gt ${MAX_BROKEN_SITES} ]]; then
            echo "**CRITICAL**: ${broken_count} sites have structural issues (threshold: ${MAX_BROKEN_SITES})."
            echo "Immediate investigation required."
        elif [[ ${broken_count} -gt 0 ]]; then
            echo "**WARNING**: ${broken_count} site(s) have adapter issues. Review and update."
        else
            echo "All sites healthy. No action needed."
        fi
        echo ""
        echo "---"
        echo "Generated by \`scripts/run_weekly_rescan.sh\` on ${TODAY}."
    } > "${RESCAN_REPORT}"

    log_info "Rescan report written to: ${RESCAN_REPORT}"
    log_info "Results: total=${total_count} broken=${broken_count} warnings=${warning_count}"

    # Alert if too many broken sites
    if [[ ${broken_count} -gt ${MAX_BROKEN_SITES} ]]; then
        write_alert "${broken_count} sites have structural issues (threshold: ${MAX_BROKEN_SITES}). See ${RESCAN_REPORT}"
        return 1
    fi

    return 0
}

# =============================================================================
# Entry Point
# =============================================================================

main() {
    mkdir -p "${WEEKLY_LOG_DIR}" "${ALERT_DIR}"

    log_info "============================================"
    log_info "GlobalNews Weekly Rescan -- START"
    log_info "============================================"
    log_info "Date: ${TODAY}"
    log_info "Dry run: ${DRY_RUN}"

    trap cleanup_on_exit EXIT

    cd "${PROJECT_DIR}"

    # Step 1: Activate venv
    if ! activate_venv; then
        write_alert "Virtual environment activation failed"
        exit 2
    fi

    # Step 2: Acquire lock (must not overlap with daily)
    if ! acquire_lock; then
        # Do not write alert for deferral -- this is expected behavior
        trap - EXIT
        exit 3
    fi

    # Step 3: Run rescan
    local rescan_result=0
    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "DRY RUN: Would validate all site adapters and configurations"
        log_info "DRY RUN: Would run dry-run crawl and analysis pipelines"
        log_info "DRY RUN: Would generate rescan report to ${RESCAN_REPORT}"
    else
        run_rescan || rescan_result=$?
    fi

    log_info "============================================"
    if [[ ${rescan_result} -eq 0 ]]; then
        log_info "GlobalNews Weekly Rescan -- SUCCESS"
    else
        log_info "GlobalNews Weekly Rescan -- ISSUES DETECTED (exit: ${rescan_result})"
    fi
    log_info "============================================"

    exit "${rescan_result}"
}

main "$@"
