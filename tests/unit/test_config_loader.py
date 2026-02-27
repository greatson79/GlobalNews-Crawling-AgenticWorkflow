"""Tests for src.utils.config_loader -- YAML config loading and validation."""

import sys
from pathlib import Path

import pytest
import yaml

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config_loader import (
    validate_sources_config,
    validate_pipeline_config,
    load_sources_config,
    load_pipeline_config,
    ConfigValidationError,
    clear_config_cache,
)


class TestSourcesValidation:
    """Test sources.yaml validation logic."""

    def test_valid_minimal_config(self, sample_sources_yaml):
        """A minimal valid config should produce no errors."""
        with open(sample_sources_yaml) as f:
            config = yaml.safe_load(f)
        errors = validate_sources_config(config)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_missing_sources_key(self):
        """Config without 'sources' key should fail."""
        errors = validate_sources_config({"version": "1.0"})
        assert len(errors) == 1
        assert "No 'sources' key" in errors[0]

    def test_invalid_region(self):
        """Invalid region code should be flagged."""
        config = {
            "sources": {
                "test": {
                    "name": "Test",
                    "url": "https://example.com",
                    "region": "xx",  # Invalid
                    "language": "en",
                    "group": "E",
                    "crawl": {
                        "primary_method": "rss",
                        "fallback_methods": [],
                        "rate_limit_seconds": 5,
                    },
                    "anti_block": {
                        "ua_tier": 2,
                        "bot_block_level": "MEDIUM",
                    },
                    "extraction": {"paywall_type": "none"},
                    "meta": {
                        "difficulty_tier": "Easy",
                        "daily_article_estimate": 100,
                        "enabled": True,
                    },
                }
            }
        }
        errors = validate_sources_config(config)
        assert any("region" in e for e in errors)

    def test_invalid_url(self):
        """URL not starting with http(s):// should be flagged."""
        config = {
            "sources": {
                "test": {
                    "name": "Test",
                    "url": "ftp://example.com",  # Invalid
                    "region": "us",
                    "language": "en",
                    "group": "E",
                    "crawl": {
                        "primary_method": "rss",
                        "fallback_methods": [],
                        "rate_limit_seconds": 5,
                    },
                    "anti_block": {
                        "ua_tier": 2,
                        "bot_block_level": "MEDIUM",
                    },
                    "extraction": {"paywall_type": "none"},
                    "meta": {
                        "difficulty_tier": "Easy",
                        "daily_article_estimate": 100,
                        "enabled": True,
                    },
                }
            }
        }
        errors = validate_sources_config(config)
        assert any("url" in e.lower() for e in errors)


class TestPipelineValidation:
    """Test pipeline.yaml validation logic."""

    def test_valid_minimal_config(self, sample_pipeline_yaml):
        """A minimal valid pipeline config should produce no errors."""
        with open(sample_pipeline_yaml) as f:
            config = yaml.safe_load(f)
        errors = validate_pipeline_config(config)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_missing_pipeline_key(self):
        """Config without 'pipeline' key should fail."""
        errors = validate_pipeline_config({"version": "1.0"})
        assert len(errors) == 1
        assert "No 'pipeline' key" in errors[0]

    def test_memory_exceeds_limit(self):
        """Memory limit > 10 GB should be flagged."""
        config = {
            "pipeline": {
                "global": {
                    "max_memory_gb": 20,  # Exceeds 10 GB limit
                    "parquet_compression": "zstd",
                },
                "stages": {},
            }
        }
        errors = validate_pipeline_config(config)
        assert any("max_memory_gb" in e for e in errors)

    def test_invalid_compression(self):
        """Invalid compression type should be flagged."""
        config = {
            "pipeline": {
                "global": {
                    "max_memory_gb": 10,
                    "parquet_compression": "bzip2",  # Invalid
                },
                "stages": {},
            }
        }
        errors = validate_pipeline_config(config)
        assert any("parquet_compression" in e for e in errors)


class TestConfigLoading:
    """Test config file loading functionality."""

    def test_load_sources_from_file(self, sample_sources_yaml):
        """Loading a valid sources.yaml should succeed."""
        clear_config_cache()
        config = load_sources_config(path=sample_sources_yaml, use_cache=False)
        assert "sources" in config
        assert "test_site" in config["sources"]

    def test_load_pipeline_from_file(self, sample_pipeline_yaml):
        """Loading a valid pipeline.yaml should succeed."""
        clear_config_cache()
        config = load_pipeline_config(path=sample_pipeline_yaml, use_cache=False)
        assert "pipeline" in config
        assert "stages" in config["pipeline"]

    def test_load_nonexistent_file_raises(self, tmp_path):
        """Loading a nonexistent file should raise FileNotFoundError."""
        clear_config_cache()
        with pytest.raises(FileNotFoundError):
            load_sources_config(path=tmp_path / "nonexistent.yaml", use_cache=False)

    def test_validation_error_raised(self, tmp_path):
        """Invalid config should raise ConfigValidationError when validate=True."""
        clear_config_cache()
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("version: 1.0\n")
        with pytest.raises(ConfigValidationError):
            load_sources_config(path=bad_yaml, use_cache=False, validate=True)
