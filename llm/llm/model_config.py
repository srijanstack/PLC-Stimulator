"""
Centralized, typed configuration system for the local llama.cpp model integration.

This module clearly separates:
1. Client-side settings: connection timeouts, base URL, generation sampling,
   and optional API keys consumed by the Python HTTP client.
2. Server-launch parameters: model path, context length (-c), GPU layers (-ngl),
   and server host/port. These MUST be configured when starting `llama-server.exe`
   and cannot be altered dynamically by the Python client after startup.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


class ClientConfig(BaseModel):
    """Configuration for connecting to the llama.cpp HTTP server."""

    base_url: str = Field(
        default="http://127.0.0.1:8080",
        description="Base URL of the running llama.cpp HTTP server.",
    )
    connect_timeout: float = Field(
        default=5.0,
        gt=0.0,
        description="Timeout in seconds for establishing HTTP connection.",
    )
    generation_timeout: float = Field(
        default=120.0,
        gt=0.0,
        description="Timeout in seconds for generation requests to complete.",
    )
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="Optional API key if the local llama-server was started with --api-key.",
    )
    max_retries: int = Field(
        default=1,
        ge=0,
        description="Maximum number of retry attempts on transient network failures.",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate URL format and strip trailing /v1 if present."""
        cleaned = v.rstrip("/")
        if cleaned.endswith("/v1"):
            cleaned = cleaned[:-3]
        parsed = urlparse(cleaned)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Must be 'http' or 'https'.")
        if not parsed.netloc:
            raise ValueError(f"Invalid base_url '{v}': missing host/port.")
        return cleaned


class GenerationConfig(BaseModel):
    """Sampling and generation parameters sent per request.
    
    These parameters are passed in the HTTP request payload and control
    text generation at inference time.
    """

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature. Lower values are more deterministic.",
    )
    top_p: float = Field(
        default=0.9,
        gt=0.0,
        le=1.0,
        description="Nucleus sampling probability threshold.",
    )
    max_tokens: int = Field(
        default=1024,
        gt=0,
        description="Maximum number of new tokens to generate.",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream tokens via Server-Sent Events (SSE).",
    )
    enable_thinking: Optional[bool] = Field(
        default=None,
        description=(
            "Configures Qwen3 thinking mode. When False, instructs the chat template "
            "to output empty thinking tags (<think>\\n\\n</think>), bypassing chain-of-thought. "
            "When True, enables thinking. When None, follows model/runtime default."
        ),
    )
    reasoning_budget: Optional[int] = Field(
        default=None,
        ge=-1,
        description=(
            "Token budget for reasoning in llama-server (-1 for unrestricted, 0 for immediate end). "
            "Supported by recent llama-server builds."
        ),
    )
    extra_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters forwarded to the llama-server endpoint.",
    )


class ServerLaunchConfig(BaseModel):
    """Parameters required when launching the llama.cpp server executable.

    IMPORTANT: These parameters are server-side startup settings.
    The Python HTTP client CANNOT alter context length, GPU offload, or
    port after llama-server has started. Modifying them here only affects
    launch commands or metadata documentation.
    """

    model_config = ConfigDict(protected_namespaces=())

    model_name: str = Field(
        default="Qwen3-4B",
        description="Model identifier or name (e.g. Qwen3-4B).",
    )
    model_path: Optional[str] = Field(
        default=None,
        description="Local path to the .gguf model file for server launch.",
    )
    context_length: int = Field(
        default=4096,
        gt=0,
        description=(
            "Server context size (-c / --ctx-size). "
            "Designed safe default for 4GB VRAM / 16GB RAM is 4096 (or 2048). "
            "Must be specified at server startup."
        ),
    )
    n_gpu_layers: Optional[int] = Field(
        default=None,
        ge=0,
        description=(
            "Number of layers to offload to GPU (-ngl / --n-gpu-layers). "
            "Must be specified at server startup. For RTX 2050 4GB VRAM, "
            "typically 24 to 28 layers fit safely within ~2.8 GB VRAM."
        ),
    )
    threads: Optional[int] = Field(
        default=None,
        gt=0,
        description="Number of CPU threads to use (-t / --threads) at server startup.",
    )
    host: str = Field(
        default="127.0.0.1",
        description="Host IP to bind llama-server (--host). Default is localhost only.",
    )
    port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="Port for llama-server (--port). Default is 8080.",
    )


class ModelConfig(BaseModel):
    """Central configuration for local LLM integration."""

    model_config = ConfigDict(protected_namespaces=())

    client: ClientConfig = Field(default_factory=ClientConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    server_launch: ServerLaunchConfig = Field(default_factory=ServerLaunchConfig)
    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "quantization": "Q4_K_M",
            "format": "GGUF",
            "runtime": "llama.cpp",
        },
        description="Model and runtime metadata.",
    )

    @classmethod
    def from_env(cls, env_file: Optional[Path | str] = None) -> ModelConfig:
        """Create configuration loaded from environment variables and optional .env file.
        
        A .env file is NOT required if system environment variables or defaults
        are sufficient.
        """
        if env_file:
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
        else:
            # Attempt to load standard .env in working directory if present
            default_env = Path(".env")
            if default_env.exists():
                load_dotenv(dotenv_path=default_env)

        # 1. Parse client settings
        base_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080")
        connect_timeout = float(os.getenv("LLM_CONNECT_TIMEOUT", "5.0"))
        generation_timeout = float(os.getenv("LLM_GENERATION_TIMEOUT", "120.0"))
        api_key_str = os.getenv("LLM_API_KEY")
        api_key = SecretStr(api_key_str) if api_key_str else None

        client_cfg = ClientConfig(
            base_url=base_url,
            connect_timeout=connect_timeout,
            generation_timeout=generation_timeout,
            api_key=api_key,
        )

        # 2. Parse generation settings
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        top_p = float(os.getenv("LLM_TOP_P", "0.9"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))
        
        enable_thinking_raw = os.getenv("LLM_ENABLE_THINKING")
        enable_thinking: Optional[bool] = None
        if enable_thinking_raw is not None:
            enable_thinking = enable_thinking_raw.strip().lower() in ("true", "1", "yes")

        reasoning_budget_raw = os.getenv("LLM_REASONING_BUDGET")
        reasoning_budget: Optional[int] = (
            int(reasoning_budget_raw) if reasoning_budget_raw is not None else None
        )

        gen_cfg = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
            reasoning_budget=reasoning_budget,
        )

        # 3. Parse server launch settings
        model_name = os.getenv("LLM_MODEL_NAME", "Qwen3-4B")
        model_path = os.getenv("LLM_MODEL_PATH")
        context_length = int(os.getenv("LLM_CONTEXT_LENGTH", "4096"))
        n_gpu_layers_raw = os.getenv("LLM_N_GPU_LAYERS")
        n_gpu_layers = int(n_gpu_layers_raw) if n_gpu_layers_raw is not None else None
        threads_raw = os.getenv("LLM_THREADS")
        threads = int(threads_raw) if threads_raw is not None else None
        host = os.getenv("LLM_HOST", "127.0.0.1")
        port = int(os.getenv("LLM_PORT", "8080"))

        server_cfg = ServerLaunchConfig(
            model_name=model_name,
            model_path=model_path,
            context_length=context_length,
            n_gpu_layers=n_gpu_layers,
            threads=threads,
            host=host,
            port=port,
        )

        return cls(
            client=client_cfg,
            generation=gen_cfg,
            server_launch=server_cfg,
        )

    def to_safe_dict(self) -> Dict[str, Any]:
        """Return a serializable dictionary representation with secrets and sensitive info masked."""
        data = self.model_dump()
        # Mask API key if present
        if self.client.api_key:
            data["client"]["api_key"] = "********"
        return data

    def __repr__(self) -> str:
        safe_info = self.to_safe_dict()
        return f"ModelConfig({safe_info})"
