#!/usr/bin/env python3
"""
RKLLM CLI chat client — interactive conversation with the RKLLM server.

Communicates via OpenAI-compatible HTTP API (/v1/chat/completions).
Supports streaming and non-streaming modes.

The RKLLM server must be running first:
  python3 llm_server.py

or manually:
  python3 ~/rknn-llm-release-v1.3.0/examples/rkllm_server_demo/rkllm_server/flask_server.py \
      --rkllm_model_path ~/models/rkllm/Qwen3.5-0.8B_w4a16_g128_rk3576.rkllm \
      --target_platform rk3576

Usage:
  python3 llm_test.py                                      # interactive chat (streaming)
  python3 llm_test.py --no-stream                          # non-streaming mode
  python3 llm_test.py --prompt "你好，介绍一下自己"          # single-shot query
  python3 llm_test.py --server http://192.168.1.100:8080   # remote server
"""

import argparse
import json
import os
import readline  # enables line editing / history in input()
import sys

# requests is a lightweight dependency; install with: pip3 install requests
try:
    import requests
except ImportError:
    print("Please install requests: pip3 install requests")
    sys.exit(1)


class LLMClient:
    """Minimal OpenAI-compatible client for RKLLM Server."""

    def __init__(self, base_url="http://127.0.0.1:8080", timeout=120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.keep_alive = False
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.session.mount("http://", adapter)

    def list_models(self):
        r = self.session.get(f"{self.base_url}/v1/models", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def chat(self, messages, stream=True, temperature=0.8, top_p=0.9, top_k=1,
             max_tokens=4096, repeat_penalty=1.1, enable_thinking=False):
        """Send a chat completion request. Yields content chunks if stream=True."""
        data = {
            "model": "rkllm",
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_tokens": max_tokens,
            "repeat_penalty": repeat_penalty,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "enable_thinking": enable_thinking,
        }

        headers = {"Content-Type": "application/json", "Authorization": "not_required"}
        resp = self.session.post(
            f"{self.base_url}/v1/chat/completions",
            json=data,
            headers=headers,
            stream=stream,
            timeout=self.timeout,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Server error ({resp.status_code}): {resp.text}")

        if stream:
            for line in resp.iter_lines(decode_unicode=True):
                if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
        else:
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            yield content


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_banner(server_url, model_name):
    print()
    print("=" * 60)
    print(f"  RKLLM Chat  |  {model_name}")
    print(f"  Server: {server_url}")
    print("=" * 60)
    print()
    print("  输入问题后回车，Ctrl+C 退出")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="RKLLM CLI chat client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 llm_test.py                                          # interactive streaming
  python3 llm_test.py --no-stream                              # non-streaming
  python3 llm_test.py --prompt "你好"                           # single shot
  python3 llm_test.py --server http://192.168.1.100:8080       # remote server
  python3 llm_test.py --temperature 0.5 --max-tokens 512        # tuning
        """,
    )

    parser.add_argument("--server", default="http://127.0.0.1:8080",
                        help="RKLLM server URL (default: http://127.0.0.1:8080)")
    parser.add_argument("--prompt", default=None,
                        help="Single-shot prompt (non-interactive mode)")
    parser.add_argument("--no-stream", action="store_true",
                        help="Disable streaming (wait for full response)")
    parser.add_argument("--temperature", type=float, default=0.8,
                        help="Sampling temperature (default: 0.8)")
    parser.add_argument("--top-p", type=float, default=0.9,
                        help="Nucleus sampling threshold (default: 0.9)")
    parser.add_argument("--max-tokens", type=int, default=4096,
                        help="Max tokens to generate (default: 4096)")
    parser.add_argument("--repeat-penalty", type=float, default=1.1,
                        help="Repeat penalty (default: 1.1)")
    parser.add_argument("--enable-thinking", action="store_true",
                        help="Enable deep thinking mode (for Qwen3)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="HTTP request timeout in seconds (default: 120)")

    args = parser.parse_args()
    stream = not args.no_stream

    client = LLMClient(base_url=args.server, timeout=args.timeout)

    # Verify server connectivity
    try:
        models = client.list_models()
        model_name = models["data"][0]["id"] if models.get("data") else "rkllm"
    except Exception as e:
        print(f"Error: Cannot connect to server at {args.server}")
        print(f"  {e}")
        print()
        print("Make sure the RKLLM server is running:")
        print("  python3 llm_server.py")
        sys.exit(1)

    # -------------------------------------------------------------------
    # Single-shot mode
    # -------------------------------------------------------------------
    if args.prompt:
        messages = [{"role": "user", "content": args.prompt}]

        if stream:
            for chunk in client.chat(
                messages, stream=True, temperature=args.temperature,
                top_p=args.top_p, max_tokens=args.max_tokens,
                repeat_penalty=args.repeat_penalty,
                enable_thinking=args.enable_thinking,
            ):
                print(chunk, end="", flush=True)
            print()
        else:
            for chunk in client.chat(
                messages, stream=False, temperature=args.temperature,
                top_p=args.top_p, max_tokens=args.max_tokens,
                repeat_penalty=args.repeat_penalty,
                enable_thinking=args.enable_thinking,
            ):
                print(chunk)
        return

    # -------------------------------------------------------------------
    # Interactive mode
    # -------------------------------------------------------------------
    print_banner(args.server, model_name)
    messages = []

    try:
        while True:
            try:
                user_input = input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                break
            if user_input.lower() == "clear":
                messages.clear()
                print("  [history cleared]")
                continue

            messages.append({"role": "user", "content": user_input})

            print("AI  > ", end="", flush=True)

            try:
                if stream:
                    full_response = ""
                    for chunk in client.chat(
                        messages, stream=True, temperature=args.temperature,
                        top_p=args.top_p, max_tokens=args.max_tokens,
                        repeat_penalty=args.repeat_penalty,
                        enable_thinking=args.enable_thinking,
                    ):
                        print(chunk, end="", flush=True)
                        full_response += chunk
                    print()
                else:
                    print("...", end="", flush=True)
                    for chunk in client.chat(
                        messages, stream=False, temperature=args.temperature,
                        top_p=args.top_p, max_tokens=args.max_tokens,
                        repeat_penalty=args.repeat_penalty,
                        enable_thinking=args.enable_thinking,
                    ):
                        full_response = chunk
                    print(f"\rAI  > {full_response}")

                messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                print(f"\n  [Error] {e}")
                # Remove the user message that failed
                if messages and messages[-1]["role"] == "user":
                    messages.pop()

    except KeyboardInterrupt:
        print()

    print("Goodbye.")


if __name__ == "__main__":
    main()
