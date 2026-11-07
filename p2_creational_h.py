# p2_creational_h.py
# Human expert - Factory Method 

from abc import ABC, abstractmethod

# --- CASE 1: DOCUMENT INFRASTRUCTURE ---

class Document(ABC):
    @abstractmethod
    def export(self, data):
        pass

class PDFDocument(Document):
    def export(self, data):
        return f"<PDF Document>{data}</PDF Document>"

class JSONDocument(Document):
    def export(self, data):
        return f"{{\"data\": \"{data}\"}}"

class XMLDocument(Document):
    def export(self, data):
        return f"<xml><data>{data}</data></xml>"

class CSVDocument(Document):
    def export(self, data):
        return f"header,data\n1,{data}"

class DocumentFactory:
    """Factory Method for Documents"""
    _formats = {
        "pdf": PDFDocument,
        "json": JSONDocument,
        "xml": XMLDocument,
        "csv": CSVDocument,
    }

    @staticmethod
    def get_document(format_type):
        target_class = DocumentFactory._formats.get(format_type.lower())
        if not target_class:
            raise ValueError("Unsupported format")
        return target_class()

# --- CASE 2: E-COMMERCE INFRASTRUCTURE ---

class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, price, items_count):
        pass

class RegularDiscount(DiscountStrategy):
    def calculate(self, price, items_count):
        return price * 0.95 if items_count > 10 else price

class VIPDiscount(DiscountStrategy):
    def calculate(self, price, items_count):
        return price * 0.85 if price > 1000 else price * 0.90

class StudentDiscount(DiscountStrategy):
    def calculate(self, price, items_count):
        return price * 0.80

class NoDiscount(DiscountStrategy):
    def calculate(self, price, items_count):
        return price

class DiscountFactory:
    """Factory Method for Discounts"""
    _types = {
        "REGULAR": RegularDiscount,
        "VIP": VIPDiscount,
        "STUDENT": StudentDiscount,
    }

    @staticmethod
    def get_discount(customer_type):
        return DiscountFactory._types.get(customer_type, NoDiscount)()

# --- REFACTORED SYSTEM (THE CLIENT) ---

class CreationalSystem:
    def __init__(self):
        self.version = "2.0 - Creational"

    def execute_document_process(self, format_type, data):
        if not data:
            return "Error: No data"
        doc = DocumentFactory.get_document(format_type)
        return doc.export(data)

    def execute_ecommerce_discounts(self, customer_type, price, items_count):
        strategy = DiscountFactory.get_discount(customer_type)
        return strategy.calculate(price, items_count)
