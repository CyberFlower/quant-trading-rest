# Signals Conditions

이 디렉토리는 매수/매도 시그널 조건과 조합 팩토리를 관리합니다.

## 구조

- `signals/conditions/public/`: 공개 가능한 condition 구현
- `signals/conditions/private/`: 개인 전략 condition 구현
- `signals/conditions/factory/`: profile -> runtime 생성
- `signals/conditions/runtime/`: 공용 체인 실행 런타임

`Stock` 도메인은 condition 구현체를 직접 import하지 않고 runtime 인터페이스만 사용합니다.
체인 단위 규칙은 `gate(0 또는 1)` + `entries(1개 이상)`입니다.

## Gate vs Entry

- `gate`:
  - Order UI(`order/*.xlsx`)와 동기화 가능한 블록입니다.
  - 체인당 `0개 또는 1개`만 허용합니다.
  - 런타임 동기화(`sync_order_quantities`)는 gate에만 적용됩니다.
  - 실행 시 gate는 허용 수량(`gate_qty`)을 계산해 entry에 전달합니다.
- `entry`:
  - 실제 주문 실행 조건 블록입니다.
  - 체인당 `1개 이상`이어야 합니다.
  - 수량은 gate에서 전달받거나(entry with gate), entry 내부 런타임 로직으로 직접 결정합니다(entry without gate).
  - entry는 Order UI 동기화 대상이 아닙니다.

## Profile

profile 해석 위치: `signals/conditions/factory/registry.py`

공개 예시 profile:
- `public_example`

## 새 Public Signal 추가

1. `signals/conditions/public/`에 condition 클래스 추가
2. `signals/conditions/public/factory.py`에 profile factory 추가
3. `signals/conditions/factory/registry.py`에 profile 등록
4. `QUANT_PROFILE=<new_profile>`로 실행 확인

권장 인터페이스:
- `execute(...)`
- `settle(...)`
- `update_quantity(quantity, tick=None)`

## Example 공개 시그널

- `public/example_condition.py`
- 학습용 예시 프로필: `public_example`
- 구성:
  - gate: `ExampleQuantityGate` (order sync 수량 전달)
  - entry: `ExamplePriceCross*Entry` (MIN1 가격의 SMA 교차 시 실행)
- 실전 전략보다는 Gate/Entry 책임 분리를 보여주기 위한 샘플입니다.
