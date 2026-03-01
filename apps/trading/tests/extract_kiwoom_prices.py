import argparse
import json


PRICE_METHODS = {
    "get_last_prices",
    "get_stock_basic_info",
    "get_stock_price_info",
}


def _strip_al_suffix(symbol):
    if symbol.endswith("_AL"):
        return symbol[:-3]
    return symbol


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Extract price-related Kiwoom replay data for tests."
    )
    parser.add_argument("--input", required=True, help="Input kiwoom JSONL file")
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
    group_meta = {}

    with open(args.input, encoding="utf-8") as fin:
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
            if symbols and symbol:
                if _strip_al_suffix(symbol) not in symbols:
                    continue
            ts = item.get("ts")
            if ts is None:
                continue
            try:
                minute_key = int(float(ts) // 60)
            except (TypeError, ValueError):
                continue
            base_symbol = _strip_al_suffix(symbol) if symbol else None
            group_key = (method, base_symbol, minute_key)
            meta = group_meta.setdefault(group_key, {"count": 0, "has_non_al": False})
            meta["count"] += 1
            if symbol and not symbol.endswith("_AL"):
                meta["has_non_al"] = True

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
            if symbols and symbol:
                if _strip_al_suffix(symbol) not in symbols:
                    continue
            ts = item.get("ts")
            if ts is not None:
                try:
                    minute_key = int(float(ts) // 60)
                except (TypeError, ValueError):
                    minute_key = None
                if minute_key is not None:
                    base_symbol = _strip_al_suffix(symbol) if symbol else None
                    group_key = (method, base_symbol, minute_key)
                    meta = group_meta.get(group_key)
                    if (
                        meta
                        and meta["count"] >= 2
                        and meta["has_non_al"]
                        and symbol
                        and symbol.endswith("_AL")
                    ):
                        continue
            fout.write(json.dumps(item, ensure_ascii=True) + "\n")
            kept += 1

    print(f"kept {kept} lines -> {args.output}")


if __name__ == "__main__":
    main()
