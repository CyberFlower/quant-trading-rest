# Investment Key

브로커 REST API 인증 키 파일은 이 디렉토리에 둡니다.

## 키 발급 가이드

- 키움 REST API: `https://openapi.kiwoom.com/intro/serviceInfo?dummyVal=0`
- 한투 REST API(참고): `https://m.blog.naver.com/leebisu/222704181327`

## 파일 포맷

`.key` 파일은 4줄 고정 포맷을 사용합니다.

```text
<APP_KEY>
<APP_SECRET>
<ACCOUNT_NO>
<CASH_SUBSTITUTE_RP_SYMBOL>
```

- 1번째 줄: 앱키
- 2번째 줄: 시크릿키
- 3번째 줄: 계좌번호
- 4번째 줄: 현금 대체 매도 대상으로 사용할 RP(또는 단기자금 ETF) 심볼

## 파일명 예시

- `kiwoominvestment.key`
- `kiwoomisainvestment.key`
- `koreainvestment.key`

## 보안 주의

- 절대 Git에 업로드하지 마세요.
- 파일 권한을 제한하세요(예: `chmod 600 investment_key/*.key`).
- UTF-8 텍스트, 불필요한 공백/빈 줄 없이 저장하세요.
