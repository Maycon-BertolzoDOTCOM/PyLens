"""Exceções customizadas do Crystalize."""


class TranspilerNotImplementedError(Exception):
    """
    Lançada quando o Transpiler gera código Crystal com construções não suportadas
    (marcadas como '# TODO: Transpile <NomeDoNó>').
    """
    def __init__(self, node_name: str):
        self.node_name = node_name
        super().__init__(
            f"A construção Python '{node_name}' ainda não é suportada pelo transpiler."
        )
