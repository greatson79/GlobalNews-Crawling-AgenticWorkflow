#!/usr/bin/env bash
# =============================================================================
# GlobalNews Crawling & Analysis System -- Monthly Data Archival
#
# Triggered by cron at 03:00 AM on the 1st of each month.
# Compresses and moves data older than 30 days to the archive directory.
# Verifies archive integrity before deleting originals.
#
# Usage:
#   scripts/archive_old_data.sh              # Normal execution
#   scripts/archive_old_data.sh --dry-run    # Show what would be archived
#   scripts/archive_old_data.sh --days 60    # Custom age threshold
#
# Archive structure:
#   data/archive/YYYY/MM/raw-YYYY-MM-DD.tar.gz
#   data/archive/YYYY/MM/raw-YYYY-MM-DD.tar.gz.sha256
#
# Exit codes:
#   0 -- Archival completed successfully
#   1 -- Archival failed (originals NOT deleted)
#   2 -- Pre-run check failed (disk space)
#
# Reference:
#   PRD Section 12.2 -- Data integrity: 0% loss
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DATA_DIR="${PROJECT_DIR}/data"
ARCHIVE_DIR="${DATA_DIR}/archive"
LOG_DIR="${DATA_DIR}/logs"
ARCHIVE_LOG="${LOG_DIR}/archive/$(date +%Y-%m-%d)-archive.log"

DRY_RUN=false
MAX_AGE_DAYS=30
TODAY="$(date +%Y-%m-%d)"

# Safety: never archive data from today or the last 2 days
SAFETY_MARGIN_DAYS=2

# =============================================================================
# Argument Parsing
# =============================================================================

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --days)
            MAX_AGE_DAYS="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--dry-run] [--days N]" >&2
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
    echo "$msg" | tee -a "${ARCHIVE_LOG}"
}

log_error() {
    local msg="[$(timestamp)] [ERROR] $1"
    echo "$msg" | tee -a "${ARCHIVE_LOG}" >&2
}

log_warn() {
    local msg="[$(timestamp)] [WARN]  $1"
    echo "$msg" | tee -a "${ARCHIVE_LOG}"
}

# Get date N days ago in YYYY-MM-DD format
# Compatible with both macOS (BSD date) and Linux (GNU date)
date_n_days_ago() {
    local n="$1"
    if date -v -1d >/dev/null 2>&1; then
        # macOS BSD date
        date -v "-${n}d" +%Y-%m-%d
    else
        # GNU date
        date -d "${n} days ago" +%Y-%m-%d
    fi
}

# Get directory size in MB
dir_size_mb() {
    local dir="$1"
    if [[ -d "${dir}" ]]; then
        du -sm "${dir}" 2>/dev/null | cut -f1 || echo "0"
    else
        echo "0"
    fi
}

# =============================================================================
# Pre-run Checks
# =============================================================================

check_disk_space() {
    local free_kb
    # Use df on the data directory
    free_kb=$(df -k "${DATA_DIR}" 2>/dev/null | tail -1 | awk '{print $4}')
    local free_gb=$((free_kb / 1024 / 1024))

    if [[ ${free_gb} -lt 1 ]]; then
        log_error "Insufficient disk space: ${free_gb} GB free. Need at least 1 GB for archival."
        return 1
    fi

    log_info "Disk space check: ${free_gb} GB free"
    return 0
}

# =============================================================================
# Archive Functions
# =============================================================================

archive_directory() {
    local source_dir="$1"
    local dir_name
    dir_name="$(basename "${source_dir}")"
    local parent_name
    parent_name="$(basename "$(dirname "${source_dir}")")"

    # Determine archive path from date directory name
    # Expected format: data/raw/YYYY-MM-DD or data/processed/YYYY-MM-DD
    local year="${dir_name:0:4}"
    local month="${dir_name:5:2}"

    if [[ ! "${year}" =~ ^[0-9]{4}$ ]] || [[ ! "${month}" =~ ^[0-9]{2}$ ]]; then
        log_warn "Skipping non-date directory: ${source_dir}"
        return 0
    fi

    local archive_subdir="${ARCHIVE_DIR}/${year}/${month}"
    local archive_name="${parent_name}-${dir_name}"
    local archive_path="${archive_subdir}/${archive_name}.tar.gz"
    local checksum_path="${archive_path}.sha256"

    if [[ -f "${archive_path}" ]]; then
        log_info "Archive already exists: ${archive_path} -- skipping"
        return 0
    fi

    local source_size
    source_size=$(dir_size_mb "${source_dir}")

    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "[DRY RUN] Would archive: ${source_dir} (${source_size} MB) -> ${archive_path}"
        return 0
    fi

    log_info "Archiving: ${source_dir} (${source_size} MB)"

    # Create archive directory
    mkdir -p "${archive_subdir}"

    # Step 1: Create tar.gz archive
    local parent_dir
    parent_dir="$(dirname "${source_dir}")"
    if ! tar -czf "${archive_path}" -C "${parent_dir}" "${dir_name}" 2>> "${ARCHIVE_LOG}"; then
        log_error "tar failed for: ${source_dir}"
        rm -f "${archive_path}"
        return 1
    fi

    # Step 2: Generate checksum
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${archive_path}" > "${checksum_path}"
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "${archive_path}" > "${checksum_path}"
    else
        log_warn "No sha256sum or shasum available. Skipping checksum."
    fi

    # Step 3: Verify archive integrity
    log_info "Verifying archive integrity: ${archive_path}"
    if ! tar -tzf "${archive_path}" >/dev/null 2>&1; then
        log_error "Archive verification FAILED: ${archive_path}"
        log_error "Keeping original data: ${source_dir}"
        rm -f "${archive_path}" "${checksum_path}"
        return 1
    fi

    # Step 4: Verify checksum if present
    if [[ -f "${checksum_path}" ]]; then
        local stored_checksum actual_checksum
        stored_checksum=$(cut -d' ' -f1 < "${checksum_path}")
        if command -v sha256sum >/dev/null 2>&1; then
            actual_checksum=$(sha256sum "${archive_path}" | cut -d' ' -f1)
        elif command -v shasum >/dev/null 2>&1; then
            actual_checksum=$(shasum -a 256 "${archive_path}" | cut -d' ' -f1)
        else
            actual_checksum="${stored_checksum}"
        fi

        if [[ "${stored_checksum}" != "${actual_checksum}" ]]; then
            log_error "Checksum mismatch for: ${archive_path}"
            log_error "Keeping original data: ${source_dir}"
            rm -f "${archive_path}" "${checksum_path}"
            return 1
        fi
    fi

    # Step 5: Remove original only after successful verification
    local archive_size
    archive_size=$(du -sm "${archive_path}" 2>/dev/null | cut -f1 || echo "?")
    log_info "Archive verified. Removing original: ${source_dir} (${source_size} MB -> ${archive_size} MB)"
    rm -rf "${source_dir}"

    log_info "Archived successfully: ${archive_name} (${source_size} -> ${archive_size} MB)"
    return 0
}

# =============================================================================
# Main Archival Logic
# =============================================================================

run_archival() {
    local cutoff_date
    cutoff_date=$(date_n_days_ago "${MAX_AGE_DAYS}")

    # Additional safety margin
    local safety_date
    safety_date=$(date_n_days_ago "${SAFETY_MARGIN_DAYS}")

    log_info "Archival parameters:"
    log_info "  Max age: ${MAX_AGE_DAYS} days"
    log_info "  Cutoff date: ${cutoff_date}"
    log_info "  Safety date: ${safety_date} (never archive newer)"
    log_info "  Archive dir: ${ARCHIVE_DIR}"

    local total_archived=0
    local total_failed=0
    local total_skipped=0
    local space_freed_mb=0

    # Record disk space before
    local disk_before_kb
    disk_before_kb=$(df -k "${DATA_DIR}" 2>/dev/null | tail -1 | awk '{print $4}')

    # Process data/raw/ directories
    for data_subdir in "raw" "processed"; do
        local search_dir="${DATA_DIR}/${data_subdir}"

        if [[ ! -d "${search_dir}" ]]; then
            log_info "Directory does not exist, skipping: ${search_dir}"
            continue
        fi

        log_info "Scanning: ${search_dir}"

        for date_dir in "${search_dir}"/*/; do
            # Remove trailing slash
            date_dir="${date_dir%/}"

            if [[ ! -d "${date_dir}" ]]; then
                continue
            fi

            local dir_date
            dir_date="$(basename "${date_dir}")"

            # Validate date format
            if [[ ! "${dir_date}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
                log_info "Skipping non-date dir: ${date_dir}"
                total_skipped=$((total_skipped + 1))
                continue
            fi

            # Safety: never archive today's data or very recent
            if [[ "${dir_date}" > "${safety_date}" ]] || [[ "${dir_date}" == "${safety_date}" ]]; then
                continue
            fi

            # Age check: only archive if older than cutoff
            if [[ "${dir_date}" > "${cutoff_date}" ]]; then
                continue
            fi

            # Get size before archival for space tracking
            local pre_size
            pre_size=$(dir_size_mb "${date_dir}")

            if archive_directory "${date_dir}"; then
                total_archived=$((total_archived + 1))
                space_freed_mb=$((space_freed_mb + pre_size))
            else
                total_failed=$((total_failed + 1))
            fi
        done
    done

    # Report disk space change
    local disk_after_kb
    disk_after_kb=$(df -k "${DATA_DIR}" 2>/dev/null | tail -1 | awk '{print $4}')
    local disk_freed_mb=$(( (disk_after_kb - disk_before_kb) / 1024 ))
    local disk_free_gb=$((disk_after_kb / 1024 / 1024))

    log_info "============================================"
    log_info "Archival Summary"
    log_info "============================================"
    log_info "  Archived:  ${total_archived} directories"
    log_info "  Failed:    ${total_failed} directories"
    log_info "  Skipped:   ${total_skipped} directories"
    log_info "  Est. data freed: ${space_freed_mb} MB"
    log_info "  Actual disk freed: ${disk_freed_mb} MB"
    log_info "  Disk free now: ${disk_free_gb} GB"

    if [[ ${total_failed} -gt 0 ]]; then
        log_error "${total_failed} archive(s) failed. Originals preserved."
        return 1
    fi

    return 0
}

# =============================================================================
# Entry Point
# =============================================================================

main() {
    mkdir -p "${LOG_DIR}/archive"

    log_info "============================================"
    log_info "GlobalNews Monthly Archival -- START"
    log_info "============================================"
    log_info "Date: ${TODAY}"
    log_info "Dry run: ${DRY_RUN}"

    cd "${PROJECT_DIR}"

    # Pre-run disk check
    if ! check_disk_space; then
        exit 2
    fi

    # Run archival
    local result=0
    run_archival || result=$?

    log_info "============================================"
    if [[ ${result} -eq 0 ]]; then
        log_info "GlobalNews Monthly Archival -- SUCCESS"
    else
        log_info "GlobalNews Monthly Archival -- COMPLETED WITH ERRORS"
    fi
    log_info "============================================"

    exit "${result}"
}

main "$@"
