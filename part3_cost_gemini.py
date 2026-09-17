"""Part 3 -- turn the measured Gemini token counts into money.

Reads measurements_gemini.json from the Gemini adaptation of Part 2 and shows:

* what one support request costs in each language;
* what a year of requests costs at a chosen volume;
* how much more Russian and Kazakh cost than English.

Gemini output cost includes thinking tokens.

Run:
    python part3_cost_gemini.py
    python part3_cost_gemini.py --requests-per-day 5000
    python part3_cost_gemini.py --output-tokens 300
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from prices_gemini import (
    MODELS,
    DEFAULT_MODEL,
    PRICE_CHECKED,
    PRICE_SOURCE,
    cost_usd,
)
from texts import LANGUAGES

DEFAULT_MEASUREMENTS = Path(__file__).with_name("measurements_gemini.json")
FALLBACK_OUTPUT_TOKENS = 300

def load_measurements(path: Path) -> Dict[str, object]:
    """Read measurements_gemini.json."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"{path.name} not found. Run part2_measure_gemini.py --call first.")
    except json.JSONDecodeError as exc:
        sys.exit(f"{path.name} is not valid JSON: {exc}")


def request_input_tokens(data: Dict[str, object], lang: str,) -> int:
    """Return measured input tokens for one real request."""
    request_tokens = data.get("request_tokens")

    if not request_tokens or lang not in request_tokens:
        sys.exit(
            f"{data.get('model_id', 'Gemini')} measurements have no "
            f"request_tokens for {lang!r}. "
            "Run part2_measure_gemini.py --call again."
        )
    return int(request_tokens[lang])


def resolve_output_tokens(billed: Optional[Dict[str, Dict[str, int]]], override: Optional[int],
                          ) -> Tuple[Dict[str, int], str]:
    """Choose output-token counts for pricing."""
    if override is not None:
        return ({lang: override for lang in LANGUAGES}, "fixed by --output-tokens",)

    if billed and all(lang in billed for lang in LANGUAGES):
        return ({lang: int(billed[lang]["output_tokens"])for lang in LANGUAGES},
                "measured in Part 2, including thinking tokens",
        )

    return ({lang: FALLBACK_OUTPUT_TOKENS for lang in LANGUAGES},"ASSUMED -- Part 2 ran without --call",)


def _header() -> str:
    return f"{'':<20}" + "".join(f"{lang.upper():>12}"for lang in LANGUAGES)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--measurements",
        type=Path,
        default=DEFAULT_MEASUREMENTS,
        help="path to measurements_gemini.json",
    )
    parser.add_argument(
        "--requests-per-day",
        type=int,
        default=2000,
        help="support volume to project (default: 2000)",
    )
    parser.add_argument(
        "--output-tokens",
        type=int,
        default=None,
        help=(
            "force one output length for all languages "
            "instead of using measured output"
        ),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=sorted(MODELS),
        help=f"Gemini model to price (default: {DEFAULT_MODEL})",
    )

    args = parser.parse_args()
    data = load_measurements(args.measurements)
    outputs, provenance = resolve_output_tokens(data.get("one_request_billed"), args.output_tokens,)

    print(f"prices from {PRICE_SOURCE}")
    print(f"checked {PRICE_CHECKED}; tokens measured on {data['model_id']}")
    print(f"answer length: {provenance}\n")

    inputs = {lang: request_input_tokens(data, lang) for lang in LANGUAGES}

    print("ONE SUPPORT REQUEST -- tokens, and cost in US cents")
    print("-" * 72)
    print(_header())
    print(f"{'input tokens':<20}" + "".join(f"{inputs[lang]:>12}" for lang in LANGUAGES))

    print(f"{'output tokens':<20}"+ "".join(f"{outputs[lang]:>12}" for lang in LANGUAGES))

    cents = [
        cost_usd(args.model,inputs[lang],outputs[lang],) * 100
        for lang in LANGUAGES
    ]

    print(f"{args.model:<20}"+ "".join(f"{value:>12.4f}" for value in cents))
    per_year = args.requests_per_day * 365
    print(f"\nAT {args.requests_per_day:,} REQUESTS/DAY -- US dollars per year")
    print("-" * 72)
    print(_header())

    yearly = [
        cost_usd(args.model,inputs[lang],outputs[lang],) * per_year
        for lang in LANGUAGES
    ]

    print(f"{args.model:<20}"+ "".join(f"{value:>12,.0f}" for value in yearly))
    print("\nTWO RATIOS THAT ARE NOT THE SAME NUMBER")
    print("-" * 72)
    print(_header())

    print(f"{'input only':<20}"+ "".join(f"{inputs[lang] / inputs['en']:>11.2f}x" for lang in LANGUAGES))

    base_bill = cost_usd(args.model, inputs["en"], outputs["en"],)

    print(f"{'total bill':<20}"+ "".join(
            f"{cost_usd(args.model, inputs[lang], outputs[lang]) / base_bill:>11.2f}x"
            for lang in LANGUAGES
        )
    )
    print(
        "\nThe first row measures input-token differences. "
        "The second is the actual projected bill and also "
        "depends on output length, including thinking tokens."
    )
    print("\nTHE NUMBER TO REMEMBER")
    print("-" * 72)

    en_year = (cost_usd(args.model, inputs["en"], outputs["en"],) * per_year)

    for lang in ("ru", "kk"):
        lang_year = (cost_usd(args.model, inputs[lang],outputs[lang],)* per_year)

        print(
            f"{lang.upper()} instead of EN on {args.model}, "
            f"same work, same volume: "
            f"${lang_year - en_year:,.0f}/year more "
            f"({lang_year / en_year:.2f}x)."
        )
    return 0

if __name__ == "__main__":
    sys.exit(main())