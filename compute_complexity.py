import argparse
import ast
from pathlib import Path
import re
import sympy
complexities = {}

class Visitor(ast.NodeVisitor):
    def visit_Await(self, node):
        self.generic_visit(node)

    def visit_Call(self,node):
        self.generic_visit(node)

    def visit_Name(self,node):
        self.generic_visit(node)

    def visit_Attribute(self,node):
        self.generic_visit(node)

    def visit_Module(self,node):
        self.generic_visit(node)

    def visit_ClassDef(self,node):
        self.generic_visit(node)

    def visit_Import(self,node):
        self.generic_visit(node)

    def visit_FunctionDef(self,node):
        self.generic_visit(node)

    def visit_Expr(self,node):
        self.generic_visit(node)

    def visit_For(self,node):
        self.generic_visit(node)

    def visit_BinOp(self,node):
        self.generic_visit(node)

    def visit_While(self,node):
        self.generic_visit(node)

    def visit_If(self,node):
        self.generic_visit(node)

    def visit_Break(self,node):
        self.generic_visit(node)

    def visit_Continue(self,node):
        self.generic_visit(node)

class _FunctionFinder(Visitor):
    def __init__(self):
        self.result = []

    def visit_FunctionDef(self, node):
        self.result.append(node)
        self.generic_visit(node)

class _ComplexityAnalyzer(Visitor):
    def __init__(self):
        self.input_symbols = {}
        self.result = [0]
        self.symbol_table = {}

    def visit_Assign(self, node):
        for target in node.targets:
            self.symbol_table[target.id] = self.evaluate(node.value)
        self.result[-1] += 1
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.result[-1] += 1
        self.generic_visit(node)

    def visit_If(self, node):
        self.result[-1] += 1
        self.generic_visit(node)

    def visit_Expr(self, node):
        self.result[-1] += 1

    def visit_For(self, node):
        iter = self.evaluate(node.iter)
        self.symbol_table[node.target.id] = iter.length
        assert isinstance(iter, _Iterable)
        self.result.append(0)
        self.generic_visit(node)
        inner_complexity = self.result.pop()
        iter_complexity = iter.length
        complexity = iter_complexity + 1 + iter_complexity*inner_complexity
        self.result[-1] += complexity

    def evaluate(self, expr):
        if expr is None:
            return None
        if isinstance(expr, ast.Constant):
            return expr.value
        if isinstance(expr, ast.Name):
            if expr.id in self.symbol_table:
                return self.symbol_table[expr.id]
            return self.input_symbols[expr.id]
        if isinstance(expr, ast.Expr):
            return self.evaluate(expr)
        if isinstance(expr, ast.Subscript):
            if isinstance(expr.slice, ast.Slice):
                s = expr.slice
                iterable = self.evaluate(expr.value)
                start = self.evaluate(s.lower)
                stop = self.evaluate(s.upper)
                step = self.evaluate(s.step)
                return compute_slice(iterable, start, stop, step)
            raise Exception()
        if isinstance(expr, ast.UnaryOp):
            if isinstance(expr.op, ast.USub):
                return -self.evaluate(expr.operand)
            return self.evaluate(expr.operand)

        if isinstance(expr, ast.BinOp):
            if isinstance(expr.op, ast.Mult):
                return self.evaluate(expr.left) * self.evaluate(expr.right)
            if isinstance(expr.op, ast.Div):
                return self.evaluate(expr.left) / self.evaluate(expr.right)
            if isinstance(expr.op, ast.Sub):
                return self.evaluate(expr.left) - self.evaluate(expr.right)
            if isinstance(expr.op, ast.Add):
                return self.evaluate(expr.left) + self.evaluate(expr.right)
            if isinstance(expr.op, ast.Mod):
                return self.evaluate(expr.left) % self.evaluate(expr.right)
            if isinstance(expr.op, ast.Pow):
                return self.evaluate(expr.left) ** self.evaluate(expr.right)

        if isinstance(expr, ast.Call):
            if expr.func.id == "len":
                return self.evaluate(expr.args[0]).length
            if expr.func.id == "range":
                args = [self.evaluate(arg) for arg in expr.args]
                return compute_range(*args)
        else:
            raise Exception("Unknown Type: ", expr)

    def analyze(self, node):
        assert isinstance(node, ast.FunctionDef)
        node.args._fields
        posonlyargs = node.args.posonlyargs or []
        args = node.args.args or []
        vararg = node.args.vararg or []
        kwonlyargs = node.args.kwonlyargs or []
        kwarg = node.args.kwarg or []
        all_args = posonlyargs + args + vararg + kwonlyargs + kwarg
        for arg in all_args:
            if arg.annotation.id in ("list", "dict", "str", "set", "tuple"):
                self.input_symbols[arg.arg] = _Iterable(sympy.Symbol(f"n_{arg.arg}"))
            else:
                self.input_symbols[arg.arg] = sympy.Symbol(f"n_{arg.arg}")
        self.generic_visit(node)
        assert len(self.result) == 1
        return self.result[0]

def compute_slice(iterable, start, stop, step):
    start = start or 0
    stop = stop or iterable.length
    step = step or 1
    if abs(step) == 1:
        return _Iterable((stop-start)/step)
    return _Iterable(sympy.ceiling((stop-start)/step))

def compute_range(start, stop=None, step=1):
    if stop is None:
        stop = start
        start = 0
    if abs(step) == 1:
        return _Iterable((stop-start)/step)
    return _Iterable(sympy.ceiling((stop-start)/step))

class _Iterable():
    def __init__(self, length):
        self.length = length

    def __repr__(self):
        return f"_Iterable(self.length)"

def read_program(path: Path):
    with open(path) as f:
        program = f.read()
    return ast.parse(program)

def find_functions(tree):
    finder = _FunctionFinder()
    finder.visit(tree)
    return finder.result

def compute_complexity(func_def):
    analyzer = _ComplexityAnalyzer()
    complexity = analyzer.analyze(func_def)
    try:
        complexity = complexity.expand()
        terms = re.split(r"[+-]", str(complexity))
        big_o = str(sympy.simplify("+".join(terms))).split('+')[0]
        print("Replacing", big_o)
        big_o = re.sub(r"^[^a-zA-Z]*", "", big_o)
        if big_o.isdigit():
            big_o = "1"
    except:
        big_o = "1"
    big_o = sympy.simplify(big_o)

    return complexity, big_o

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="The path to the Python file to evaluate.")
    config = parser.parse_args()

    tree = read_program(config.path)
    functions = find_functions(tree)
    for function in functions:
        gr, bo = compute_complexity(function)
        print(function.name)
        print(f"Growth Rate Function: {gr}", f"O({bo})", sep="\n")
        print()

if __name__ == "__main__":
    main()