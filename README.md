# 키움증권, 한국투자증권 제공 REST API 기반 자동매매 프로젝트

REST API 기반 자동매매 프로젝트입니다.
핵심은 `signal condition` 들을 여러 노드로 구성된 체인으로 조합해, 브로커/시장에 맞게 동일한 실행 엔진을 재사용하는 구조입니다.

## What You Can Do

- REST API 브로커(키움/한투) 기반 실시간 매매 실행
- 시그널 profile 전환 (`QUANT_PROFILE`)으로 전략 교체
- 공개 시그널을 추가해 커스텀 전략 확장

## 프로젝트 개관

- 브로커: 키움(국장), 한국투자증권(미국장)
- 실행 진입점: `apps/trading/main.py`
- 전략 전환: `QUANT_PROFILE` 환경변수
- 주문 입력: `order/<broker>/*.xlsx`
- 인증키: `investment_key/*.key`

## 빠른 시작

```bash
python3 -m pip install --upgrade pip
python3 -m pip install requests pytz pandas exchange_calendars matplotlib openpyxl
```

## 실행 전 필수 준비

프로그램 실행 전 아래 2가지는 반드시 준비되어야 합니다.

- 브로커 인증 키 파일(`investment_key/*.key`)
  - 준비 방법/포맷: `investment_key/README.md` 를 참고하세요.
- 주문 시트(`order/<broker>/*.xlsx`)
  - 컬럼/틱/제약사항: `order/README.md` 를 참고하세요.

실행 예시:

```bash
QUANT_PROFILE=public_example python -m apps.trading.main kiwoom quant
scripts/run_quant.sh kiwoom quant public_example
```

## 운영 모델

- 낮(국장) 세션: 키움증권 중심 운용
   - 국장 기준 `08:00~09:00`: 거래 주문 없이 가격 정보 업데이트만 수행
- 밤(미국장) 세션: 한국투자증권 중심 운용
- `crontab` 등 스케줄러 기반 일일 운용

## 주요 제약사항

- 매수/매도 단계는 최대 3단계로 order_ui를 통해 설정 가능
- API 과호출 시 연결 제한/해제가 발생할 수 있어 요청 간 `sleep`과 rate limit 고려 필요
- 증권사 정책(요청량/세션)은 수시로 변경될 수 있음

## Gate/Entry 체인 모델

- 이 프로젝트의 체인 단위는 `gate(0 또는 1)` + `entry(1개 이상)`입니다.
- `gate`는 Order UI 수량과 동기화되는 블록이며, 동기화는 gate에만 적용됩니다.
- `entry`는 실제 주문 실행 블록이며, 수량은 gate에서 전달받거나 entry 내부 런타임 로직에서 결정합니다. 즉, entry는 Order UI 동기화 대상이 아닙니다.
- 각 체인의 마지막 entry는 trader에 바인딩되어 실제 주문 호출을 수행합니다.
- 공개 예시 프로필(`public_example`)은 gate 1 + entry 1 구조의 최소 샘플입니다.

## 문서

- 조건 체인/프로필: `signals/conditions/README.md`
- 키 파일 포맷: `investment_key/README.md`
- 주문 파일 규칙: `order/README.md`
- 로그 경로: `output/log/README.md`

## 주의사항

이 프로젝트 사용으로 인한 모든 투자 판단, 손익, 법적/세무적 책임은 사용자 본인에게 있습니다.
작성자는 사용 결과에 대해 책임을 지지 않습니다.
