import time
import math
import requests
import json
import datetime

MIN_SLEEP_TIME = 0.05  # seconds
MAX_SLEEP_TIME = 0.5  # seconds


class KiwoomRestAPI:
    def __init__(self, api_key: str, api_secret: str, mock=False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.mock = mock
        self.sleep_time = MIN_SLEEP_TIME
        self.today = datetime.datetime.now().strftime("%Y%m%d")
        self.host = (
            "https://api.kiwoom.com" if not mock else "https://mockapi.kiwoom.com"
        )
        self.issue_access_token()

    def _sleep_with_backoff(self, response):
        if response is None or response.status_code != 200:
            self.sleep_time = min(MAX_SLEEP_TIME, self.sleep_time * 2 + 0.05)
            print("API request failed, retrying in {:.2f} seconds...".format(self.sleep_time))
        else:
            self.sleep_time = max(MIN_SLEEP_TIME, self.sleep_time / 2 - 0.01)
        time.sleep(self.sleep_time)

    def issue_access_token(self):
        endpoint = "/oauth2/token"
        url = self.host + endpoint

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
        }

        params = {
            "grant_type": "client_credentials",  # grant_type
            "appkey": self.api_key,  # 앱키
            "secretkey": self.api_secret,  # 시크릿키
        }

        response = requests.post(url, headers=headers, json=params)
        self._sleep_with_backoff(response)

        if response.status_code == 200:
            self.access_token = f"Bearer {response.json().get('token')}"
        else:
            raise Exception("Failed to issue access token: " + response.text)

    def get_last_prices(self, symbol: str, period_unit: str, base_period: str):
        endpoint = "/api/dostk/chart"
        url = self.host + endpoint

        api_id_mapper = {"MIN": "ka10080", "DAY": "ka10081", "WEEK": "ka10082"}

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": self.access_token,
            "api-id": api_id_mapper[
                period_unit
            ],  # "ka10080" for minute, "ka10081" for daily, "ka10082" for weekly
        }

        params = {}
        if period_unit == "MIN":
            params = {
                "stk_cd": symbol,
                "tic_scope": base_period,  # 분봉 단위 (1, 3, 5, 10, 15, 30, 45, 60)
                "upd_stkpc_tp": "1",
            }
        elif period_unit in ["DAY", "WEEK"]:
            params = {
                "stk_cd": symbol,
                "base_dt": base_period,  # 기준일자 YYYYMMDD
                "upd_stkpc_tp": "1",
            }

        for _ in range(5):
            response = requests.post(url, headers=headers, json=params)
            self._sleep_with_backoff(response)
            try:
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        raise Exception("Failed to fetch last prices: " + response.text)

    def get_stock_basic_info(self, symbol: str):
        endpoint = "/api/dostk/stkinfo"
        url = self.host + endpoint

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": self.access_token,
            "api-id": "ka10100",
        }

        params = {
            "stk_cd": symbol,
        }

        for _ in range(5):
            response = requests.post(url, headers=headers, json=params)
            self._sleep_with_backoff(response)
            try:
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        raise Exception("Failed to fetch stock basic info: " + response.text)

    def get_stock_price_info(self, symbol):
        endpoint = "/api/dostk/mrkcond"
        url = self.host + endpoint

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": self.access_token,
            "api-id": "ka10007",
        }

        params = {
            "stk_cd": symbol,
        }

        for _ in range(5):
            response = requests.post(url, headers=headers, json=params)
            self._sleep_with_backoff(response)
            try:
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        raise Exception("Failed to fetch stock price info: " + response.text)

    def send_order(self, symbol: str, quantity: int, buy: bool, price):
        endpoint = "/api/dostk/ordr"
        url = self.host + endpoint

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": self.access_token,
            "api-id": "kt10000" if buy else "kt10001",
        }

        order_quantity = max(int(math.ceil(float(quantity))), 0)
        order_price = ""
        if price is not None:
            order_price = str(abs(int(price)))

        params = {
            "dmst_stex_tp": "SOR" if not self.mock else "KRX",
            "stk_cd": symbol,
            "ord_qty": str(order_quantity),
            "ord_uv": order_price,
            "trde_tp": "0",
            "cond_uv": "",
        }

        for _ in range(5):
            response = requests.post(url, headers=headers, json=params)
            self._sleep_with_backoff(response)
            try:
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue

        raise Exception("Failed to send order: " + response.text)

    def get_deposit_info(self):
        endpoint = "/api/dostk/acnt"
        url = self.host + endpoint

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": self.access_token,
            "api-id": "kt00001",
        }

        params = {
            "qry_tp": "3",
        }

        for _ in range(5):
            response = requests.post(url, headers=headers, json=params)
            self._sleep_with_backoff(response)
            try:
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        raise Exception("Failed to fetch deposit info: " + response.text)

    # 주식기본정보요청
    def get_basic_info(self, symbol: str):
        endpoint = "/api/dostk/stkinfo"
        url = self.host + endpoint

        headers = {
            "Content-Type": "application/json;charset=UTF-8",  # 컨텐츠타입
            "authorization": self.access_token,  # 접근토큰
            "cont-yn": "N",  # 연속조회여부
            "api-id": "ka10001",  # TR명
        }

        params = {
            "stk_cd": symbol,  # 종목코드
        }

        for _ in range(5):
            response = requests.post(url, headers=headers, json=params)
            self._sleep_with_backoff(response)
            try:
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        raise Exception("Failed to fetch basic info: " + response.text)

    def get_account_balance(self):
        endpoint = "/api/dostk/acnt"
        url = self.host + endpoint

        headers = {
            "Content-Type": "application/json;charset=UTF-8",  # 컨텐츠타입
            "authorization": self.access_token,  # 접근토큰
            "cont-yn": "N",  # 연속조회여부
            "api-id": "ka01690",  # TR명
        }

        params = {
            "qry_dt": self.today,  # 조회일자 YYYYMMDD
        }

        for _ in range(5):
            response = requests.post(url, headers=headers, json=params)
            self._sleep_with_backoff(response)
            try:
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        raise Exception("Failed to fetch account balance: " + response.text)

    def check_confirmed_order(self, day=""):
        endpoint = "/api/dostk/acnt"
        url = self.host + endpoint

        headers = {
            "Content-Type": "application/json;charset=UTF-8",  # 컨텐츠타입
            "authorization": self.access_token,  # 접근토큰
            "cont-yn": "N",  # 연속조회여부
            "api-id": "kt00007",  # TR명
        }

        params = {
            "ord_dt": day if day != "" else self.today,  # 조회일자 YYYYMMDD
            "qry_tp": "4",
            "stk_bond_tp": "0",
            "sell_tp": "0",
            "stk_cd": "",
            "fr_ord_no": "",
            "dmst_stex_tp": "%"
        }

        for _ in range(5):
            response = requests.post(url, headers=headers, json=params)
            self._sleep_with_backoff(response)
            try:
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        raise Exception("Failed to fetch confirmed order: " + response.text)
    
    def get_hoga(self, symbol: str):
        endpoint = "/api/dostk/mrkcond"
        url = self.host + endpoint

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": self.access_token,
            "api-id": "ka10004",
        }

        params = {
            "stk_cd": symbol,
        }

        for _ in range(5):
            response = requests.post(url, headers=headers, json=params)
            self._sleep_with_backoff(response)
            try:
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue
        raise Exception("Failed to fetch hoga info: " + response.text)


# def buy_test():
# print("[send_order] 매수:")
# quantity = int(available_cash) // int(1.3 * cur_price)
# print(f"{stock_name} {quantity} {cur_price}")
# if quantity > 0:
#     print(api.send_order(symbol, str(quantity), True, cur_price))
#     time.sleep(MAX_SLEEP_TIME)

# print("[get_deposit_info]:")
# response = api.get_deposit_info()
# for _ in range(5):
#     time.sleep(MAX_SLEEP_TIME)
#     try:
#         if response["return_code"] == 0:
#             available_cash = response["100stk_ord_alow_amt"]
#             print("Available cash: {}", available_cash)
#             break
#         else:
#             print("Error fetching deposit info:", response["return_code"])
#             time.sleep(0.1)
#             response = api.get_deposit_info()
#     except Exception as e:
#         print(f"Exception occurred: {e}")
#         print("Error parsing deposit info response")
#         response = api.get_deposit_info()

# print("[send_order] 매도:")
# response = api.send_order(symbol, 1, False, cur_price)
# print(response)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Kiwoom REST API runner")
    parser.add_argument(
        "--key-file",
        default="investment_key/kiwoominvestment.key",
        help="Path to key file",
    )
    parser.add_argument("--mock", action="store_true", help="Use mock API host")
    parser.add_argument("--symbol", default="005930", help="Stock code")
    parser.add_argument(
        "--call",
        default="get_hoga",
        choices=[
            "get_hoga",
            "get_stock_price_info",
            "get_stock_basic_info",
            "get_deposit_info",
            "get_account_balance",
            "get_last_prices_min",
            "get_last_prices_day",
            "get_last_prices_week",
            "check_confirmed_order",
            "send_order",
        ],
        help="API to call",
    )
    parser.add_argument("--min-period", default="15", help="Minute period for MIN")
    parser.add_argument("--day", default="", help="YYYYMMDD for DAY/WEEK/confirmed")
    parser.add_argument("--quantity", default="1", help="Order quantity")
    parser.add_argument("--buy", action="store_true", help="Buy order")
    parser.add_argument("--price", default="", help="Order price for send_order")
    args = parser.parse_args()

    with open(args.key_file, encoding="utf-8") as f:
        lines = f.readlines()

    api_key = lines[0].strip()
    api_secret = lines[1].strip()

    api = KiwoomRestAPI(api_key, api_secret, mock=args.mock)
    if not args.day:
        args.day = datetime.datetime.now().strftime("%Y%m%d")

    if args.call == "get_hoga":
        print("[get_hoga]:")
        print(api.get_hoga(args.symbol))
    elif args.call == "get_stock_price_info":
        print("[get_stock_price_info]:")
        print(api.get_stock_price_info(args.symbol))
    elif args.call == "get_stock_basic_info":
        print("[get_stock_basic_info]:")
        print(api.get_stock_basic_info(args.symbol))
    elif args.call == "get_deposit_info":
        print("[get_deposit_info]:")
        print(api.get_deposit_info())
    elif args.call == "get_account_balance":
        print("[get_account_balance]:")
        print(api.get_account_balance())
    elif args.call == "get_last_prices_min":
        print("[get_last_prices] 분봉:")
        print(api.get_last_prices(args.symbol, "MIN", args.min_period))
    elif args.call == "get_last_prices_day":
        print("[get_last_prices] 일봉:")
        print(api.get_last_prices(args.symbol, "DAY", args.day))
    elif args.call == "get_last_prices_week":
        print("[get_last_prices] 주봉:")
        print(api.get_last_prices(args.symbol, "WEEK", args.day))
    elif args.call == "check_confirmed_order":
        print("[check_confirmed_order]:")
        print(api.check_confirmed_order(args.day))
    elif args.call == "send_order":
        if not args.price:
            raise SystemExit("send_order requires --price")
        print("[send_order]:")
        print(api.send_order(args.symbol, args.quantity, args.buy, args.price))
