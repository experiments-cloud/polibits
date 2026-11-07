"""
adapters.py

Uniform entry points for the generated samples, built by one fixed rule so that
no sample is hand-tuned:

P2 (Factory): every sample keeps a client class with the baseline signature
  (execute_document_process(format_type, data), execute_ecommerce_discounts(
  customer_type, price, items_count)); it is instantiated with no arguments and
  those two methods are used as-is.

P4 (Strategy): the Context class is used as the prompt asked for it:
  ctx = ShoppingCartContext()            (or build_*context() if the sample provides one)
  ctx.set_strategy_by_name(name)         if that method exists, else ctx.set_strategy(name)
  ctx.calculate_total(price, items) / calculate_final_price(price, items)
"""
import importlib.util
import inspect
import sys

CLIENT_NAMES = ("execute_document_process", "execute_ecommerce_discounts")


def load(path, tag):
    name = f"sample_{tag}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


def p2_entry(mod):
    for _, cls in inspect.getmembers(mod, inspect.isclass):
        if cls.__module__ == mod.__name__ and all(hasattr(cls, n) for n in CLIENT_NAMES):
            obj = cls()
            return obj.execute_document_process, obj.execute_ecommerce_discounts
    raise LookupError("no client class with the baseline signature")


def p4_entry(mod):
    builders = [f for n, f in inspect.getmembers(mod, inspect.isfunction)
                if n.startswith("build") and "context" in n.lower() and f.__module__ == mod.__name__]
    ctx = builders[0]() if builders else mod.ShoppingCartContext()
    select = getattr(ctx, "set_strategy_by_name", None) or ctx.set_strategy
    calc = getattr(ctx, "calculate_total", None) or getattr(ctx, "calculate_final_price")

    def disc(ctype, price, items):
        select(ctype)
        return calc(price, items)
    return disc
