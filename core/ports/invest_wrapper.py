from abc import ABC, abstractmethod

class InvestmentWrapper(ABC):
    @abstractmethod
    def connect(self, mode):
        pass

    @abstractmethod
    def get_last_prices(self, symbol, tick, input_desc):
        pass

    @abstractmethod
    def update_by_minute(self, symbol):
        pass

    @abstractmethod
    def check_and_update_stock_info(self, symbol, info):
        pass
    
    @abstractmethod
    def buy_stock_by_market_price(self, symbol, quantity):
        pass
    
    @abstractmethod
    def sell_stock_by_market_price(self, symbol, quantity):
        pass
