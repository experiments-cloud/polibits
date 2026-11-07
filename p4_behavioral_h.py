# p4_behavioral_h.py
# Human expert - Strategy

from abc import ABC, abstractmethod

# --- STRATEGY PATTERN: BUSINESS LOGIC ---
class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, price, items_count):
        pass

class RegularStrategy(DiscountStrategy):
    def calculate(self, price, items_count):
        return price * 0.95 if items_count > 10 else price

class VIPStrategy(DiscountStrategy):
    def calculate(self, price, items_count):
        return price * 0.85 if price > 1000 else price * 0.90

class StudentStrategy(DiscountStrategy):
    def calculate(self, price, items_count):
        return price * 0.80

class NoDiscountStrategy(DiscountStrategy):
    def calculate(self, price, items_count):
        return price

# --- BEHAVIORAL SYSTEM (HUMAN) ---
class BehavioralSystem:
    def __init__(self):
        self._default = NoDiscountStrategy()
        self._strategies = {
            "REGULAR": RegularStrategy(),
            "VIP": VIPStrategy(),
            "STUDENT": StudentStrategy(),
        }
        self._current_strategy = self._default

    def set_strategy_by_name(self, strategy_name):
        self._current_strategy = self._strategies.get(strategy_name, self._default)

    def process_sale(self, raw_price, items_count):
        return self._current_strategy.calculate(raw_price, items_count)
