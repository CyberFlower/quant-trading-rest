# Test Framework (Record/Replay)

This folder contains fake wrappers that replay real API responses recorded during live runs.

## Modules

- `api_recording.py`: JSONL recorder/replayer used by the record REST clients and fake REST.
- `kiwoom_record_rest.py`: Kiwoom REST client with optional recording (`RECORDING_ENABLED`).
- `hantoo_record_rest.py`: Hantoo REST client with optional recording (`RECORDING_ENABLED`).
- `apps/trading/tests/fake_kiwoom_rest.py`: Fake Kiwoom REST implementation that replays recorded JSONL data.
- `apps/trading/tests/fake_hantoo_rest.py`: Fake Hantoo REST implementation that replays recorded JSONL data.
- `apps/trading/tests/fake_kiwoom_wrapper.py`: Kiwoom wrapper that uses `FakeKiwoomRestAPI`.
- `apps/trading/tests/fake_hantoo_wrapper.py`: Hantoo wrapper that uses `FakeKoreaInvestment`.
- `apps/trading/tests/run_main_fake.py`: Runs `apps.trading.main` logic with fake wrappers and a fake market clock.
- `apps/trading/tests/extract_kiwoom_prices.py`: Creates a price-only Kiwoom replay file.
- `apps/trading/tests/extract_hantoo_prices.py`: Creates a price-only Hantoo replay file.

## 1) Record live data

Record paths are set in code by default:
- `apps/trading/tests/fixtures/kiwoom.jsonl`
- `apps/trading/tests/fixtures/hantoo.jsonl`

To generate fixtures from live API responses:
1. Set `RECORDING_ENABLED = True` in:
   - `core/infra/kiwoom_record_rest.py`
   - `core/infra/hantoo_record_rest.py`
2. Run trading once per broker/account mode:
   - `python -m apps.trading.main kiwoom quant`
   - `python -m apps.trading.main hantoo quant`
3. Recorded JSONL files are appended under `apps/trading/tests/fixtures/`.

If you want to change record output paths, use env vars:
- `KIWOOM_RECORD_PATH`
- `HANTOO_RECORD_PATH`

Then run your regular command (example):

```bash
python -m apps.trading.main kiwoom quant
```

The record REST clients append responses to the JSONL files.

## 2) Replay with fake wrappers

Use the runner in this folder:

```bash
python -m apps.trading.tests.run_main_fake kiwoom test --max-loops 3
```

You can override replay files:

```bash
python -m apps.trading.tests.run_main_fake kiwoom test --kiwoom-data apps/trading/tests/fixtures/kiwoom.jsonl
python -m apps.trading.tests.run_main_fake hantoo test --hantoo-data apps/trading/tests/fixtures/hantoo.jsonl
```

Price-only replays:
- Kiwoom defaults to `apps/trading/tests/fixtures/kiwoom_prices.jsonl` (falls back to `apps/trading/tests/fixtures/kiwoom.jsonl`).
- Hantoo defaults to `apps/trading/tests/fixtures/hantoo_prices.jsonl` (falls back to `apps/trading/tests/fixtures/hantoo.jsonl`).

Trim replay files:
- Kiwoom: `python apps/trading/tests/extract_kiwoom_prices.py --input apps/trading/tests/fixtures/kiwoom.jsonl --output apps/trading/tests/fixtures/kiwoom_prices.jsonl --symbols 005930,035420`
- Hantoo: `python apps/trading/tests/extract_hantoo_prices.py --input apps/trading/tests/fixtures/hantoo.jsonl --output apps/trading/tests/fixtures/hantoo_prices.jsonl`

You can set initial fake cash/holdings with `KIWOOM_FAKE_CASH` and `KIWOOM_FAKE_HOLDINGS`
(JSON list: `[{\"symbol\":\"005930\",\"qty\":10,\"buy_price\":60000}]`).

## Notes

- Record files are JSONL (one response per line).
- Date-dependent params are normalized so replays are stable across days.
- `get_last_prices` in `apps/trading/tests/fake_kiwoom_rest.py` always appends `_AL` to the symbol to match Kiwoom price recordings.
- Hantoo account balance and available cash are seeded from constants in `apps/trading/tests/fake_hantoo_rest.py` and updated by fake orders.
- The replay runner updates `order/<invest_company>/test_order.xlsx` during the run.
