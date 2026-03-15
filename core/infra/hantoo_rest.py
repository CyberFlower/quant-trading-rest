import json
import datetime
import time
import requests
import pytz

EXCHANGE_ORDER_CODE = {"NAS": "NASD", "NYS": "NYSE", "AMS": "AMEX"}
MIN_SLEEP_TIME = 0.05  # seconds
MAX_SLEEP_TIME = 0.5  # seconds
DEFAULT_RETRY_COUNT = 5


class KoreaInvestment:
    def __init__(self, api_key: str, api_secret: str, acc_no: str, mock: bool = False):
        self.mock = mock
        self.api_key = api_key
        self.api_secret = api_secret
        self.acc_no = acc_no
        self.acc_no_prefix = acc_no.split("-")[0]
        self.acc_no_postfix = acc_no.split("-")[1]
        nyt = pytz.timezone("America/New_York")
        self.today = datetime.datetime.now(nyt).strftime("%Y%m%d")
        self.access_token = None
        self.sleep_time = MIN_SLEEP_TIME
        self.base_url = (
            "https://openapi.koreainvestment.com:9443"
            if not mock
            else "https://openapivts.koreainvestment.com:29443"
        )
        self.issue_access_token()

    def _sleep_with_backoff(self, success: bool):
        if success:
            self.sleep_time = max(MIN_SLEEP_TIME, self.sleep_time / 2 - 0.01)
        else:
            self.sleep_time = min(MAX_SLEEP_TIME, self.sleep_time * 2 + 0.05)
        time.sleep(self.sleep_time)

    def _is_success_payload(self, payload):
        if not isinstance(payload, dict):
            return True
        rt_cd = payload.get("rt_cd")
        if rt_cd is None:
            return True
        return rt_cd == "0"

    def _request_json(
        self,
        method: str,
        path: str,
        headers: dict,
        *,
        params=None,
        data=None,
        retry_count: int = DEFAULT_RETRY_COUNT,
        validate_payload=None,
    ):
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error = None

        for _ in range(retry_count):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                )
                if response.status_code == 200:
                    payload = response.json()
                    success = self._is_success_payload(payload)
                    if validate_payload is not None:
                        success = success and validate_payload(payload)
                    if success:
                        self._sleep_with_backoff(True)
                        return payload
                    last_error = payload
                else:
                    last_error = response.text
            except (requests.RequestException, ValueError) as exc:
                last_error = str(exc)

            self._sleep_with_backoff(False)

        raise Exception(
            "Hantoo request failed: method={} path={} error={}".format(
                method, path, last_error
            )
        )

    def issue_access_token(self):
        path = "oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.api_key,
            "appsecret": self.api_secret,
        }
        resp_data = self._request_json("POST", path, headers, data=json.dumps(data))
        self.access_token = f'Bearer {resp_data["access_token"]}'

    # 해외주식 주문가능금액(외화) 조회
    def get_oversea_available_cash(self):
        path = "uapi/overseas-stock/v1/trading/foreign-margin"
        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "TTTC2101R",  # 모의 투자 지원 안 함
            "custtype": "P",
        }
        params = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
        }
        return self._request_json("GET", path, headers, params=params)

    # 해외주식 분봉
    def fetch_usa_1m_ohlcv(self, symbol: str, excd: str, nmin: int):
        path = "/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "HHDFS76950200",
            "tr_cont": "",
        }
        params = {
            "auth": "",
            "excd": excd,
            "symb": symbol,
            "nmin": nmin,
            "pinc": "1",
            "next": "0",
            "nrec": "100",
            "fill": "",
            "keyb": "",
        }
        return self._request_json("GET", path, headers, params=params)

    # 해외주식 일/주/월봉
    def fetch_ohlcv_usa_overesea(
        self,
        symbol: str,
        excd: str,
        timeframe: str = "D",
        end_day: str = "",
        adj_price: bool = True,
    ):
        path = "/uapi/overseas-price/v1/quotations/dailyprice"
        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "HHDFS76240000",
        }
        timeframe_lookup = {"D": "0", "W": "1", "M": "2"}
        if end_day == "":
            end_day = self.today
        params = {
            "AUTH": "",
            "EXCD": excd,
            "SYMB": symbol,
            "GUBN": timeframe_lookup.get(timeframe, "0"),
            "BYMD": end_day,
            "MODP": 1 if adj_price else 0,
        }
        return self._request_json("GET", path, headers, params=params)

    # 해외주식 현재가
    def fetch_domestic_usa_price(self, symbol: str, excd: str) -> dict:
        path = "uapi/overseas-price/v1/quotations/price"
        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "HHDFS00000300",
        }
        params = {"auth": "", "excd": excd, "symb": symbol}
        return self._request_json("GET", path, headers, params=params)

    def get_basic_info(self, symbol: str, excd: str):
        path = "uapi/overseas-price/v1/quotations/price-detail"
        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "HHDFS76200200",
        }
        params = {"auth": "", "excd": excd, "symb": symbol}
        return self._request_json("GET", path, headers, params=params)

    # 해외주식 주문
    def create_oversea_order(
        self,
        side: str,
        exchange: str,
        symbol: str,
        price,
        quantity,
        order_type: str,
    ) -> dict:
        if not self.mock:
            tr_id = "TTTT1002U" if side == "buy" else "TTTT1006U"
        else:
            tr_id = "VTTT1002U" if side == "buy" else "VTTT1006U"
        path = "uapi/overseas-stock/v1/trading/order"
        excd = EXCHANGE_ORDER_CODE[exchange]
        ord_dvsn = "00"
        if tr_id == "TTTT1002U":
            if order_type == "00":
                ord_dvsn = "00"
            elif order_type == "LOO":
                ord_dvsn = "32"
            elif order_type == "LOC":
                ord_dvsn = "34"
        elif tr_id == "TTTT1006U":
            if order_type == "00":
                ord_dvsn = "00"
            elif order_type == "MOO":
                ord_dvsn = "31"
            elif order_type == "LOO":
                ord_dvsn = "32"
            elif order_type == "MOC":
                ord_dvsn = "33"
            elif order_type == "LOC":
                ord_dvsn = "34"
        else:
            ord_dvsn = "00"
        data = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "OVRS_EXCG_CD": excd,
            "PDNO": symbol,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0",
        }
        hashkey = self.issue_hashkey(data)
        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": tr_id,
            "hashkey": hashkey,
        }
        return self._request_json("POST", path, headers, data=json.dumps(data))

    def get_hoga(self, symbol: str, excd: str):
        path = "/uapi/overseas-price/v1/quotations/inquire-asking-price"
        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "HHDFS76200100",  # 모의투자 지원 안 함
        }
        params = {"auth": "", "excd": excd, "symb": symbol}
        return self._request_json("GET", path, headers, params=params)

    def check_confirmed_order(self, day=""):
        path = "/uapi/overseas-stock/v1/trading/inquire-ccnl"
        headers = {
            # "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "TTTS3035R" if not self.mock else "VTTT3035R",
        }
        params = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "PDNO": "%",
            "ORD_STRT_DT": day if day != "" else self.today,
            "ORD_END_DT": day if day != "" else self.today,
            "SLL_BUY_DVSN": "00",
            "CCLD_NCCS_DVSN": "00",
            "OVRS_EXCG_CD": "NASD",
            "SORT_SQN": "DS",
            "ORD_DT": "",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "CTX_AREA_NK200": "",
            "CTX_AREA_FK200": "",
        }
        return self._request_json("GET", path, headers, params=params)

    def issue_hashkey(self, data: dict):
        path = "uapi/hashkey"
        headers = {
            "content-type": "application/json",
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "User-Agent": "Mozilla/5.0",
        }
        resp = self._request_json(
            "POST",
            path,
            headers,
            data=json.dumps(data),
            validate_payload=lambda payload: "HASH" in payload,
        )
        hashkey = resp["HASH"]
        return hashkey

    def get_account_balance(self):
        path = "uapi/overseas-stock/v1/trading/inquire-balance"
        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "TTTS3012R",
            "custtype": "P",
        }
        params = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "OVRS_EXCG_CD": "NASD",
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
        }
        return self._request_json("GET", path, headers, params=params)


def basic_test(symbol, excd):
    # # 해외주식 주문가능금액(외화) 조회
    # cash_result = ki.get_oversea_available_cash()
    # print("해외주식 주문가능금액 결과:", cash_result)
    # time.sleep(0.5)  # Avoid rate limit issues

    # 해외주식 분봉 조회
    # ohlcv_result = ki.fetch_usa_1m_ohlcv(symbol, excd, 1)
    # print(f"{symbol} 1분봉 결과:", ohlcv_result)
    # # print(f"price len: {len(ohlcv_result['output2']['price'])}")
    # time.sleep(0.5)  # Avoid rate limit issues

    # 해외주식 일봉 조회
    # daily_result = ki.fetch_ohlcv_usa_overesea(symbol, excd, "D")
    # print(f"{symbol} 일봉 결과:", daily_result)
    # time.sleep(0.5)  # Avoid rate limit issues

    # 해외주식 현재가 조회
    price_result = ki.fetch_domestic_usa_price(symbol, excd)
    print(f"{symbol} 현재가 결과:", price_result)
    time.sleep(0.5)  # Avoid rate limit issues

    # # 해외주식 기본정보 조회
    # basic_info = ki.get_basic_info(symbol, excd)
    # print(f"{symbol} 기본정보 결과:", basic_info)
    # time.sleep(0.5)  # Avoid rate limit issues
    
    # #해외주식 계좌잔고 조회
    # balance_info = ki.get_account_balance()
    # print("계좌잔고 결과:", balance_info)
    # time.sleep(0.5)  # Avoid rate limit issues
    
    # ordered_info = ki.check_confirmed_order("20251229")
    # print("주문 확인 결과:", ordered_info)

def basic_order_test(symbol, excd):
    # 해외주식 현재가 조회
    price_result = ki.fetch_domestic_usa_price(symbol, excd)
    print(f"{symbol} 현재가 결과:", price_result)
    time.sleep(0.5)  # Avoid rate limit issues

    # 해외주식 주문
    total_remain = 60000.0
    quantity = int(total_remain / abs(float(price_result["output"]["last"])))
    order_result = ki.create_oversea_order(
        side="buy",
        exchange="AMS",
        symbol=symbol,
        price=abs(float(price_result["output"]["last"])),
        quantity=quantity,
        order_type="00",
    )
    print(f"{symbol} 매수 주문 결과:", order_result)
    time.sleep(0.5)  # Avoid rate limit issues


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hantoo REST API runner")
    parser.add_argument(
        "--key-file",
        default="investment_key/koreainvestment.key",
        help="Path to key file",
    )
    parser.add_argument("--mock", action="store_true", help="Use mock API host")
    parser.add_argument("--symbol", default="AAPL", help="Symbol")
    parser.add_argument("--excd", default="NAS", help="Exchange code")
    parser.add_argument(
        "--call",
        default="fetch_domestic_usa_price",
        choices=[
            "fetch_domestic_usa_price",
            "fetch_usa_1m_ohlcv",
            "fetch_ohlcv_usa_overesea",
            "get_basic_info",
            "get_oversea_available_cash",
            "get_account_balance",
            "get_hoga",
            "check_confirmed_order",
            "create_oversea_order",
        ],
        help="API to call",
    )
    parser.add_argument("--nmin", type=int, default=1, help="Minutes for 1m OHLCV")
    parser.add_argument("--timeframe", default="D", help="D/W/M timeframe")
    parser.add_argument("--end-day", default="", help="YYYYMMDD")
    parser.add_argument(
        "--adj-price", action="store_true", help="Adjust price for OHLCV"
    )
    parser.add_argument("--day", default="", help="YYYYMMDD for confirmed orders")
    parser.add_argument("--side", default="buy", help="buy or sell")
    parser.add_argument("--exchange", default="NAS", help="Order exchange code")
    parser.add_argument("--price", default="", help="Order price")
    parser.add_argument("--quantity", default="", help="Order quantity")
    parser.add_argument("--order-type", default="00", help="Order type code")
    args = parser.parse_args()

    with open(args.key_file, encoding="utf-8") as f:
        lines = f.readlines()

    api_key = lines[0].strip()
    api_secret = lines[1].strip()
    acc_no = lines[2].strip()

    ki = KoreaInvestment(api_key, api_secret, acc_no, mock=args.mock)
    time.sleep(0.5)  # Avoid rate limit issues

    if args.call == "fetch_domestic_usa_price":
        print(ki.fetch_domestic_usa_price(args.symbol, args.excd))
    elif args.call == "fetch_usa_1m_ohlcv":
        print(ki.fetch_usa_1m_ohlcv(args.symbol, args.excd, args.nmin))
    elif args.call == "fetch_ohlcv_usa_overesea":
        print(
            ki.fetch_ohlcv_usa_overesea(
                args.symbol,
                args.excd,
                timeframe=args.timeframe,
                end_day=args.end_day,
                adj_price=args.adj_price,
            )
        )
    elif args.call == "get_basic_info":
        print(ki.get_basic_info(args.symbol, args.excd))
    elif args.call == "get_oversea_available_cash":
        print(ki.get_oversea_available_cash())
    elif args.call == "get_account_balance":
        print(ki.get_account_balance())
    elif args.call == "get_hoga":
        print(ki.get_hoga(args.symbol, args.excd))
    elif args.call == "check_confirmed_order":
        print(ki.check_confirmed_order(args.day))
    elif args.call == "create_oversea_order":
        if not args.price or not args.quantity:
            raise SystemExit("create_oversea_order requires --price and --quantity")
        print(
            ki.create_oversea_order(
                side=args.side,
                exchange=args.exchange,
                symbol=args.symbol,
                price=args.price,
                quantity=args.quantity,
                order_type=args.order_type,
            )
        )
