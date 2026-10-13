#!/usr/bin/env python3
"""Check status of Watcher AI providers (config + live ping).

Loads repo-root `.env`, reports selection (intelligence / LLM / embeddings),
and probes whatever is configured: Free, Ollama, Gemini, Anthropic.

Usage (from repo root or anywhere):
  uv run --directory watcher-backend python ../scripts/check-ai-providers.py
  # or, with venv already active in watcher-backend:
  python ../scripts/check-ai-providers.py

Flags:
  --no-ping     only print config (no network / LLM calls)
  --json        machine-readable summary on stdout
  --timeout N   per-request timeout seconds (default 30)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "watcher-backend"


def _load_env() -> Path | None:
    env_path = REPO_ROOT / ".env"
    try:
        from dotenv import load_dotenv
    except ImportError:
        # Minimal fallback: parse KEY=VALUE lines without python-dotenv.
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)
            return env_path
        return None
    load_dotenv(env_path if env_path.exists() else None)
    return env_path if env_path.exists() else None


def _mask(value: str | None) -> str:
    if not value:
        return "(unset)"
    if len(value) <= 8:
        return "***"
    return f"***{value[-4:]}"


def _ensure_backend_on_path() -> None:
    backend = str(BACKEND_DIR)
    if backend not in sys.path:
        sys.path.insert(0, backend)


@dataclass
class CheckResult:
    name: str
    configured: bool
    ok: bool | None
    detail: str
    latency_ms: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _print_config(resolved_tier: str) -> None:
    print("=" * 60)
    print("Watcher AI providers - config")
    print("=" * 60)
    print(f"  HARDWARE_PROFILE      : {os.getenv('HARDWARE_PROFILE') or '(auto)'}")
    print(f"  INTELLIGENCE_PROVIDER : {os.getenv('INTELLIGENCE_PROVIDER', 'auto')}")
    print(f"  resolved analysis tier: {resolved_tier}")
    print(f"  LLM_PROVIDER          : {os.getenv('LLM_PROVIDER', 'ollama')}")
    print(f"  LLM_MODEL             : {os.getenv('LLM_MODEL') or '(provider default)'}")
    print(f"  GOOGLE_API_KEY        : {_mask(os.getenv('GOOGLE_API_KEY'))}")
    print(f"  ANTHROPIC_API_KEY     : {_mask(os.getenv('ANTHROPIC_API_KEY'))}")
    print(f"  OLLAMA_BASE_URL       : {os.getenv('OLLAMA_BASE_URL') or '(unset)'}")
    print(f"  OLLAMA_MODEL          : {os.getenv('OLLAMA_MODEL', 'qwen2.5:14b')}")
    print(f"  EMBEDDING_PROVIDER    : {os.getenv('EMBEDDING_PROVIDER') or '(auto)'}")
    print(f"  RERANK_STRATEGY       : {os.getenv('RERANK_STRATEGY', 'auto')}")
    print()


async def check_free() -> CheckResult:
    return CheckResult(
        name="free",
        configured=True,
        ok=True,
        detail="rule-based FreeProvider always available (no API key)",
    )


async def check_ollama(timeout: float) -> CheckResult:
    base = (os.getenv("OLLAMA_BASE_URL") or "").strip().rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:14b").strip() or "qwen2.5:14b"
    if not base:
        return CheckResult(
            name="ollama",
            configured=False,
            ok=None,
            detail="OLLAMA_BASE_URL unset - skipped",
        )

    try:
        import httpx
    except ImportError:
        return CheckResult(
            name="ollama",
            configured=True,
            ok=False,
            detail="httpx not installed (run via: uv run --directory watcher-backend ...)",
        )

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            tags_resp = await client.get(f"{base}/api/tags")
            tags_resp.raise_for_status()
            models = [m.get("name", "") for m in tags_resp.json().get("models", [])]
            # Prefer exact / prefix match on pulled tags
            model_present = any(
                m == model or m.startswith(model + ":") or model.startswith(m)
                for m in models
            )
            if not model_present:
                # Still try generate if tags list odd; report missing model clearly
                detail_missing = f"reachable; model '{model}' not in tags ({', '.join(models) or 'none'})"
                gen = await client.post(
                    f"{base}/api/generate",
                    json={"model": model, "prompt": "ok", "stream": False, "options": {"num_predict": 4}},
                )
                latency = int((time.perf_counter() - t0) * 1000)
                if gen.status_code >= 400:
                    return CheckResult(
                        name="ollama",
                        configured=True,
                        ok=False,
                        detail=detail_missing + f"; generate HTTP {gen.status_code}",
                        latency_ms=latency,
                    )
                return CheckResult(
                    name="ollama",
                    configured=True,
                    ok=True,
                    detail=detail_missing + "; generate ok",
                    latency_ms=latency,
                )

            gen = await client.post(
                f"{base}/api/generate",
                json={
                    "model": model,
                    "prompt": "Respondé solo: ok",
                    "stream": False,
                    "options": {"num_predict": 8},
                },
            )
            latency = int((time.perf_counter() - t0) * 1000)
            if gen.status_code >= 400:
                return CheckResult(
                    name="ollama",
                    configured=True,
                    ok=False,
                    detail=f"tags ok; generate HTTP {gen.status_code}: {gen.text[:160]}",
                    latency_ms=latency,
                )
            text = (gen.json().get("response") or "").strip().replace("\n", " ")
            return CheckResult(
                name="ollama",
                configured=True,
                ok=True,
                detail=f"model={model}; generate ok ({text[:40] or 'empty'})",
                latency_ms=latency,
            )
    except Exception as e:  # noqa: BLE001 - report any probe failure
        latency = int((time.perf_counter() - t0) * 1000)
        return CheckResult(
            name="ollama",
            configured=True,
            ok=False,
            detail=f"{type(e).__name__}: {e}",
            latency_ms=latency,
        )


async def check_gemini(timeout: float) -> CheckResult:
    key = (os.getenv("GOOGLE_API_KEY") or "").strip()
    model = (os.getenv("LLM_MODEL") or "gemini-2.5-flash").strip()
    if not key:
        return CheckResult(
            name="gemini",
            configured=False,
            ok=None,
            detail="GOOGLE_API_KEY unset - skipped",
        )

    t0 = time.perf_counter()
    try:
        import google.generativeai as genai

        genai.configure(api_key=key)
        gmodel = genai.GenerativeModel(model)
        # generate_content is sync; run in thread to respect timeout roughly
        def _call() -> str:
            resp = gmodel.generate_content(
                "Respondé solo con la palabra: ok",
                generation_config={"max_output_tokens": 16, "temperature": 0},
            )
            return (getattr(resp, "text", None) or "").strip()

        text = await asyncio.wait_for(asyncio.to_thread(_call), timeout=timeout)
        latency = int((time.perf_counter() - t0) * 1000)
        return CheckResult(
            name="gemini",
            configured=True,
            ok=True,
            detail=f"model={model}; ok ({text[:40] or 'empty'})",
            latency_ms=latency,
        )
    except ImportError:
        # REST fallback without SDK
        try:
            import httpx

            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={key}"
            )
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": "Respondé solo: ok"}]}],
                        "generationConfig": {"maxOutputTokens": 16, "temperature": 0},
                    },
                )
            latency = int((time.perf_counter() - t0) * 1000)
            if resp.status_code >= 400:
                return CheckResult(
                    name="gemini",
                    configured=True,
                    ok=False,
                    detail=f"HTTP {resp.status_code}: {resp.text[:160]}",
                    latency_ms=latency,
                )
            return CheckResult(
                name="gemini",
                configured=True,
                ok=True,
                detail=f"model={model}; REST ok",
                latency_ms=latency,
            )
        except Exception as e:  # noqa: BLE001
            latency = int((time.perf_counter() - t0) * 1000)
            return CheckResult(
                name="gemini",
                configured=True,
                ok=False,
                detail=f"{type(e).__name__}: {e}",
                latency_ms=latency,
            )
    except Exception as e:  # noqa: BLE001
        latency = int((time.perf_counter() - t0) * 1000)
        msg = str(e)
        soft = "429" in msg or "Resource exhausted" in msg or "rate" in msg.lower()
        return CheckResult(
            name="gemini",
            configured=True,
            ok=bool(soft),
            detail=("rate-limited (key/reachable): " if soft else "") + f"{type(e).__name__}: {e}",
            latency_ms=latency,
        )


async def check_anthropic(timeout: float) -> CheckResult:
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    model = (os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-20241022").strip()
    if not key:
        return CheckResult(
            name="anthropic",
            configured=False,
            ok=None,
            detail="ANTHROPIC_API_KEY unset - skipped",
        )

    t0 = time.perf_counter()
    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=key)
        msg = await asyncio.wait_for(
            client.messages.create(
                model=model,
                max_tokens=16,
                messages=[{"role": "user", "content": "Respondé solo: ok"}],
            ),
            timeout=timeout,
        )
        latency = int((time.perf_counter() - t0) * 1000)
        text = ""
        if msg.content:
            block = msg.content[0]
            text = getattr(block, "text", "") or ""
        return CheckResult(
            name="anthropic",
            configured=True,
            ok=True,
            detail=f"model={model}; ok ({text.strip()[:40] or 'empty'})",
            latency_ms=latency,
        )
    except ImportError:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 16,
                        "messages": [{"role": "user", "content": "Respondé solo: ok"}],
                    },
                )
            latency = int((time.perf_counter() - t0) * 1000)
            if resp.status_code >= 400:
                return CheckResult(
                    name="anthropic",
                    configured=True,
                    ok=False,
                    detail=f"HTTP {resp.status_code}: {resp.text[:160]}",
                    latency_ms=latency,
                )
            return CheckResult(
                name="anthropic",
                configured=True,
                ok=True,
                detail=f"model={model}; REST ok",
                latency_ms=latency,
            )
        except Exception as e:  # noqa: BLE001
            latency = int((time.perf_counter() - t0) * 1000)
            return CheckResult(
                name="anthropic",
                configured=True,
                ok=False,
                detail=f"{type(e).__name__}: {e}",
                latency_ms=latency,
            )
    except Exception as e:  # noqa: BLE001
        latency = int((time.perf_counter() - t0) * 1000)
        return CheckResult(
            name="anthropic",
            configured=True,
            ok=False,
            detail=f"{type(e).__name__}: {e}",
            latency_ms=latency,
        )


def _resolve_tier() -> str:
    _ensure_backend_on_path()
    try:
        from app.services.intelligence_provider import resolve_intelligence_tier

        return resolve_intelligence_tier(os.getenv("GOOGLE_API_KEY"))
    except Exception as e:  # noqa: BLE001
        return f"(unavailable: {type(e).__name__}: {e})"


def _status_icon(r: CheckResult) -> str:
    if not r.configured:
        return "-"
    if r.ok is True:
        return "OK"
    if r.ok is False:
        return "FAIL"
    return "?"


async def run(no_ping: bool, timeout: float) -> list[CheckResult]:
    results: list[CheckResult] = [await check_free()]
    if no_ping:
        base = (os.getenv("OLLAMA_BASE_URL") or "").strip()
        results.append(
            CheckResult(
                name="ollama",
                configured=bool(base),
                ok=None,
                detail="ping skipped" if base else "OLLAMA_BASE_URL unset - skipped",
            )
        )
        results.append(
            CheckResult(
                name="gemini",
                configured=bool((os.getenv("GOOGLE_API_KEY") or "").strip()),
                ok=None,
                detail="ping skipped" if (os.getenv("GOOGLE_API_KEY") or "").strip() else "GOOGLE_API_KEY unset - skipped",
            )
        )
        results.append(
            CheckResult(
                name="anthropic",
                configured=bool((os.getenv("ANTHROPIC_API_KEY") or "").strip()),
                ok=None,
                detail="ping skipped" if (os.getenv("ANTHROPIC_API_KEY") or "").strip() else "ANTHROPIC_API_KEY unset - skipped",
            )
        )
        return results

    results.append(await check_ollama(timeout))
    results.append(await check_gemini(timeout))
    results.append(await check_anthropic(timeout))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Watcher AI provider status")
    parser.add_argument("--no-ping", action="store_true", help="Config only, no live probes")
    parser.add_argument("--json", action="store_true", help="JSON summary on stdout")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout seconds")
    args = parser.parse_args()

    env_path = _load_env()
    _ensure_backend_on_path()
    tier = _resolve_tier()

    if not args.json:
        print(f"env: {env_path or '(no .env found at repo root)'}")
        _print_config(tier)
        print("=" * 60)
        print("Probes" + (" (skipped)" if args.no_ping else ""))
        print("=" * 60)

    results = asyncio.run(run(args.no_ping, args.timeout))

    if args.json:
        payload = {
            "env": str(env_path) if env_path else None,
            "resolved_tier": tier,
            "checks": [r.to_dict() for r in results],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for r in results:
            lat = f"  {r.latency_ms} ms" if r.latency_ms is not None else ""
            print(f"  [{_status_icon(r):4}] {r.name:10} {r.detail}{lat}")
        print()

    # Exit: fail if any *configured* probe returned ok=False
    failed = [r for r in results if r.configured and r.ok is False]
    # Soft-fail when the resolved analysis tier's provider is down
    if failed:
        if not args.json:
            print(f"FAILED: {', '.join(r.name for r in failed)}")
        return 1

    # Warn (exit 0) if resolved tier is local/pro but that provider wasn't configured
    if not args.json:
        print("All configured providers OK (or skipped).")
        if isinstance(tier, str) and tier == "local" and not (os.getenv("OLLAMA_BASE_URL") or "").strip():
            print("NOTE: resolved tier is local but OLLAMA_BASE_URL is unset.")
        if isinstance(tier, str) and tier == "pro" and not (os.getenv("GOOGLE_API_KEY") or "").strip():
            print("NOTE: resolved tier is pro but GOOGLE_API_KEY is unset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
