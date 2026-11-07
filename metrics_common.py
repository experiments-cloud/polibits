"""
metrics_common.py

Radon 6.0.1 helpers shared by the analysis scripts.
  normalize(src): code only -- comments, docstrings and the __main__ demo removed
                  (optionally one method removed, e.g. to keep the discount logic only)
  metrics(code):  cc_max_method (max CC over functions and methods, class blocks excluded),
                  cc_max_block (max over all Radon blocks), mi (Maintainability Index, 0-100), sloc
"""
import ast
import radon.complexity as cc
import radon.metrics as mm
from radon.raw import analyze
from radon.visitors import Class

def normalize(src, drop_method=None):
    tree = ast.parse(src)
    tree.body = [n for n in tree.body if not (
        isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Name) and n.test.left.id == "__name__")]
    for node in ast.walk(tree):          # drop docstrings
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)) and node.body \
                and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) \
                and isinstance(node.body[0].value.value, str) and len(node.body) > 1:
            node.body = node.body[1:]
        if drop_method and isinstance(node, ast.ClassDef):
            node.body = [n for n in node.body if not (isinstance(n, ast.FunctionDef) and n.name == drop_method)]
    return ast.unparse(tree)


def metrics(code):
    blocks = cc.cc_visit(code)
    funcs = [b.complexity for b in blocks if not isinstance(b, Class)]
    for b in blocks:
        if isinstance(b, Class):
            funcs += [m.complexity for m in b.methods]
    return {"cc_max_method": max(funcs), "cc_max_block": max(b.complexity for b in blocks),
            "mi": round(mm.mi_visit(code, multi=False), 2), "sloc": analyze(code).sloc}
