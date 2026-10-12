"""
Unit tests for llm/model_config.py.

Tests cover default settings, environment variable overrides, validation rules,
secret masking, and the distinction between client-side and server-launch settings.
All tests run locally without network or model runtime requirements.
"""

import os
import unittest
from unittest.mock import patch
from pydantic import ValidationError

from llm.model_config import (
    ClientConfig,
    GenerationConfig,
    ModelConfig,
    ServerLaunchConfig,
)


class TestModelConfig(unittest.TestCase):
    """Test suite for ModelConfig, ClientConfig, GenerationConfig, and ServerLaunchConfig."""

    def test_default_config_initialization(self):
        """Test default values for all configuration subcomponents."""
        cfg = ModelConfig()

        # Client defaults
        self.assertEqual(cfg.client.base_url, "http://127.0.0.1:8080")
        self.assertEqual(cfg.client.connect_timeout, 5.0)
        self.assertEqual(cfg.client.generation_timeout, 120.0)
        self.assertIsNone(cfg.client.api_key)

        # Generation defaults
        self.assertEqual(cfg.generation.temperature, 0.7)
        self.assertEqual(cfg.generation.top_p, 0.9)
        self.assertEqual(cfg.generation.max_tokens, 1024)
        self.assertFalse(cfg.generation.stream)
        self.assertIsNone(cfg.generation.enable_thinking)

        # Server launch defaults (server-side only)
        self.assertEqual(cfg.server_launch.model_name, "Qwen3-4B")
        self.assertEqual(cfg.server_launch.context_length, 4096)
        self.assertEqual(cfg.server_launch.host, "127.0.0.1")
        self.assertEqual(cfg.server_launch.port, 8080)
        self.assertIsNone(cfg.server_launch.n_gpu_layers)

    def test_client_config_validations(self):
        """Test validation rules for ClientConfig."""
        # Invalid base_url scheme
        with self.assertRaises(ValidationError):
            ClientConfig(base_url="ftp://127.0.0.1:8080")

        # Invalid base_url (missing host)
        with self.assertRaises(ValidationError):
            ClientConfig(base_url="http://")

        # Negative / zero timeouts
        with self.assertRaises(ValidationError):
            ClientConfig(connect_timeout=0.0)

        with self.assertRaises(ValidationError):
            ClientConfig(generation_timeout=-1.0)

        # Trailing slash is stripped automatically
        cfg = ClientConfig(base_url="http://127.0.0.1:8080/")
        self.assertEqual(cfg.base_url, "http://127.0.0.1:8080")

    def test_generation_config_validations(self):
        """Test validation rules for GenerationConfig."""
        # Temperature out of bounds
        with self.assertRaises(ValidationError):
            GenerationConfig(temperature=-0.1)

        with self.assertRaises(ValidationError):
            GenerationConfig(temperature=2.5)

        # Top-p out of bounds
        with self.assertRaises(ValidationError):
            GenerationConfig(top_p=0.0)

        with self.assertRaises(ValidationError):
            GenerationConfig(top_p=1.5)

        # Max tokens <= 0
        with self.assertRaises(ValidationError):
            GenerationConfig(max_tokens=0)

    def test_server_launch_config_validations(self):
        """Test validation rules for ServerLaunchConfig."""
        with self.assertRaises(ValidationError):
            ServerLaunchConfig(context_length=0)

        with self.assertRaises(ValidationError):
            ServerLaunchConfig(port=70000)

        with self.assertRaises(ValidationError):
            ServerLaunchConfig(n_gpu_layers=-1)

    def test_from_env_loading(self):
        """Test loading configuration from environment variables."""
        mock_env = {
            "LLM_BASE_URL": "http://127.0.0.1:9090",
            "LLM_CONNECT_TIMEOUT": "10.0",
            "LLM_GENERATION_TIMEOUT": "60.0",
            "LLM_API_KEY": "secret-token-123",
            "LLM_TEMPERATURE": "0.3",
            "LLM_TOP_P": "0.85",
            "LLM_MAX_TOKENS": "512",
            "LLM_ENABLE_THINKING": "false",
            "LLM_REASONING_BUDGET": "0",
            "LLM_MODEL_NAME": "Qwen3-4B-Custom",
            "LLM_CONTEXT_LENGTH": "2048",
            "LLM_N_GPU_LAYERS": "28",
            "LLM_PORT": "9090",
        }

        with patch.dict(os.environ, mock_env, clear=True):
            cfg = ModelConfig.from_env()

            self.assertEqual(cfg.client.base_url, "http://127.0.0.1:9090")
            self.assertEqual(cfg.client.connect_timeout, 10.0)
            self.assertEqual(cfg.client.generation_timeout, 60.0)
            self.assertIsNotNone(cfg.client.api_key)
            self.assertEqual(cfg.client.api_key.get_secret_value(), "secret-token-123")

            self.assertEqual(cfg.generation.temperature, 0.3)
            self.assertEqual(cfg.generation.top_p, 0.85)
            self.assertEqual(cfg.generation.max_tokens, 512)
            self.assertFalse(cfg.generation.enable_thinking)
            self.assertEqual(cfg.generation.reasoning_budget, 0)

            self.assertEqual(cfg.server_launch.model_name, "Qwen3-4B-Custom")
            self.assertEqual(cfg.server_launch.context_length, 2048)
            self.assertEqual(cfg.server_launch.n_gpu_layers, 28)
            self.assertEqual(cfg.server_launch.port, 9090)

    def test_secret_masking(self):
        """Test that secrets are never exposed in to_safe_dict() or repr()."""
        mock_env = {
            "LLM_API_KEY": "super-secret-key-xyz",
        }

        with patch.dict(os.environ, mock_env, clear=True):
            cfg = ModelConfig.from_env()

            safe_dict = cfg.to_safe_dict()
            self.assertEqual(safe_dict["client"]["api_key"], "********")

            repr_str = repr(cfg)
            self.assertNotIn("super-secret-key-xyz", repr_str)
            self.assertIn("********", repr_str)

    def test_server_client_distinction_documented(self):
        """Verify that server-only settings exist in server_launch, not client."""
        cfg = ModelConfig()
        # context_length and n_gpu_layers are in server_launch, NOT in client
        self.assertTrue(hasattr(cfg.server_launch, "context_length"))
        self.assertTrue(hasattr(cfg.server_launch, "n_gpu_layers"))
        self.assertFalse(hasattr(cfg.client, "context_length"))
        self.assertFalse(hasattr(cfg.client, "n_gpu_layers"))


if __name__ == "__main__":
    unittest.main()

