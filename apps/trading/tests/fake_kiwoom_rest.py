import json
import os

from core.infra.api_recording import ApiReplay


def _default_path(env_var, filename):
    env_path = os.getenv(env_var)
    if env_path:
        return env_path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "fixtures", filename)


def _parse_price(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return abs(int(value))
    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if not value:
            return None
        if value[0] in "+-":
            value = value[1:]
        try:
            return abs(int(value))
        except ValueError:
            return None
    return None


def _strip_al_suffix(symbol):
    if symbol.endswith("_AL"):
        return symbol[:-3]
    return symbol


def _load_price_cache(path):
    if not path or not os.path.exists(path):
        return {}
    price_cache = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            method = item.get("method")
            params = item.get("params", {})
            response = item.get("response", {})
            symbol = params.get("symbol")
            if not symbol:
                continue
            symbol = _strip_al_suffix(symbol)
            if method == "get_stock_price_info":
                price = _parse_price(response.get("cur_prc"))
                if price is not None:
                    price_cache[symbol] = price
            elif method == "get_last_prices":
                for key in (
                    "stk_min_pole_chart_qry",
                    "stk_dt_pole_chart_qry",
                    "stk_stk_pole_chart_qry",
                ):
                    items = response.get(key)
                    if items:
                        price = _parse_price(items[0].get("cur_prc"))
                        if price is not None:
                            price_cache[symbol] = price
                        break
    return price_cache


DEFAULT_KIWOOM_CASH = 5018585
DEFAULT_KIWOOM_HOLDINGS = [
    {
        "symbol": "423160",
        "name": "KODEX KOFR금리액티브(합성)",
        "qty": 235,
        "buy_price": 110716,
    },
    {"symbol": "005380", "name": "현대차", "qty": 58, "buy_price": 219953},
    {"symbol": "271560", "name": "오리온", "qty": 58, "buy_price": 106495},
    {"symbol": "298020", "name": "효성티앤씨", "qty": 27, "buy_price": 222593},
    {"symbol": "035420", "name": "NAVER", "qty": 18, "buy_price": 276779},
    {"symbol": "133690", "name": "TIGER 미국나스닥100", "qty": 34, "buy_price": 132243},
    {"symbol": "185750", "name": "종근당", "qty": 39, "buy_price": 87377},
    {"symbol": "214150", "name": "클래시스", "qty": 60, "buy_price": 56500},
    {"symbol": "069500", "name": "KODEX 200", "qty": 85, "buy_price": 38532},
    {"symbol": "078600", "name": "대주전자재료", "qty": 43, "buy_price": 74584},
    {"symbol": "005930", "name": "삼성전자", "qty": 44, "buy_price": 59552},
    {"symbol": "298050", "name": "HS효성첨단소재", "qty": 12, "buy_price": 204292},
    {"symbol": "053800", "name": "안랩", "qty": 33, "buy_price": 60688},
    {"symbol": "039130", "name": "하나투어", "qty": 40, "buy_price": 48784},
    {"symbol": "017670", "name": "SK텔레콤", "qty": 36, "buy_price": 53950},
    {"symbol": "348210", "name": "넥스틴", "qty": 30, "buy_price": 56467},
    {"symbol": "360750", "name": "TIGER 미국S&P500", "qty": 72, "buy_price": 19799},
    {"symbol": "033100", "name": "제룡전기", "qty": 34, "buy_price": 40374},
    {"symbol": "248070", "name": "솔루엠", "qty": 68, "buy_price": 18847},
    {"symbol": "011070", "name": "LG이노텍", "qty": 6, "buy_price": 161178},
    {"symbol": "090430", "name": "아모레퍼시픽", "qty": 8, "buy_price": 124200},
    {"symbol": "137400", "name": "피엔티", "qty": 23, "buy_price": 39039},
    {"symbol": "178320", "name": "서진시스템", "qty": 34, "buy_price": 23874},
    {"symbol": "066570", "name": "LG전자", "qty": 6, "buy_price": 93000},
    {"symbol": "364980", "name": "TIGER 2차전지TOP10", "qty": 26, "buy_price": 8418},
    {"symbol": "005070", "name": "코스모신소재", "qty": 2, "buy_price": 45569},
    {"symbol": "403870", "name": "HPSP", "qty": 4, "buy_price": 32175},
    {"symbol": "085670", "name": "뉴프렉스", "qty": 2, "buy_price": 4995},
]


class FakeKiwoomAccountState:
    def __init__(self, initial_cash=0, holdings=None):
        self.cash = int(initial_cash or 0)
        self.holdings = {}
        for item in holdings or []:
            symbol = item.get("symbol")
            if not symbol:
                continue
            qty = int(item.get("qty", 0))
            if qty <= 0:
                continue
            buy_price = int(item.get("buy_price", 0))
            name = item.get("name", symbol)
            self.holdings[symbol] = {
                "qty": qty,
                "avg_price": buy_price,
                "name": name,
            }

    def apply_buy(self, symbol, quantity, price, name=None):
        total_cost = price * quantity
        if total_cost > self.cash:
            return False
        current = self.holdings.get(symbol)
        if current:
            new_qty = current["qty"] + quantity
            if new_qty <= 0:
                return False
            current_cost = current["avg_price"] * current["qty"]
            current["qty"] = new_qty
            current["avg_price"] = int((current_cost + total_cost) / new_qty)
            if name:
                current["name"] = name
        else:
            self.holdings[symbol] = {
                "qty": quantity,
                "avg_price": price,
                "name": name or symbol,
            }
        self.cash -= total_cost
        return True

    def apply_sell(self, symbol, quantity, price):
        current = self.holdings.get(symbol)
        if not current or current["qty"] < quantity:
            return False
        current["qty"] -= quantity
        if current["qty"] <= 0:
            self.holdings.pop(symbol, None)
        self.cash += price * quantity
        return True

    def as_deposit_info(self):
        return {
            "return_code": 0,
            "return_msg": "OK",
            "100stk_ord_alow_amt": str(self.cash),
        }

    def as_account_balance(self, price_lookup):
        day_bal_rt = []
        for symbol, item in self.holdings.items():
            current_price = price_lookup(symbol)
            if current_price is None:
                current_price = item["avg_price"]
            day_bal_rt.append(
                {
                    "stk_cd": symbol,
                    "stk_nm": item["name"],
                    "rmnd_qty": str(item["qty"]),
                    "buy_uv": str(item["avg_price"]),
                    "cur_prc": str(current_price),
                }
            )
        return {
            "return_code": 0,
            "return_msg": "OK",
            "day_bal_rt": day_bal_rt,
        }


class FakeKiwoomRestAPI:
    def __init__(
        self,
        record_path=None,
        price_path=None,
        account_state=None,
        initial_cash=None,
        holdings=None,
    ):
        if record_path is None:
            record_path = _default_path("KIWOOM_REPLAY_PATH", "kiwoom.jsonl")
        if price_path is None:
            price_path = _default_path("KIWOOM_PRICE_REPLAY_PATH", "kiwoom_prices.jsonl")
            if not os.path.exists(price_path):
                price_path = record_path
        if not os.path.exists(record_path) and os.path.exists(price_path):
            record_path = price_path
        self.replay = ApiReplay(record_path)
        self.price_replay = ApiReplay(price_path)
        self._replay_cache = {}
        self._price_cache = _load_price_cache(price_path)
        self._last_price_info = {}
        if account_state is None:
            if initial_cash is None:
                initial_cash = DEFAULT_KIWOOM_CASH
            if holdings is None:
                holdings = DEFAULT_KIWOOM_HOLDINGS
            account_state = FakeKiwoomAccountState(initial_cash, holdings)
        self.account = account_state

    def _get_replay(self, replay, method, params, fallback=None):
        key = (method, json.dumps(params, sort_keys=True, ensure_ascii=True))
        try:
            response = replay.get_next(method, params)
            self._replay_cache[key] = response
            return response
        except (KeyError, IndexError):
            alt_params = None
            symbol = params.get("symbol") if isinstance(params, dict) else None
            if symbol:
                base_symbol = _strip_al_suffix(symbol)
                if base_symbol != symbol:
                    alt_params = dict(params)
                    alt_params["symbol"] = base_symbol
            if alt_params is not None:
                alt_key = (
                    method,
                    json.dumps(alt_params, sort_keys=True, ensure_ascii=True),
                )
                if alt_key in self._replay_cache:
                    return self._replay_cache[alt_key]
                try:
                    response = replay.get_next(method, alt_params)
                    self._replay_cache[alt_key] = response
                    return response
                except (KeyError, IndexError):
                    pass
            if key in self._replay_cache:
                return self._replay_cache[key]
            if fallback is not None:
                return fallback
            raise

    def get_last_prices(self, symbol: str, period_unit: str, base_period: str):
        if not symbol.endswith("_AL"):
            symbol = f"{symbol}_AL"
        if period_unit in ["DAY", "WEEK"]:
            base_period = ""
        params = {
            "symbol": symbol,
            "period_unit": period_unit,
            "base_period": base_period,
        }
        response = self._get_replay(self.price_replay, "get_last_prices", params)
        price = None
        for key in (
            "stk_min_pole_chart_qry",
            "stk_dt_pole_chart_qry",
            "stk_stk_pole_chart_qry",
        ):
            items = response.get(key)
            if items:
                price = _parse_price(items[0].get("cur_prc"))
                break
        if price is not None:
            base_symbol = _strip_al_suffix(symbol)
            self._price_cache[base_symbol] = price
        return response

    def get_stock_basic_info(self, symbol: str):
        params = {"symbol": symbol}
        fallback = {
            "code": symbol,
            "name": symbol,
            "return_code": 0,
            "return_msg": "OK",
        }
        return self._get_replay(self.replay, "get_stock_basic_info", params, fallback)

    def get_stock_price_info(self, symbol):
        price = self._price_cache.get(symbol)
        if price is None:
            params = {"symbol": symbol}
            fallback = {
                "stk_cd": symbol,
                "cur_prc": "0",
                "return_code": 0,
                "return_msg": "OK",
            }
            response = self._get_replay(
                self.price_replay, "get_stock_price_info", params, fallback
            )
            if response:
                self._last_price_info[symbol] = dict(response)
            price = _parse_price(response.get("cur_prc"))
            if price is not None:
                self._price_cache[symbol] = price
            return response
        cached = dict(self._last_price_info.get(symbol, {}))
        if not cached:
            cached = {
                "stk_cd": symbol,
                "cur_prc": str(price),
                "return_code": 0,
                "return_msg": "OK",
            }
        cached["stk_cd"] = symbol
        cached["cur_prc"] = str(price)
        return cached

    def send_order(self, symbol: str, quantity: int, buy: bool, price):
        params = {
            "symbol": symbol,
            "quantity": quantity,
            "buy": buy,
            "price": price,
        }
        parsed_price = _parse_price(price)
        if parsed_price is None or parsed_price <= 0:
            return {
                "return_code": 1,
                "return_msg": "NO_PRICE",
                "params": params,
            }
        if buy:
            ok = self.account.apply_buy(symbol, int(quantity), parsed_price)
        else:
            ok = self.account.apply_sell(symbol, int(quantity), parsed_price)
        return {
            "return_code": 0 if ok else 1,
            "return_msg": "OK" if ok else "INSUFFICIENT_BALANCE",
            "params": params,
        }

    def get_hoga(self, symbol: str):
        price = self._price_cache.get(symbol)
        if price is None or price <= 0:
            return {
                "return_code": 1,
                "return_msg": "NO_PRICE",
                "stk_cd": symbol,
            }
        return {
            "return_code": 0,
            "return_msg": "OK",
            "stk_cd": symbol,
            "sel_fpr_bid": str(price),
            "buy_fpr_bid": str(price),
        }

    def get_deposit_info(self):
        return self.account.as_deposit_info()

    def get_basic_info(self, symbol: str):
        params = {"symbol": symbol}
        fallback = {
            "code": symbol,
            "name": symbol,
            "return_code": 0,
            "return_msg": "OK",
        }
        return self._get_replay(self.replay, "get_basic_info", params, fallback)

    def get_account_balance(self):
        return self.account.as_account_balance(self._price_cache.get)
