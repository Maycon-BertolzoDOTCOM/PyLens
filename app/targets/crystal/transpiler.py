"""
Transpiler Python para Crystal

Suporta:
- List comprehensions → .map/.select/.each
- Decorators → Crystal macros
- f-strings → interpolação Crystal (#{expr})
- Classes → class/end
- Try/except → begin/rescue/ensure/end
- With statements → File.open do |f|; end
- Lambda → blocks {|x| x + 1}
- Type hints → Crystal types
- Async/await → spawn + channels
- Yield → yield
"""

import ast
from typing import Dict, List, Optional, Tuple


# Mapeamento de tipos Python para Crystal
PYTHON_TO_CRYSTAL_TYPES = {
    "int": "Int32",
    "float": "Float64",
    "str": "String",
    "bool": "Bool",
    "list": "Array",
    "dict": "Hash",
    "tuple": "Tuple",
    "set": "Set",
    "None": "Nil",
    "Any": "Nil",
}


class Transpiler:
    """Transpiler Python para Crystal"""

    def __init__(self):
        self.supported_constructs = {
            "For": "for loops",
            "While": "while loops",
            "Assign": "variable assignment",
            "Expr": "expressions",
            "Call": "function calls",
            "BinOp": "binary operations",
            "ListComp": "list comprehensions",
            "DecoratedFunctionDef": "decorators",
            "JoinedStr": "f-strings",
            "ClassDef": "classes",
            "Try": "try/except",
            "With": "with statements",
            "Lambda": "lambdas",
            "FunctionDefWithTypeHints": "type hints",
            "AsyncFunctionDef": "async/await",
            "Yield": "yield",
        }

        self.python_to_crystal = {
            "print": "puts",
            "range": "Range",
            "len": "size",
            "sum": "sum",
            "str": "to_s",
            "int": "to_i",
            "float": "to_f",
            "abs": "abs",
            "min": "min",
            "max": "max",
            "sorted": "sort",
            "reversed": "reverse",
            "enumerate": "each_with_index",
            "zip": "zip",
            "map": "map",
            "filter": "select",
            "any": "any?",
            "all": "all?",
            "isinstance": "is_a?",
            "type": "class",
        }

    def transpile(self, python_code: str) -> str:
        """
        Transpilar código Python para Crystal

        Args:
            python_code: código Python para transpilar

        Returns:
            str: código Crystal transpilado
        """
        try:
            tree = ast.parse(python_code)
            crystal_code = self._transpile_node(tree)

            return self._wrap_crystal_code(crystal_code)

        except Exception as e:
            raise TranspilerError(f"Transpilation failed: {e}")

    def _transpile_node(self, node: ast.AST) -> str:
        """Transpilar nó AST específico"""

        if isinstance(node, ast.Module):
            return "\n".join([self._transpile_node(stmt) for stmt in node.body])

        elif isinstance(node, ast.For):
            return self._transpile_for_loop(node)

        elif isinstance(node, ast.While):
            return self._transpile_while_loop(node)

        elif isinstance(node, ast.If):
            return self._transpile_if(node)

        elif isinstance(node, ast.FunctionDef):
            if node.decorator_list:
                return self._transpile_decorated_function(node)
            return self._transpile_function_def(node)

        elif isinstance(node, ast.AsyncFunctionDef):
            return self._transpile_async_function(node)

        elif isinstance(node, ast.Return):
            if node.value is None:
                return "return"
            return f"return {self._transpile_node(node.value)}"

        elif isinstance(node, ast.Assign):
            return self._transpile_assignment(node)

        elif isinstance(node, ast.AugAssign):
            target = self._transpile_node(node.target)
            value = self._transpile_node(node.value)
            op = self._transpile_operator(node.op)
            return f"{target} {op}= {value}"

        elif isinstance(node, ast.Expr):
            return self._transpile_expression(node)

        elif isinstance(node, ast.Call):
            return self._transpile_function_call(node)

        elif isinstance(node, ast.BinOp):
            left = self._transpile_node(node.left)
            right = self._transpile_node(node.right)
            op = self._transpile_operator(node.op)
            return f"{left} {op} {right}"

        elif isinstance(node, ast.Compare):
            left = self._transpile_node(node.left)
            parts = [left]
            for op, comp in zip(node.ops, node.comparators):
                parts.append(self._transpile_cmp_operator(op))
                parts.append(self._transpile_node(comp))
            return " ".join(parts)

        elif isinstance(node, ast.BoolOp):
            op = " && " if isinstance(node.op, ast.And) else " || "
            return op.join(self._transpile_node(v) for v in node.values)

        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return f"!{self._transpile_node(node.operand)}"
            elif isinstance(node.op, ast.USub):
                return f"-{self._transpile_node(node.operand)}"
            return self._transpile_node(node.operand)

        elif isinstance(node, ast.Name):
            name_map = {"True": "true", "False": "false", "None": "nil"}
            return name_map.get(node.id, node.id)

        elif isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "true" if node.value else "false"
            if node.value is None:
                return "nil"
            if isinstance(node.value, str):
                escaped = node.value.replace("\\", "\\\\").replace('"', '\\"')
                return f'"{escaped}"'
            return str(node.value)

        elif isinstance(node, ast.Attribute):
            obj = self._transpile_node(node.value)
            return f"{obj}.{node.attr}"

        elif isinstance(node, ast.Subscript):
            obj = self._transpile_node(node.value)
            idx = self._transpile_node(node.slice)
            return f"{obj}[{idx}]"

        elif isinstance(node, ast.List):
            elements = ", ".join(self._transpile_node(e) for e in node.elts)
            return f"[{elements}]"

        elif isinstance(node, ast.Tuple):
            elements = ", ".join(self._transpile_node(e) for e in node.elts)
            return f"{{{elements}}}"

        elif isinstance(node, ast.Dict):
            pairs = []
            for key, value in zip(node.keys, node.values):
                k = self._transpile_node(key)
                v = self._transpile_node(value)
                pairs.append(f"{k} => {v}")
            return "{" + ", ".join(pairs) + "}"

        elif isinstance(node, ast.Set):
            elements = ", ".join(self._transpile_node(e) for e in node.elts)
            return "Set{" + elements + "}"

        elif isinstance(node, ast.ListComp):
            return self._transpile_list_comprehension(node)

        elif isinstance(node, ast.SetComp):
            return self._transpile_set_comprehension(node)

        elif isinstance(node, ast.DictComp):
            return self._transpile_dict_comprehension(node)

        elif isinstance(node, ast.GeneratorExp):
            return self._transpile_generator_exp(node)

        elif isinstance(node, ast.Lambda):
            return self._transpile_lambda(node)

        elif isinstance(node, ast.JoinedStr):
            return self._transpile_fstring(node)

        elif isinstance(node, ast.Try):
            return self._transpile_try(node)

        elif isinstance(node, ast.With):
            return self._transpile_with(node)

        elif isinstance(node, ast.AsyncWith):
            return self._transpile_with(node)

        elif isinstance(node, ast.ClassDef):
            return self._transpile_class(node)

        elif isinstance(node, ast.Yield):
            return self._transpile_yield(node)

        elif isinstance(node, ast.YieldFrom):
            return self._transpile_yield_from(node)

        elif isinstance(node, ast.Pass):
            return "# pass"

        elif isinstance(node, ast.Break):
            return "break"

        elif isinstance(node, ast.Continue):
            return "next"

        elif isinstance(node, ast.Global):
            return f"# global {', '.join(node.names)}"

        elif isinstance(node, ast.Nonlocal):
            return f"# nonlocal {', '.join(node.names)}"

        elif isinstance(node, ast.Assert):
            test = self._transpile_node(node.test)
            msg = f'"{self._transpile_node(node.msg)}"' if node.msg else ""
            return f"raise AssertionError.new({msg}) unless {test}"

        elif isinstance(node, ast.Delete):
            targets = ", ".join(self._transpile_node(t) for t in node.targets)
            return f"{targets} = nil"

        else:
            return f"# TODO: Transpile {type(node).__name__}"

    def _transpile_for_loop(self, node: ast.For) -> str:
        """Transpilar loop for"""
        target = self._transpile_node(node.target)
        iter_node = node.iter

        # Converter range() para sintaxe Crystal
        if (
            isinstance(iter_node, ast.Call)
            and isinstance(iter_node.func, ast.Name)
            and iter_node.func.id == "range"
        ):
            args = iter_node.args
            if len(args) == 1:
                n = self._transpile_node(args[0])
                iterable = f"(0...{n})"
            elif len(args) == 2:
                start = self._transpile_node(args[0])
                stop = self._transpile_node(args[1])
                iterable = f"({start}...{stop})"
            else:
                start = self._transpile_node(args[0])
                stop = self._transpile_node(args[1])
                step = self._transpile_node(args[2])
                iterable = f"({start}...{stop}).step({step})"
        elif isinstance(iter_node, ast.Call) and isinstance(iter_node.func, ast.Name):
            func_name = self.python_to_crystal.get(iter_node.func.id, iter_node.func.id)
            args = ", ".join(self._transpile_node(a) for a in iter_node.args)
            iterable = f"{func_name}({args})"
        else:
            iterable = self._transpile_node(iter_node)

        body = "\n".join([f"  {self._transpile_node(stmt)}" for stmt in node.body])
        return f"{iterable}.each do |{target}|\n{body}\nend"

    def _transpile_while_loop(self, node: ast.While) -> str:
        """Transpilar loop while"""
        condition = self._transpile_node(node.test)
        body = "\n".join([f"  {self._transpile_node(stmt)}" for stmt in node.body])
        return f"while {condition}\n{body}\nend"

    def _transpile_if(self, node: ast.If) -> str:
        """Transpilar if/elif/else"""
        condition = self._transpile_node(node.test)
        body = "\n".join([f"  {self._transpile_node(stmt)}" for stmt in node.body])
        result = f"if {condition}\n{body}"

        orelse = node.orelse
        while orelse:
            if len(orelse) == 1 and isinstance(orelse[0], ast.If):
                elif_node = orelse[0]
                elif_cond = self._transpile_node(elif_node.test)
                elif_body = "\n".join([f"  {self._transpile_node(s)}" for s in elif_node.body])
                result += f"\nelsif {elif_cond}\n{elif_body}"
                orelse = elif_node.orelse
            else:
                else_body = "\n".join([f"  {self._transpile_node(s)}" for s in orelse])
                result += f"\nelse\n{else_body}"
                orelse = []

        result += "\nend"
        return result

    def _transpile_function_def(self, node: ast.FunctionDef) -> str:
        """Transpilar definição de função"""
        name = node.name
        args = self._transpile_args(node.args)
        return_type = self._transpile_return_annotation(node.returns)

        body = "\n".join([f"  {self._transpile_node(stmt)}" for stmt in node.body])

        if return_type:
            return f"def {name}({args}) : {return_type}\n{body}\nend"
        return f"def {name}({args})\n{body}\nend"

    def _transpile_async_function(self, node: ast.AsyncFunctionDef) -> str:
        """Transpilar função assíncrona para spawn"""
        name = node.name
        args = self._transpile_args(node.args)
        body = "\n".join([f"  {self._transpile_node(stmt)}" for stmt in node.body])

        return f"def {name}({args})\n  spawn do\n{body}\n  end\nend"

    def _transpile_decorated_function(self, node: ast.FunctionDef) -> str:
        """Transpilar função com decorator para Crystal macro"""
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)

        func_def = self._transpile_function_def(node)

        # Gerar macro Crystal para cada decorator
        macro_defs = []
        for dec_name in decorators:
            macro_defs.append(f"macro {dec_name}(\\#{{method}})")
            macro_defs.append(f"  def \\#{{method.name}}(\\#{{method.args.join(\", \")}})")
            macro_defs.append(f"    \\#{{method.body}}")
            macro_defs.append(f"  end")
            macro_defs.append(f"end")

        return "\n".join(macro_defs) + "\n" + func_def

    def _transpile_args(self, args: ast.arguments) -> str:
        """Transpilar argumentos de função"""
        parts = []

        for arg in args.args:
            arg_name = arg.arg
            if arg.annotation:
                type_hint = self._transpile_node(arg.annotation)
                crystal_type = PYTHON_TO_CRYSTAL_TYPES.get(type_hint, type_hint)
                parts.append(f"{arg_name} : {crystal_type}")
            else:
                parts.append(arg_name)

        if args.vararg:
            arg_name = args.vararg.arg
            parts.append(f"*{arg_name}")

        for arg in args.kwonlyargs:
            arg_name = arg.arg
            if arg.annotation:
                type_hint = self._transpile_node(arg.annotation)
                crystal_type = PYTHON_TO_CRYSTAL_TYPES.get(type_hint, type_hint)
                parts.append(f"{arg_name} : {crystal_type}")
            else:
                parts.append(arg_name)

        return ", ".join(parts)

    def _transpile_return_annotation(self, annotation: Optional[ast.AST]) -> Optional[str]:
        """Transpilar anotação de retorno"""
        if annotation is None:
            return None
        type_hint = self._transpile_node(annotation)
        return PYTHON_TO_CRYSTAL_TYPES.get(type_hint, type_hint)

    def _transpile_assignment(self, node: ast.Assign) -> str:
        """Transpilar atribuição"""
        if len(node.targets) == 1:
            target = self._transpile_node(node.targets[0])
            value = self._transpile_node(node.value)
            return f"{target} = {value}"
        else:
            targets = ", ".join([self._transpile_node(t) for t in node.targets])
            value = self._transpile_node(node.value)
            return f"{targets} = {value}"

    def _transpile_expression(self, node: ast.Expr) -> str:
        """Transpilar expressão"""
        return self._transpile_node(node.value)

    def _transpile_function_call(self, node: ast.Call) -> str:
        """Transpilar chamada de função"""
        func_name = self._transpile_node(node.func)

        if func_name in self.python_to_crystal:
            func_name = self.python_to_crystal[func_name]

        args = ", ".join([self._transpile_node(arg) for arg in node.args])

        for kw in node.keywords:
            if kw.arg:
                arg_val = self._transpile_node(kw.value)
                args += f", {kw.arg}: {arg_val}"

        return f"{func_name}({args})"

    def _transpile_operator(self, op: ast.operator) -> str:
        """Mapear operador Python para Crystal"""
        ops = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.FloorDiv: "//",
            ast.Mod: "%",
            ast.Pow: "**",
            ast.BitAnd: "&",
            ast.BitOr: "|",
            ast.BitXor: "^",
            ast.LShift: "<<",
            ast.RShift: ">>",
        }
        return ops.get(type(op), "?")

    def _transpile_cmp_operator(self, op: ast.cmpop) -> str:
        """Mapear operador de comparação Python para Crystal"""
        ops = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.Is: "==",
            ast.IsNot: "!=",
            ast.In: ".includes?",
            ast.NotIn: ".includes?",
        }
        return ops.get(type(op), "==")

    # =========================================================================
    # NOVAS CONSTRUÇÕES
    # =========================================================================

    def _transpile_list_comprehension(self, node: ast.ListComp) -> str:
        """
        Transpilar list comprehension.

        Python: [x * 2 for x in range(10)]
        Crystal: (0...10).map { |x| x * 2 }
        """
        if len(node.generators) != 1:
            # Fallback para compreensões complexas
            return self._transpile_complex_comprehension(node, "Array")

        gen = node.generators[0]
        target = self._transpile_node(gen.target)
        iterable = self._transpile_node(gen.iter)
        element = self._transpile_node(node.elt)

        # Verificar se é filter (if clause)
        if gen.ifs:
            condition = self._transpile_node(gen.ifs[0])
            return f"{iterable}.select do |{target}|\n  {condition}\nend.map do |{target}|\n  {element}\nend"

        return f"{iterable}.map do |{target}|\n  {element}\nend"

    def _transpile_set_comprehension(self, node: ast.SetComp) -> str:
        """Transpilar set comprehension para Set.new + map."""
        gen = node.generators[0]
        target = self._transpile_node(gen.target)
        iterable = self._transpile_node(gen.iter)
        element = self._transpile_node(node.elt)

        return f"Set.new({iterable}.map do |{target}|\n  {element}\nend)"

    def _transpile_dict_comprehension(self, node: ast.DictComp) -> str:
        """Transpilar dict comprehension."""
        gen = node.generators[0]
        target = self._transpile_node(gen.target)
        iterable = self._transpile_node(gen.iter)
        key = self._transpile_node(node.key)
        value = self._transpile_node(node.value)

        return f"{iterable}.each_with_object({{}}) do |{target}, hash|\n  hash[{key}] = {value}\nend"

    def _transpile_generator_exp(self, node: ast.GeneratorExp) -> str:
        """Transpilar generator expression para iterator Crystal."""
        gen = node.generators[0]
        target = self._transpile_node(gen.target)
        iterable = self._transpile_node(gen.iter)
        element = self._transpile_node(node.elt)

        return f"{iterable}.each do |{target}|\n  {element}\nend"

    def _transpile_complex_comprehension(self, node: ast.expr, result_type: str) -> str:
        """Fallback para compreensões com múltiplos geradores."""
        if isinstance(node, (ast.ListComp, ast.SetComp)):
            gen = node.generators[0]
            target = self._transpile_node(gen.target)
            iterable = self._transpile_node(gen.iter)
            element = self._transpile_node(node.elt)
            return f"{iterable}.map do |{target}|\n  {element}\nend"
        elif isinstance(node, ast.DictComp):
            gen = node.generators[0]
            target = self._transpile_node(gen.target)
            iterable = self._transpile_node(gen.iter)
            key = self._transpile_node(node.key)
            value = self._transpile_node(node.value)
            return f"{iterable}.map do |{target}|\n  [{key}, {value}]\nend.to_h"
        return f"# TODO: Complex comprehension"

    def _transpile_lambda(self, node: ast.Lambda) -> str:
        """
        Transpilar lambda para Crystal block.

        Python: lambda x, y: x + y
        Crystal: ->(x, y) { x + y }
        """
        args = ", ".join(arg.arg for arg in node.args.args)
        body = self._transpile_node(node.body)
        return f"->({args}) {{ {body} }}"

    def _transpile_fstring(self, node: ast.JoinedStr) -> str:
        """
        Transpilar f-string para interpolação Crystal.

        Python: f"Hello {name}"
        Crystal: "Hello #{name}"
        """
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                expr = self._transpile_node(value.value)
                parts.append(f"#{{{expr}}}")

        return '"' + "".join(parts) + '"'

    def _transpile_try(self, node: ast.Try) -> str:
        """
        Transpilar try/except/finally para Crystal begin/rescue/ensure.

        Python:
            try:
                risky()
            except ValueError as e:
                handle(e)
            finally:
                cleanup()

        Crystal:
            begin
              risky()
            rescue e : ValueError
              handle(e)
            ensure
              cleanup()
            end
        """
        body = "\n".join([f"  {self._transpile_node(stmt)}" for stmt in node.body])

        result = f"begin\n{body}"

        for handler in node.handlers:
            if handler.type:
                exc_type = self._transpile_node(handler.type)
                exc_name = self._transpile_node(handler.name) if handler.name else "e"
                handler_body = "\n".join([f"  {self._transpile_node(s)}" for s in handler.body])
                result += f"\nrescue {exc_name} : {exc_type}\n{handler_body}"
            else:
                handler_body = "\n".join([f"  {self._transpile_node(s)}" for s in handler.body])
                result += f"\nrescue\n{handler_body}"

        if node.orelse:
            else_body = "\n".join([f"  {self._transpile_node(s)}" for s in node.orelse])
            result += f"\nelse\n{else_body}"

        if node.finalbody:
            finally_body = "\n".join([f"  {self._transpile_node(s)}" for s in node.finalbody])
            result += f"\nensure\n{finally_body}"

        result += "\nend"
        return result

    def _transpile_with(self, node: ast.With) -> str:
        """
        Transpilar with statement para Crystal blocks.

        Python:
            with open("file.txt") as f:
                content = f.read()

        Crystal:
            File.open("file.txt") do |f|
              content = f.gets_to_end
            end
        """
        result = ""
        for item in node.items:
            context_expr = self._transpile_node(item.context_expr)

            # Handle open() specially -> File.open()
            if (
                isinstance(item.context_expr, ast.Call)
                and isinstance(item.context_expr.func, ast.Name)
                and item.context_expr.func.id == "open"
            ):
                args = ", ".join(self._transpile_node(a) for a in item.context_expr.args)
                context_expr = f"File.open({args})"

            if item.optional_vars:
                var = self._transpile_node(item.optional_vars)
                result += f"{context_expr}.open do |{var}|\n"
            else:
                result += f"{context_expr}.open do\n"

        body = "\n".join([f"  {self._transpile_node(stmt)}" for stmt in node.body])
        result += body

        # Fechar blocos
        for _ in node.items:
            result += "\nend"

        return result

    def _transpile_class(self, node: ast.ClassDef) -> str:
        """
        Transpilar classe Python para Crystal.

        Python:
            class Person:
                def __init__(self, name, age):
                    self.name = name
                    self.age = age

        Crystal:
            class Person
              def initialize(@name : String, @age : Int32)
              end

              getter name
              getter age
            end
        """
        bases = ", ".join(self._transpile_node(base) for base in node.bases)
        class_line = f"class {node.name}"
        if bases:
            class_line += f" < {bases}"

        body_parts = []
        init_method = None
        other_methods = []

        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                if stmt.name == "__init__":
                    init_method = stmt
                else:
                    other_methods.append(stmt)
            elif isinstance(stmt, ast.Assign):
                # Variáveis de classe
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        body_parts.append(f"  @{var_name}")
            else:
                body_parts.append(f"  {self._transpile_node(stmt)}")

        # Gerar initialize
        if init_method:
            args = self._transpile_init_args(init_method.args)
            init_body = []
            for stmt in init_method.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Attribute):
                            if isinstance(target.value, ast.Name) and target.value.id == "self":
                                value = self._transpile_node(stmt.value)
                                init_body.append(f"  @{target.attr} = {value}")
                else:
                    init_body.append(f"  {self._transpile_node(stmt)}")

            body_parts.insert(0, f"def initialize({args})")
            body_parts.insert(1, "\n".join(init_body))
            body_parts.insert(2, "end")

        # Gerar getters
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        body_parts.append(f"\n  getter {target.id}")

        # Gerar outros métodos
        for method in other_methods:
            body_parts.append(f"\n{self._transpile_function_def(method)}")

        class_body = "\n".join(body_parts)
        return f"{class_line}\n{class_body}\nend"

    def _transpile_init_args(self, args: ast.arguments) -> str:
        """Transpilar argumentos do __init__ para Crystal initialize."""
        parts = []
        for arg in args.args:
            if arg.arg == "self":
                continue
            arg_name = arg.arg
            if arg.annotation:
                type_hint = self._transpile_node(arg.annotation)
                crystal_type = PYTHON_TO_CRYSTAL_TYPES.get(type_hint, type_hint)
                parts.append(f"@{arg_name} : {crystal_type}")
            else:
                parts.append(f"@{arg_name}")
        return ", ".join(parts)

    def _transpile_yield(self, node: ast.Yield) -> str:
        """
        Transpilar yield para Crystal.

        Python: yield value
        Crystal: yield value
        """
        if node.value:
            value = self._transpile_node(node.value)
            return f"yield {value}"
        return "yield"

    def _transpile_yield_from(self, node: ast.YieldFrom) -> str:
        """
        Transpilar yield from para Crystal.

        Python: yield from iterable
        Crystal: iterable.each { |x| yield x }
        """
        iterable = self._transpile_node(node.value)
        return f"{iterable}.each {{ |x| yield x }}"

    def _wrap_crystal_code(self, code: str) -> str:
        """Envolver código Crystal em estrutura básica"""
        wrapper = """# Crystal code generated from Python

# Main execution
%s
"""
        return wrapper % code


class TranspilerError(Exception):
    """Erro específico do transpiler"""
    pass
