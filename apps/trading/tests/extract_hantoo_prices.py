import argparse
import json


PRICE_METHODS = {
    "fetch_usa_1m_ohlcv",
    "fetch_ohlcv_usa_overesea",
    "fetch_domestic_usa_price",
    "get_hoga",
    "get_basic_info",
}


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Extract price-related Hantoo replay data for tests."
    )
    parser.add_argument("--input", required=True, help="Input hantoo JSONL file")
    parser.add_argument("--output", required=True, help="Output JSONL file")
    parser.add_argument(
        "--symbols",
        default="",
        help="Comma-separated symbols to keep (optional)",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    symbols = {s.strip() for s in args.symbols.split(",") if s.strip()}

    kept = 0
    with open(args.input, encoding="utf-8") as fin, open(
        args.output, "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            method = item.get("method")
            if method not in PRICE_METHODS:
                continue
            params = item.get("params", {})
            symbol = params.get("symbol")
            if symbols and symbol and symbol not in symbols:
                continue
            fout.write(json.dumps(item, ensure_ascii=True) + "\n")
            kept += 1

    print(f"kept {kept} lines -> {args.output}")


if __name__ == "__main__":
    main()
