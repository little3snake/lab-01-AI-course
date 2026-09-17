"""Part 2 adapted for Gemini API.

Does two things:

1. Counts tokens for every text in texts.py in EN/RU/KK.
2. With --call, sends one real support request per language and records
   actual Gemini API usage.

Results are written to measurements_gemini.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from texts import CORPUS, LANGUAGES


load_dotenv()

#OUTPUT_PATH = Path(__file__).with_name("measurements_gemini.json")
OUTPUT_PATH = Path(__file__).with_name("measurements.json")

# Keep output bounded so one accidental long answer does not consume
# unnecessary quota.
MAX_OUTPUT_TOKENS = 2048

# Use the same model for token measurement and real requests.
DEFAULT_MODEL = "gemini-3.8-flash"


def count_tokens(client: genai.Client, model_id: str, text: str) -> int:
    """Count Gemini tokens for one text."""
    result = client.models.count_tokens(model=model_id, contents=text,)
    return int(result.total_tokens)


def one_real_request(client: genai.Client, model_id: str, lang: str,) -> Optional[Dict[str, int]]:
    """Send system prompt + complaint and return actual API token usage."""
    response = client.models.generate_content(
        model=model_id,
        contents=CORPUS["complaint"][lang],
        config=types.GenerateContentConfig(
            system_instruction=CORPUS["system_prompt"][lang],
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2,
        ),
    )

    print("  --- answer ---")
    if response.text: print("  " + response.text.replace("\n", "\n  "))
    else: print("  [no text response]")

    usage = response.usage_metadata

    if usage is None:
        print("  no usage metadata returned")
        return None

    input_tokens = int(usage.prompt_token_count or 0)
    visible_output_tokens = int(usage.candidates_token_count or 0)
    thinking_tokens = int(getattr(usage, "thoughts_token_count", 0) or 0)

    # Gemini reports reasoning/thinking separately when applicable.
    # Keep both visible output and total generated-token usage for analysis.
    total_output_tokens = visible_output_tokens + thinking_tokens

    print(f"  input tokens: {input_tokens}")
    print(f"  visible output tokens: {visible_output_tokens}")

    if thinking_tokens: print(f"  thinking tokens: {thinking_tokens}")

    print(f"  total output tokens: {total_output_tokens}")

    return {
        "input_tokens": input_tokens,
        "output_tokens": total_output_tokens,
        "visible_output_tokens": visible_output_tokens,
        "thinking_tokens": thinking_tokens,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model id (default: {DEFAULT_MODEL})",
    )

    parser.add_argument(
        "--call",
        action="store_true",
        help="also answer the complaint in each language",
    )

    args = parser.parse_args()
    model_id = args.model

    try:
        client = genai.Client()
    except Exception as exc:
        print(f"could not build Gemini client: {exc}", file=sys.stderr)
        print("check GEMINI_API_KEY in .env", file=sys.stderr)
        return 1

    counts: Dict[str, Dict[str, int]] = {}

    print(f"counting tokens on {model_id}")

    try:
        for item_id, versions in CORPUS.items():
            counts[item_id] = {
                lang: count_tokens(client, model_id, versions[lang])
                for lang in LANGUAGES
            }

            row = "  ".join(
                f"{lang}={counts[item_id][lang]}"
                for lang in LANGUAGES
            )
            print(f"  {item_id:<18} {row}")

    except Exception as exc:
        print(f"Gemini API error while counting tokens: {exc}", file=sys.stderr)
        return 1

    billed: Dict[str, Dict[str, int]] = {}

    if args.call:
        print(
            f"\nanswering the same complaint on {model_id}, "
            "in each language:"
        )

        for lang in LANGUAGES:
            print(f"\n[{lang}]")

            try:
                result = one_real_request(client, model_id, lang,)
            except Exception as exc:
                print(
                    f"Gemini API error for {lang}: {exc}",
                    file=sys.stderr,
                )
                return 1

            if result is not None:
                billed[lang] = result

    # For Gemini, the most reliable "real request" input token count
    # comes from usage_metadata of the actual generated request.
    request_tokens = {
        lang: billed[lang]["input_tokens"]
        for lang in billed
    } if billed else None

    payload = {
        "provider": "google",
        "model": model_id,
        "model_id": model_id,
        "token_counts": counts,
        "request_tokens": request_tokens,
        "one_request_billed": billed or None,
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nwrote {OUTPUT_PATH.name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())