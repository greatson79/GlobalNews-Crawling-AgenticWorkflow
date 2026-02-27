"""Shared fixtures for the 3-layer test suite.

Fixtures provide:
- project_root: path to the actual project root (for structural tests)
- tmp_project: temporary project directory with .claude/ structure
- tmp_project_with_sot: temporary project with initialized SOT (state.yaml)
- sot_manager module: imported sot_manager for direct function testing
"""

import importlib.util
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Path setup — add scripts/ to sys.path for imports
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


# ---------------------------------------------------------------------------
# Module import helpers
# ---------------------------------------------------------------------------

def _import_script(name):
    """Import a script module from scripts/ by name (without .py)."""
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(SCRIPTS_DIR, f"{name}.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root():
    """Return the actual project root path."""
    return PROJECT_ROOT


@pytest.fixture
def agents_dir(project_root):
    """Return the .claude/agents/ directory path."""
    return os.path.join(project_root, ".claude", "agents")


@pytest.fixture
def scripts_dir(project_root):
    """Return the scripts/ directory path."""
    return os.path.join(project_root, "scripts")


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with .claude/ structure.

    Returns the tmp_path root. Does NOT create a SOT file.
    """
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return tmp_path


@pytest.fixture
def tmp_project_with_sot(tmp_project):
    """Create a temporary project with initialized SOT (20-step workflow).

    Returns the tmp_path root with .claude/state.yaml initialized.
    """
    sot = _import_script("sot_manager")
    result = sot.cmd_init(str(tmp_project), "Test Workflow", 20)
    assert result["valid"], f"SOT init failed: {result}"
    return tmp_project


@pytest.fixture
def sot_mod():
    """Import and return the sot_manager module."""
    return _import_script("sot_manager")


@pytest.fixture
def distribute_mod():
    """Import and return the distribute_sites_to_teams module."""
    return _import_script("distribute_sites_to_teams")


@pytest.fixture
def sources_mod():
    """Import and return the generate_sources_yaml_draft module."""
    return _import_script("generate_sources_yaml_draft")


def _create_dummy_output(project_dir, path, size=200):
    """Create a dummy output file with minimum size for L0 validation."""
    full_path = os.path.join(str(project_dir), path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write("# Dummy output\n" + "x" * size)
    return path


@pytest.fixture
def create_output():
    """Factory fixture to create dummy output files in a project directory."""
    return _create_dummy_output


# ---------------------------------------------------------------------------
# GlobalNews System Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_sources_yaml(tmp_path):
    """Create a minimal valid sources.yaml for testing.

    Returns:
        Path to the temporary sources.yaml file.
    """
    content = """
sources:
  test_site:
    name: "Test Site"
    url: "https://www.example.com"
    region: "us"
    language: "en"
    group: "E"
    crawl:
      primary_method: "rss"
      fallback_methods: ["sitemap", "dom"]
      rss_url: "https://www.example.com/rss"
      sitemap_url: "/sitemap.xml"
      rate_limit_seconds: 5
      crawl_delay_mandatory: null
      max_requests_per_hour: 720
      jitter_seconds: 0
    anti_block:
      ua_tier: 2
      default_escalation_tier: 1
      max_escalation_tier: 5
      requires_proxy: false
      proxy_region: null
      bot_block_level: "MEDIUM"
    extraction:
      paywall_type: "none"
      title_only: false
      rendering_required: false
      charset: "utf-8"
    meta:
      difficulty_tier: "Easy"
      daily_article_estimate: 100
      sections_count: 5
      enabled: true
"""
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(content)
    return yaml_path


@pytest.fixture
def sample_pipeline_yaml(tmp_path):
    """Create a minimal valid pipeline.yaml for testing.

    Returns:
        Path to the temporary pipeline.yaml file.
    """
    content = """
pipeline:
  version: "1.0"
  python_version: "3.12"
  global:
    max_memory_gb: 10
    log_level: "INFO"
    gc_between_stages: true
    parquet_compression: "zstd"
    batch_size_default: 500
  stages:
    stage_1_preprocessing:
      enabled: true
      description: "Test stage"
      input_format: "jsonl"
      output_format: "parquet"
      output_path: "data/processed/articles.parquet"
      parallelism: 1
      memory_limit_gb: 1.5
      timeout_seconds: 1800
      models: []
      dependencies: []
"""
    yaml_path = tmp_path / "pipeline.yaml"
    yaml_path.write_text(content)
    return yaml_path
