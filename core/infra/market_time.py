from abc import ABC, abstractmethod
from datetime import datetime

import exchange_calendars
import pytz


class MarketTimeInterface(ABC):
    @abstractmethod
    def is_exchange_available(self):
        pass

    @abstractmethod
    def is_pre_market_open(self):
        pass

    @abstractmethod
    def is_market_open(self):
        pass

    @abstractmethod
    def is_market_close(self):
        pass

    @abstractmethod
    def is_week_close(self):
        pass

    @abstractmethod
    def get_minute(self):
        pass


class KRXMarketTime(MarketTimeInterface):
    def __init__(self):
        self.market_open = False
        self.exchange_available = False

    def is_exchange_available(self):
        if self.exchange_available:
            return True
        xkrx = exchange_calendars.get_calendar("XKRX")
        if xkrx.is_session(datetime.now().strftime("%Y-%m-%d")):
            self.exchange_available = True
            return True
        return False

    def is_pre_market_open(self):
        kst = pytz.timezone("Asia/Seoul")
        current_time = datetime.now(kst)
        return current_time.hour >= 8 and current_time.hour < 9

    def is_market_open(self):
        if self.market_open:
            return True
        if not self.is_exchange_available():
            return False
        kst = pytz.timezone("Asia/Seoul")
        current_time = datetime.now(kst)
        if current_time.hour >= 9 and current_time.minute >= 0:
            self.market_open = True
            return True
        return False

    def is_market_close(self):
        if not self.is_exchange_available():
            return True
        kst = pytz.timezone("Asia/Seoul")
        current_time = datetime.now(kst)
        return (current_time.hour > 15) or (
            current_time.hour == 15 and current_time.minute >= 30
        )

    def is_market_available(self):
        if self.is_market_open() == False:
            return False
        if self.is_market_close() == True:
            return False
        return True

    def is_week_close(self):
        kst = pytz.timezone("Asia/Seoul")
        current_time_in_kst = datetime.now(kst)
        weekday = current_time_in_kst.weekday()
        if weekday in [5, 6]:
            return True
        if weekday == 4:
            return self.is_market_close()
        return False

    def get_minute(self):
        kst = pytz.timezone("Asia/Seoul")
        current_time = datetime.now(kst)
        return current_time.minute


class NasdaqMarketTime(MarketTimeInterface):
    def __init__(self):
        self.market_open = False
        self.exchange_available = False

    def is_exchange_available(self):
        if self.exchange_available:
            return True
        xnys = exchange_calendars.get_calendar("XNYS")
        nyt = pytz.timezone("America/New_York")
        current_time = datetime.now(nyt)
        if xnys.is_session(current_time.strftime("%Y-%m-%d")):
            self.exchange_available = True
            return True
        return False

    def is_pre_market_open(self):
        return False

    def is_market_open(self):
        if self.market_open:
            return True
        if not self.is_exchange_available():
            return False
        nyt = pytz.timezone("America/New_York")
        current_time = datetime.now(nyt)
        if current_time.hour >= 9 and current_time.minute >= 30:
            self.market_open = True
            return True
        return False

    def is_market_close(self):
        if not self.is_exchange_available():
            return True
        nyt = pytz.timezone("America/New_York")
        current_time = datetime.now(nyt)
        return current_time.hour >= 16

    def is_market_available(self):
        if self.is_market_open() == False:
            return False
        if self.is_market_close() == True:
            return False
        return True

    def is_week_close(self):
        nyt = pytz.timezone("America/New_York")
        current_time_in_ny = datetime.now(nyt)
        weekday = current_time_in_ny.weekday()
        if weekday in [5, 6]:
            return True
        if weekday == 4:
            return self.is_market_close()
        return False

    def get_minute(self):
        nyt = pytz.timezone("America/New_York")
        current_time = datetime.now(nyt)
        return current_time.minute
