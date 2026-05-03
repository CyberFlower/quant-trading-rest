# Order Sheet

주문 파라미터는 `order/<broker>/*.xlsx`에서 읽습니다.
종목별 condition profile은 같은 디렉토리의 `condition_profiles.toml`에서 읽습니다.

## 필수 컬럼 예시

키움용 예시:

| symbol | name | buy_1 | buy_2 | buy_3 | sell_1 | sell_2 | sell_3 | buyTick | sellTick | acc_balance |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| 005930 | 삼성전자 | 10 | 10 | 10 | 10 | 10 | 10 | DAY | DAY | 0 |
| 000660 | SK하이닉스 | 3 | 3 | 4 | 2 | 3 | 5 | MIN15 | DAY | 0 |

한투용 예시:

현재 구현 기준 한투 주문 시트는 미국 주식 기준으로 사용합니다.

| symbol | name | buy_1 | buy_2 | buy_3 | sell_1 | sell_2 | sell_3 | buyTick | sellTick | acc_balance |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| SGOV | AMS | 10 | 10 | 10 | 10 | 10 | 10 | DAY | DAY | 0 |
| AAPL | NAS | 3 | 3 | 4 | 2 | 3 | 5 | MIN15 | DAY | 0 |

## 주요 컬럼 의미

### `symbol`

- 브로커 API가 식별하는 종목 코드입니다.
- 키움 기준으로는 국내 주식 종목코드 예: `005930`
- 한투 기준으로는 해외 종목 심볼 예: `AAPL`
- 주문, 시세 조회, 잔고 조회의 기준 키로 사용됩니다.

### `name`

- 현재 구현 기준으로 이 컬럼의 의미는 브로커마다 다릅니다.
- 키움:
  - 사람이 읽는 종목명입니다.
  - 예: `삼성전자`, `SK하이닉스`
- 한투:
  - 종목명이 아니라 거래소/시장 식별값으로 사용됩니다.
  - 현재 구현 기준 미국 주식 시장 식별값입니다.
  - 예: `NAS`, `NYS`, `AMS`
- 즉, `name`은 브로커 중립적인 “표시 이름” 컬럼이 아니라, 브로커별로 필요한 보조 식별 정보를 담는 컬럼으로 이해하는 편이 맞습니다.

### `buyTick`, `sellTick`

- 전략이 차트 기반 판단을 할 때 어떤 주기의 가격 데이터를 기준으로 볼지를 지정합니다.
- 쉽게 말해 “과거 데이터를 몇 분봉/일봉/주봉 기준으로 해석할 것인가”를 정하는 값입니다.
- 예:
  - `MIN1`: 1분봉 기준으로 조건을 본다.
  - `MIN15`: 15분봉 기준으로 조건을 본다.
  - `DAY`: 일봉 기준으로 조건을 본다.
  - `WEEK`: 주봉 기준으로 조건을 본다.
- `buyTick`과 `sellTick`은 서로 다를 수 있습니다.
- 이 값은 전략이 참고하는 가격 시계열의 기준 tick을 뜻합니다.

### `acc_balance`

- 종목별 계좌 잔고 수량입니다.
- 사용자가 직접 입력하는 값이라기보다, 프로그램이 장 종료 이후 브로커를 통해 잔고를 확인하고 주문 시트에 반영하는 값입니다.
- 따라서 이 컬럼은 다음 실행이나 사후 확인을 위한 운영 정보 성격이 강합니다.

## 규칙

- 매수/매도는 최대 3단계(`*_1..*_3`)만 지원합니다.
- `buyTick`, `sellTick` 허용값:
  - `MIN1`, `MIN3`, `MIN5`, `MIN10`, `MIN15`, `MIN30`, `MIN45`
  - `HOUR`, `DAY`, `WEEK`, `MONTH`
- RP 종목은 더 이상 Order Sheet에 반드시 포함할 필요가 없습니다.
- RP 메타데이터는 `trading_profiles.toml`에서 관리하며, Order Sheet와는 독립적으로 동작합니다.
- `trading_profiles.toml`에서 `rp_symbol`, `rp_name`을 비우거나 `None`/`null` 문자열로 두면 RP 기능을 사용하지 않습니다.

## Condition Profile

`condition_profiles.toml`은 주문 시트와 같은 브로커 디렉토리에 둡니다.
파일이 없거나 종목별 설정이 없으면 `private_condition`을 사용합니다.

예:

```toml
default = "private_condition"

[kiwoom_isa.symbols]
"005930" = "private_ma_short_cycle"

[kiwoom_quant.symbols]
"000660" = "private_ma_short_cycle"
```

조회 순서:

- `<broker>_<account>.symbols.<symbol>`
- `<account>.symbols.<symbol>`
- `default`
- `private_condition`

브로커별 입력 기준:

- 키움:
  - `symbol`: 종목코드
  - `name`: 종목명
- 한투:
  - 현재 구현 기준 미국 주식용 입력입니다.
  - `symbol`: 미국 주식 심볼
  - `name`: 거래소/시장 식별값

주의:

- 현재 구현은 `name` 컬럼을 브로커에 따라 다르게 사용합니다.
- 따라서 키움용 주문 시트와 한투용 주문 시트는 같은 컬럼 이름을 쓰더라도 의미가 완전히 같지는 않습니다.
- 예제 파일은 public 저장소의 `order/kiwoom/example_order.xlsx`, `order/hantoo/example_order.xlsx`를 참고하면 됩니다.

## 동기화

- 실행 중 수량 동기화는 15분 주기로 반영됩니다.
- OpenClaw/Syncthing 등으로 장중에 사용자가 외부에서 수정이 가능합니다. 
- `acc_balance`는 장 종료 이후 프로그램이 브로커 잔고를 조회한 뒤 종목별로 갱신합니다.
