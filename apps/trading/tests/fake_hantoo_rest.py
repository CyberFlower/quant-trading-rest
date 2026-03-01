import os

from core.infra.api_recording import ApiReplay


def _default_path(env_var, filename):
    env_path = os.getenv(env_var)
    if env_path:
        return env_path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "fixtures", filename)


DEFAULT_HANTOO_ACCOUNT_BALANCE = {
    "output1": [
        {
            "pdno": "CFLT",
            "prdt_name": "컨플루언트",
            "cblc_qty13": "46.00000000",
            "avg_unpr3": "23.0756",
        },
        {
            "pdno": "GEHC",
            "prdt_name": "GE 헬스케어 테크놀로지스",
            "cblc_qty13": "12.00000000",
            "avg_unpr3": "77.5350",
        },
        {
            "pdno": "POOL",
            "prdt_name": "풀",
            "cblc_qty13": "7.00000000",
            "avg_unpr3": "320.7028",
        },
        {
            "pdno": "REGN",
            "prdt_name": "리제네론 파머슈티컬스",
            "cblc_qty13": "12.00000000",
            "avg_unpr3": "583.0175",
        },
        {
            "pdno": "EIX",
            "prdt_name": "에디슨 인터내셔널",
            "cblc_qty13": "31.00000000",
            "avg_unpr3": "55.6852",
        },
        {
            "pdno": "ELV",
            "prdt_name": "엘리밴스 헬스",
            "cblc_qty13": "3.00000000",
            "avg_unpr3": "335.2166",
        },
        {
            "pdno": "GIS",
            "prdt_name": "제너럴 밀스",
            "cblc_qty13": "25.00000000",
            "avg_unpr3": "49.4936",
        },
        {
            "pdno": "GPN",
            "prdt_name": "글로벌 페이먼츠",
            "cblc_qty13": "12.00000000",
            "avg_unpr3": "86.3787",
        },
        {
            "pdno": "IT",
            "prdt_name": "가트너",
            "cblc_qty13": "4.00000000",
            "avg_unpr3": "251.9650",
        },
        {
            "pdno": "LMT",
            "prdt_name": "록히드 마틴",
            "cblc_qty13": "1.00000000",
            "avg_unpr3": "472.8800",
        },
        {
            "pdno": "ORCL",
            "prdt_name": "오라클",
            "cblc_qty13": "2.00000000",
            "avg_unpr3": "304.7375",
        },
        {
            "pdno": "PFE",
            "prdt_name": "화이자",
            "cblc_qty13": "23.00000000",
            "avg_unpr3": "24.8165",
        },
        {
            "pdno": "SLB",
            "prdt_name": "슐럼버거",
            "cblc_qty13": "23.00000000",
            "avg_unpr3": "36.2832",
        },
        {
            "pdno": "UNH",
            "prdt_name": "유나이티드헬스 그룹",
            "cblc_qty13": "14.00000000",
            "avg_unpr3": "344.0970",
        },
        {
            "pdno": "UNP",
            "prdt_name": "유니언 퍼시픽",
            "cblc_qty13": "8.00000000",
            "avg_unpr3": "233.1443",
        },
        {
            "pdno": "UPS",
            "prdt_name": "UPS",
            "cblc_qty13": "17.00000000",
            "avg_unpr3": "95.3847",
        },
        {
            "pdno": "VZ",
            "prdt_name": "버라이존 커뮤니케이션스",
            "cblc_qty13": "6.00000000",
            "avg_unpr3": "42.9125",
        },
        {
            "pdno": "SGOV",
            "prdt_name": "ISHARES 0-3M TREASURY BOND",
            "cblc_qty13": "4.00000000",
            "avg_unpr3": "100.5269",
        },
        {
            "pdno": "XHE",
            "prdt_name": "SPDR S&P HEALTH CARE EQUIPMENT",
            "cblc_qty13": "10.00000000",
            "avg_unpr3": "82.3869",
        },
    ],
    "rt_cd": "0",
}
DEFAULT_HANTOO_AVAILABLE_CASH = {
    "output": [{"frcr_gnrl_ord_psbl_amt": "1912.240000"}],
    "rt_cd": "0",
}


class FakeHantooAccountState:
    def __init__(self, initial_cash=0.0, holdings=None):
        self.cash = float(initial_cash or 0.0)
        self.holdings = {}
        self._order_seq = 1
        self._completed_orders = []
        for item in holdings or []:
            symbol = item.get("symbol")
            if not symbol:
                continue
            qty = int(item.get("qty", 0))
            if qty <= 0:
                continue
            avg_price = float(item.get("avg_price", 0.0))
            name = item.get("name", symbol)
            self.holdings[symbol] = {
                "qty": qty,
                "avg_price": avg_price,
                "name": name,
            }

    def _next_order_id(self):
        order_id = f"FAKE{self._order_seq:06d}"
        self._order_seq += 1
        return order_id

    def apply_buy(self, symbol, quantity, price, name=None):
        total_cost = price * quantity
        if total_cost > self.cash:
            return False, None
        current = self.holdings.get(symbol)
        if current:
            new_qty = current["qty"] + quantity
            current_cost = current["avg_price"] * current["qty"]
            current["qty"] = new_qty
            current["avg_price"] = (current_cost + total_cost) / new_qty
            if name:
                current["name"] = name
        else:
            self.holdings[symbol] = {
                "qty": quantity,
                "avg_price": price,
                "name": name or symbol,
            }
        self.cash -= total_cost
        order_id = self._next_order_id()
        self._completed_orders.append(
            {
                "odno": order_id,
                "pdno": symbol,
                "sll_buy_dvsn_cd": "02",
                "ft_ccld_qty": str(quantity),
            }
        )
        return True, order_id

    def apply_sell(self, symbol, quantity, price):
        current = self.holdings.get(symbol)
        if not current or current["qty"] < quantity:
            return False, None
        current["qty"] -= quantity
        if current["qty"] <= 0:
            self.holdings.pop(symbol, None)
        self.cash += price * quantity
        order_id = self._next_order_id()
        self._completed_orders.append(
            {
                "odno": order_id,
                "pdno": symbol,
                "sll_buy_dvsn_cd": "01",
                "ft_ccld_qty": str(quantity),
            }
        )
        return True, order_id

    def as_available_cash(self):
        return {
            "output": [{"frcr_gnrl_ord_psbl_amt": f"{self.cash:.6f}"}],
            "rt_cd": "0",
        }

    def as_account_balance(self):
        output1 = []
        for symbol, item in self.holdings.items():
            output1.append(
                {
                    "ovrs_pdno": symbol,
                    "ovrs_item_name": item["name"],
                    "ovrs_cblc_qty": f"{item['qty']:.8f}",
                    "pchs_avg_pric": f"{item['avg_price']:.5f}",
                    "now_pric2": f"{item['avg_price']:.5f}",
                }
            )
        return {"output1": output1, "rt_cd": "0"}

    def pop_completed_orders(self):
        orders = list(self._completed_orders)
        self._completed_orders.clear()
        return orders


class FakeKoreaInvestment:
    def __init__(
        self,
        acc_no: str,
        record_path=None,
        account_state=None,
        initial_cash=None,
        holdings=None,
    ):
        if record_path is None:
            record_path = _default_path("HANTOO_REPLAY_PATH", "hantoo.jsonl")
        self.replay = ApiReplay(record_path)
        self.acc_no = acc_no
        self.acc_no_prefix = acc_no.split("-")[0]
        self.acc_no_postfix = acc_no.split("-")[1]
        if account_state is None:
            if initial_cash is None:
                try:
                    initial_cash = float(
                        DEFAULT_HANTOO_AVAILABLE_CASH["output"][0][
                            "frcr_gnrl_ord_psbl_amt"
                        ]
                    )
                except (KeyError, ValueError, TypeError):
                    initial_cash = 0.0
            if holdings is None:
                holdings = [
                    {
                        "symbol": item.get("ovrs_pdno") or item.get("pdno"),
                        "name": item.get("ovrs_item_name")
                        or item.get("prdt_name")
                        or item.get("ovrs_pdno")
                        or item.get("pdno"),
                        "qty": int(
                            float(
                                item.get("ovrs_cblc_qty")
                                or item.get("cblc_qty13")
                                or 0
                            )
                        ),
                        "avg_price": float(
                            item.get("pchs_avg_pric") or item.get("avg_unpr3") or 0
                        ),
                    }
                    for item in DEFAULT_HANTOO_ACCOUNT_BALANCE.get("output1", [])
                ]
            account_state = FakeHantooAccountState(initial_cash, holdings)
        self.account = account_state

    def get_oversea_available_cash(self):
        return self.account.as_available_cash()

    def fetch_usa_1m_ohlcv(self, symbol: str, excd: str, nmin: int):
        params = {"symbol": symbol, "excd": excd, "nmin": nmin}
        return self.replay.get_next("fetch_usa_1m_ohlcv", params)

    def fetch_ohlcv_usa_overesea(
        self,
        symbol: str,
        excd: str,
        timeframe: str = "D",
        end_day: str = "",
        adj_price: bool = True,
    ):
        end_day = ""
        params = {
            "symbol": symbol,
            "excd": excd,
            "timeframe": timeframe,
            "end_day": end_day,
            "adj_price": adj_price,
        }
        return self.replay.get_next("fetch_ohlcv_usa_overesea", params)

    def fetch_domestic_usa_price(self, symbol: str, excd: str) -> dict:
        params = {"symbol": symbol, "excd": excd}
        return self.replay.get_next("fetch_domestic_usa_price", params)

    def get_basic_info(self, symbol: str, excd: str):
        params = {"symbol": symbol, "excd": excd}
        return self.replay.get_next("get_basic_info", params)

    def create_oversea_order(
        self,
        side: str,
        exchange: str,
        symbol: str,
        price,
        quantity,
        order_type: str,
    ) -> dict:
        try:
            qty = int(quantity)
            px = float(price)
        except (TypeError, ValueError):
            qty = 0
            px = 0.0
        if qty <= 0 or px <= 0:
            return {"rt_cd": "1", "msg1": "INVALID_ORDER"}
        if side == "buy":
            ok, order_id = self.account.apply_buy(symbol, qty, px)
        else:
            ok, order_id = self.account.apply_sell(symbol, qty, px)
        if not ok:
            return {"rt_cd": "1", "msg1": "INSUFFICIENT_BALANCE"}
        return {"rt_cd": "0", "msg1": "OK", "output": {"ODNO": order_id}}

    def get_hoga(self, symbol: str, excd: str):
        params = {"symbol": symbol, "excd": excd}
        return self.replay.get_next("get_hoga", params)

    def check_confirmed_order(self, day=""):
        return {"rt_cd": "0", "output": self.account.pop_completed_orders()}

    def get_account_balance(self):
        return self.account.as_account_balance()
