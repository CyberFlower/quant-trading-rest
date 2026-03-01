# Order Sheet

주문 파라미터는 `order/<broker>/*.xlsx`에서 읽습니다.

## 필수 컬럼 예시

| symbol | name | buy_1 | buy_2 | buy_3 | sell_1 | sell_2 | sell_3 | buyTick | sellTick | acc_balance |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| 005930 | 삼성전자 | 10 | 10 | 10 | 10 | 10 | 10 | DAY | DAY | 0 |
| 000660 | SK하이닉스 | 3 | 3 | 4 | 2 | 3 | 5 | MIN15 | DAY | 0 |

## 규칙

- 매수/매도는 최대 3단계(`*_1..*_3`)만 지원합니다.
- `buyTick`, `sellTick` 허용값:
  - `MIN1`, `MIN3`, `MIN5`, `MIN10`, `MIN15`, `MIN30`, `MIN45`
  - `HOUR`, `DAY`, `WEEK`, `MONTH`
- 키 파일 4번째 줄의 RP 대체 심볼은 Order Sheet에도 반드시 포함되어야 합니다.

## 동기화

- 실행 중 수량 동기화는 15분 주기로 반영됩니다.
- OpenClaw/Syncthing 등으로 xlsx를 갱신해도 같은 주기로 반영됩니다.
