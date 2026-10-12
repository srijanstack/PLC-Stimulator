"""
Unit tests for llm/llama_cpp_client.py.

All tests use mocked HTTP responses (unittest.mock) and do NOT require
a running llama-server process or network access.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import httpx

from llm.llama_cpp_client import (
    GenerationResult,
    LlamaCppClient,
    LlamaCppConnectionError,
    LlamaCppInvalidResponseError,
    LlamaCppServerError,
    LlamaCppTimeoutError,
    StreamChunk,
)
from llm.model_config import GenerationConfig, ModelConfig


class TestLlamaCppClient(unittest.TestCase):
    """Test suite for LlamaCppClient."""

    def setUp(self):
        """Set up client with standard test configuration."""
        self.config = ModelConfig()
        self.client = LlamaCppClient(config=self.config)

    def tearDown(self):
        self.client.close()

    # ------------------------------------------------------------------------
    # Health and Status Checks
    # ------------------------------------------------------------------------

    @patch.object(httpx.Client, "get")
    def test_check_health_success(self, mock_get):
        """Test health check returns reachable=True when server returns HTTP 200."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        health = self.client.check_health()
        self.assertTrue(health["reachable"])
        self.assertEqual(health["status_code"], 200)
        self.assertTrue(self.client.is_healthy())

    @patch.object(httpx.Client, "get")
    def test_check_health_model_loading_503(self, mock_get):
        """Test health check handles 503 while model is still loading."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 503
        mock_response.text = "Loading model..."
        mock_get.return_value = mock_response

        health = self.client.check_health()
        self.assertTrue(health["reachable"])
        self.assertEqual(health["status_code"], 503)
        self.assertEqual(health["status"], "loading")
        self.assertFalse(self.client.is_healthy())

    @patch.object(httpx.Client, "get")
    def test_check_health_connection_error(self, mock_get):
        """Test health check raises LlamaCppConnectionError when connection fails."""
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        with self.assertRaises(LlamaCppConnectionError):
            self.client.check_health()
        self.assertFalse(self.client.is_healthy())

    @patch.object(httpx.Client, "get")
    def test_check_health_timeout(self, mock_get):
        """Test health check raises LlamaCppTimeoutError on timeout."""
        mock_get.side_effect = httpx.ConnectTimeout("Connect timed out")

        with self.assertRaises(LlamaCppTimeoutError):
            self.client.check_health()

    @patch.object(httpx.Client, "get")
    def test_get_status_composite(self, mock_get):
        """Test get_status combines health and model metadata."""
        def mock_dispatch(url, *args, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            if url == "/health":
                resp.status_code = 200
                resp.json.return_value = {"status": "ok"}
            elif url == "/v1/models":
                resp.status_code = 200
                resp.json.return_value = {"data": [{"id": "Qwen3-4B"}]}
            elif url == "/props":
                resp.status_code = 200
                resp.json.return_value = {"total_slots": 1}
            return resp

        mock_get.side_effect = mock_dispatch

        status = self.client.get_status()
        self.assertTrue(status["health"]["reachable"])
        self.assertEqual(len(status["models"]), 1)
        self.assertEqual(status["models"][0]["id"], "Qwen3-4B")
        self.assertIn("props", status)

    # ------------------------------------------------------------------------
    # Generation: Non-Streaming & Parsing
    # ------------------------------------------------------------------------

    @patch.object(httpx.Client, "post")
    def test_chat_generation_success_with_runtime_metrics(self, mock_post):
        """Test successful generation parsing with runtime-supplied timings."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-test",
            "model": "Qwen3-4B",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello, world!",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
            "timings": {
                "predicted_per_second": 25.4,
            },
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Hi"}]
        result = self.client.chat(messages)

        self.assertEqual(result.content, "Hello, world!")
        self.assertIsNone(result.thinking)
        self.assertIsNone(result.text_without_thinking)
        self.assertEqual(result.prompt_tokens, 10)
        self.assertEqual(result.completion_tokens, 5)
        self.assertEqual(result.total_tokens, 15)
        self.assertEqual(result.tokens_per_second, 25.4)
        self.assertEqual(result.metrics_source, "runtime")
        self.assertEqual(result.finish_reason, "stop")

    @patch.object(httpx.Client, "post")
    def test_qwen3_thinking_tag_parsing(self, mock_post):
        """Test that Qwen3 <think>...</think> tags are cleanly extracted while preserving raw content."""
        raw_text = "<think>\nStep 1: Analyze question.\nStep 2: Formulate answer.\n</think>\nThis is the final answer."

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": raw_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"completion_tokens": 20},
        }
        mock_post.return_value = mock_response

        result = self.client.generate("Test prompt")

        # Crucial requirement: Raw content must NEVER be silently stripped
        self.assertEqual(result.content, raw_text)
        # Thinking extracted separately
        self.assertEqual(result.thinking, "Step 1: Analyze question.\nStep 2: Formulate answer.")
        # Clean answer extracted separately
        self.assertEqual(result.text_without_thinking, "This is the final answer.")

    @patch.object(httpx.Client, "post")
    def test_qwen3_thinking_parameters_passed_to_request(self, mock_post):
        """Test that enable_thinking=False and reasoning_budget are properly sent to the server."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Direct reply"}}]
        }
        mock_post.return_value = mock_response

        gen_override = GenerationConfig(
            enable_thinking=False,
            reasoning_budget=0,
        )

        self.client.generate("Direct question", override_config=gen_override)

        # Inspect payload sent to server
        call_kwargs = mock_post.call_args.kwargs
        json_payload = call_kwargs["json"]

        self.assertEqual(json_payload["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(json_payload["reasoning_budget"], 0)

    @patch.object(httpx.Client, "post")
    def test_metric_calculation_fallback_calculated(self, mock_post):
        """Test calculation of tokens_per_second when runtime timings are absent."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        # No 'timings' key, but 'usage' is present
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Quick test"}}],
            "usage": {"completion_tokens": 10},
        }
        mock_post.return_value = mock_response

        result = self.client.generate("Test")
        self.assertEqual(result.completion_tokens, 10)
        self.assertEqual(result.metrics_source, "calculated")
        self.assertIsNotNone(result.tokens_per_second)
        self.assertGreater(result.tokens_per_second, 0.0)

    @patch.object(httpx.Client, "post")
    def test_missing_metrics_handled_gracefully(self, mock_post):
        """Test that when usage and timings are both absent, metrics_source is 'unavailable'."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        # Empty usage and no timings
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "No metrics reply"}}],
        }
        mock_post.return_value = mock_response

        result = self.client.generate("Test")
        self.assertIsNone(result.completion_tokens)
        self.assertIsNone(result.tokens_per_second)
        self.assertEqual(result.metrics_source, "unavailable")

    # ------------------------------------------------------------------------
    # Error Handling
    # ------------------------------------------------------------------------

    @patch.object(httpx.Client, "post")
    def test_generation_connection_error(self, mock_post):
        """Test LlamaCppConnectionError raised on post connection failure."""
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        with self.assertRaises(LlamaCppConnectionError):
            self.client.generate("Test")

    @patch.object(httpx.Client, "post")
    def test_generation_timeout_error(self, mock_post):
        """Test LlamaCppTimeoutError raised on generation timeout."""
        mock_post.side_effect = httpx.ReadTimeout("Generation timed out")
        with self.assertRaises(LlamaCppTimeoutError):
            self.client.generate("Test")

    @patch.object(httpx.Client, "post")
    def test_generation_server_500_error(self, mock_post):
        """Test LlamaCppServerError raised on HTTP 500."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error in llama-server"
        mock_post.return_value = mock_response

        with self.assertRaises(LlamaCppServerError):
            self.client.generate("Test")

    @patch.object(httpx.Client, "post")
    def test_generation_bad_request_400(self, mock_post):
        """Test LlamaCppInvalidResponseError raised on HTTP 400."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.text = "Bad context length"
        mock_post.return_value = mock_response

        with self.assertRaises(LlamaCppInvalidResponseError):
            self.client.generate("Test")

    @patch.object(httpx.Client, "post")
    def test_generation_malformed_json_response(self, mock_post):
        """Test LlamaCppInvalidResponseError raised on invalid JSON body."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        mock_post.return_value = mock_response

        with self.assertRaises(LlamaCppInvalidResponseError):
            self.client.generate("Test")

    @patch.object(httpx.Client, "post")
    def test_generation_missing_choices_field(self, mock_post):
        """Test LlamaCppInvalidResponseError raised when choices field is missing."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test", "choices": []}
        mock_post.return_value = mock_response

        with self.assertRaises(LlamaCppInvalidResponseError):
            self.client.generate("Test")

    def test_empty_messages_validation(self):
        """Test that empty messages list raises ValueError."""
        with self.assertRaises(ValueError):
            self.client.chat([])

    # ------------------------------------------------------------------------
    # Streaming Behavior
    # ------------------------------------------------------------------------

    @patch.object(httpx.Client, "stream")
    def test_streaming_generation(self, mock_stream):
        """Test stream_chat accurately streams chunks and tracks TTFT."""
        mock_stream_ctx = MagicMock()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200

        # Simulate SSE response stream
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " "}}]}',
            'data: {"choices": [{"delta": {"content": "World!"}, "finish_reason": "stop"}]}',
            'data: [DONE]',
        ]
        mock_resp.iter_lines.return_value = iter(sse_lines)

        mock_stream_ctx.__enter__.return_value = mock_resp
        mock_stream.return_value = mock_stream_ctx

        chunks = list(self.client.stream_generate("Hi"))

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].delta, "Hello")
        self.assertTrue(chunks[0].is_first_token)
        self.assertIsNotNone(chunks[0].time_to_first_token)

        self.assertEqual(chunks[1].delta, " ")
        self.assertFalse(chunks[1].is_first_token)
        self.assertIsNone(chunks[1].time_to_first_token)

        self.assertEqual(chunks[2].delta, "World!")
        self.assertEqual(chunks[2].cumulative_text, "Hello World!")
        self.assertEqual(chunks[2].finish_reason, "stop")


if __name__ == "__main__":
    unittest.main()

