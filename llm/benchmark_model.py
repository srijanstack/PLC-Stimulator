"""
Benchmark script for measuring local llama.cpp model throughput and latency.

This benchmark uses a fixed neutral engineering prompt to evaluate runtime
performance independently of domain-specific (PLC / ladder logic) knowledge or RAG.

DISCLAIMER:
This tool measures local inference latency and token throughput only.
It does NOT measure PLC accuracy, RAG quality, or ladder-logic correctness.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from typing import List, Optional

from llm.llama_cpp_client import (
    GenerationResult,
    LlamaCppClient,
    LlamaCppConnectionError,
    LlamaCppError,
    LlamaCppTimeoutError,
)
from llm.model_config import GenerationConfig, ModelConfig

DEFAULT_NEUTRAL_PROMPT = (
    "Explain the basic principle of a negative feedback control loop "
    "in three concise sentences."
)


def run_benchmark(
    base_url: Optional[str] = None,
    runs: int = 3,
    stream: bool = False,
    prompt: str = DEFAULT_NEUTRAL_PROMPT,
    enable_thinking: Optional[bool] = None,
    max_tokens: int = 512,
    warmup: bool = False,
) -> int:
    """Execute the local model benchmark.

    Args:
        base_url: Optional override for the server base URL.
        runs: Number of benchmark repetitions.
        stream: Whether to stream tokens and measure Time To First Token (TTFT).
        prompt: Fixed neutral prompt.
        enable_thinking: Optional override for Qwen3 thinking mode.
        max_tokens: Maximum tokens to generate per repetition.
        warmup: Whether to execute 1 unmeasured warmup pass first.

    Returns:
        0 on success, 1 on failure.
    """
    config = ModelConfig.from_env()
    if base_url:
        config.client.base_url = base_url

    print("=" * 70)
    print(" Local Model Runtime Benchmark (llama.cpp)")
    print("=" * 70)
    print(f" Target Endpoint : {config.client.base_url}")
    print(f" Model Name      : {config.server_launch.model_name}")
    print(f" Mode            : {'Streaming (SSE)' if stream else 'Standard (Non-streaming)'}")
    print(f" Thinking Mode   : {enable_thinking if enable_thinking is not None else 'Default'}")
    print(f" Max Tokens      : {max_tokens}")
    print(f" Repetitions     : {runs}")
    print("-" * 70)
    print(" Note: This benchmark measures inference throughput (tokens/sec) and")
    print(" latency. It does NOT evaluate PLC accuracy, RAG, or ladder logic.")
    print("=" * 70)

    client = LlamaCppClient(config=config)

    # 1. Connectivity Check
    print("\n[1/3] Checking server reachability...")
    try:
        health = client.check_health()
        print(f" [OK] Server is reachable at {config.client.base_url}")
        if health.get("status_code") == 503:
            print(" [WARN] Server returned HTTP 503 (Model may still be loading). Aborting benchmark.")
            return 1
    except LlamaCppConnectionError as err:
        print(f" [ERROR] Could not connect to llama.cpp server: {err}")
        print(" Troubleshooting:")
        print("  1. Verify llama-server is running on the expected host/port.")
        print("  2. Start llama-server (see README.md for instructions).")
        print("  3. Verify the base URL (default: http://127.0.0.1:8080).")
        return 1
    except LlamaCppError as err:
        print(f" [ERROR] Health check failed: {err}")
        return 1

    gen_config = GenerationConfig(
        max_tokens=max_tokens,
        stream=stream,
        enable_thinking=enable_thinking,
        reasoning_budget=0 if enable_thinking is False else None,
    )

    # 2. Warmup run (optional)
    if warmup:
        print("\n[2/3] Performing 1 unmeasured warmup pass...")
        try:
            client.generate(prompt=prompt, override_config=gen_config)
            print(" [OK] Warmup complete.")
        except Exception as err:
            print(f" [WARN] Warmup run encountered an issue: {err}")
    else:
        print("\n[2/3] Skipping warmup pass.")

    # 3. Benchmark Execution
    print(f"\n[3/3] Running {runs} benchmark iterations...")
    elapsed_times: List[float] = []
    ttft_times: List[float] = []
    tokens_per_seconds: List[float] = []
    completion_tokens_list: List[int] = []
    metrics_sources: List[str] = []

    for i in range(1, runs + 1):
        print(f"\n--- Run {i} of {runs} ---")
        try:
            if stream:
                start_time = time.perf_counter()
                ttft: Optional[float] = None
                tokens_generated = 0
                full_text = ""

                for chunk in client.stream_generate(prompt=prompt, override_config=gen_config):
                    if chunk.is_first_token and chunk.time_to_first_token is not None:
                        ttft = chunk.time_to_first_token
                    if chunk.delta:
                        tokens_generated += 1
                        full_text = chunk.cumulative_text

                total_time = time.perf_counter() - start_time
                elapsed_times.append(total_time)
                if ttft is not None:
                    ttft_times.append(ttft)

                # Streaming token count estimation / reporting
                tps = round(tokens_generated / total_time, 2) if total_time > 0 and tokens_generated > 0 else None
                if tps:
                    tokens_per_seconds.append(tps)
                    metrics_sources.append("calculated (stream tokens)")
                completion_tokens_list.append(tokens_generated)

                print(f" Elapsed Time    : {total_time:.3f} s")
                print(f" Time to 1st Tok : {f'{ttft:.3f} s' if ttft else 'Unavailable'}")
                print(f" Stream Chunks   : {tokens_generated}")
                print(f" Tokens / Sec    : {f'{tps:.2f} tps' if tps else 'Unavailable'}")

            else:
                result: GenerationResult = client.generate(
                    prompt=prompt,
                    override_config=gen_config,
                )

                elapsed_times.append(result.elapsed_seconds)
                if result.completion_tokens is not None:
                    completion_tokens_list.append(result.completion_tokens)
                if result.tokens_per_second is not None:
                    tokens_per_seconds.append(result.tokens_per_second)
                    metrics_sources.append(result.metrics_source)

                print(f" Elapsed Time    : {result.elapsed_seconds:.3f} s")
                print(f" Prompt Tokens   : {result.prompt_tokens if result.prompt_tokens is not None else 'Unavailable'}")
                print(f" Generated Tokens: {result.completion_tokens if result.completion_tokens is not None else 'Unavailable'}")
                print(f" Tokens / Sec    : {f'{result.tokens_per_second:.2f} tps' if result.tokens_per_second is not None else 'Unavailable'}")
                print(f" Metrics Source  : {result.metrics_source}")

        except LlamaCppTimeoutError as err:
            print(f" [TIMEOUT] Run {i} timed out: {err}")
        except LlamaCppError as err:
            print(f" [ERROR] Run {i} failed: {err}")

    # 4. Summary Report
    print("\n" + "=" * 70)
    print(" Benchmark Summary")
    print("=" * 70)
    successful_runs = len(elapsed_times)
    print(f" Completed Runs     : {successful_runs} / {runs}")

    if successful_runs > 0:
        avg_elapsed = statistics.mean(elapsed_times)
        min_elapsed = min(elapsed_times)
        max_elapsed = max(elapsed_times)
        print(f" Total Latency (avg): {avg_elapsed:.3f} s (min: {min_elapsed:.3f} s, max: {max_elapsed:.3f} s)")

        if ttft_times:
            avg_ttft = statistics.mean(ttft_times)
            print(f" Time to 1st Token  : {avg_ttft:.3f} s (avg)")

        if completion_tokens_list:
            avg_tokens = statistics.mean(completion_tokens_list)
            print(f" Completion Tokens  : {avg_tokens:.1f} tokens (avg)")

        if tokens_per_seconds:
            avg_tps = statistics.mean(tokens_per_seconds)
            min_tps = min(tokens_per_seconds)
            max_tps = max(tokens_per_seconds)
            primary_source = metrics_sources[0] if metrics_sources else "unavailable"
            print(f" Generation Speed   : {avg_tps:.2f} tokens/sec (min: {min_tps:.2f}, max: {max_tps:.2f})")
            print(f" Metrics Source     : {primary_source}")
        else:
            print(" Generation Speed   : Unavailable (Server did not report token counts)")
    else:
        print(" No benchmark iterations completed successfully.")

    print("=" * 70)
    client.close()
    return 0 if successful_runs == runs else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local llama.cpp model throughput and latency benchmark."
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="llama.cpp server base URL (default: from LLM_BASE_URL or http://127.0.0.1:8080)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of repetitions to run (default: 3)",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Use streaming mode and measure Time To First Token (TTFT)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum generation tokens per repetition (default: 512)",
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="Disable Qwen3 thinking/reasoning mode for concise generation",
    )
    parser.add_argument(
        "--warmup",
        action="store_true",
        help="Execute 1 unmeasured warmup run before benchmark",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=DEFAULT_NEUTRAL_PROMPT,
        help="Custom fixed neutral prompt to benchmark against",
    )

    args = parser.parse_args()

    enable_thinking = False if args.no_thinking else None
    sys.exit(
        run_benchmark(
            base_url=args.base_url,
            runs=args.runs,
            stream=args.stream,
            prompt=args.prompt,
            enable_thinking=enable_thinking,
            max_tokens=args.max_tokens,
            warmup=args.warmup,
        )
    )


if __name__ == "__main__":
    main()

