# p1_monolithic_baseline.py
import math

class MonolithicSystem:
    def __init__(self):
        self.version = "1.0 - Baseline"

    def execute_document_process(self, format_type, data):
        """Case 1: Document Processing with nested logic."""
        #print(f"--- Starting Document Processing ({format_type}) ---")
        
        # Validation and Transformation (Mixed logic)
        if not data:
            return "Error: No data"
        
        # Export simulation through massive conditional structures
        if format_type.lower() == "pdf":
            result = f"<PDF Document>{data}</PDF Document>"
        elif format_type.lower() == "json":
            result = f"{{\"data\": \"{data}\"}}"
        elif format_type.lower() == "xml":
            result = f"<xml><data>{data}</data></xml>"
        elif format_type.lower() == "csv":
            result = f"header,data\n1,{data}"
        else:
            raise ValueError("Unsupported format")
            
        #print(f"Result: {result}")
        return result

    def execute_ecommerce_discounts(self, customer_type, price, items_count):
        """Case 2: Discount Engine with multiple decision branches."""
        #print(f"\n--- Calculating Discount for: {customer_type} ---")
        
        final_price = price
        
        # Hard-coded business logic
        if customer_type == "REGULAR":
            if items_count > 10:
                final_price = price * 0.95  # 5% Volume discount
            else:
                final_price = price
        elif customer_type == "VIP":
            if price > 1000:
                final_price = price * 0.85  # 15% Premium VIP discount
            else:
                final_price = price * 0.90  # 10% Standard VIP discount
        elif customer_type == "STUDENT":
            final_price = price * 0.80      # 20% Fixed
        else:
            final_price = price
            
        #print(f"Final price: ${final_price:.2f}")
        return final_price

# Execution simulation
if __name__ == "__main__":
    system = MonolithicSystem()
    system.execute_document_process("pdf", "Research Report")
    system.execute_ecommerce_discounts("VIP", 1200, 5)