from dataclasses import dataclass
from typing import Dict, List

# for this assignment, both terminals/nonterminals are just strings
Symbol = str


@dataclass
class Alternative:
    # one RHS option in a rule (like ["R"])
    seq: List[Symbol]
    # optional weight if we want weighted choices later
    weight: float = 1.0


class CFG:
    def __init__(self) -> None:
        # stores grammar like: "<S>" -> [Alternative(...), Alternative(...)]
        self.rules: Dict[Symbol, List[Alternative]] = {}

    def add_rule(self, lhs: Symbol, alternatives: List[Alternative]) -> None:
        # left side should be a nonterminal such as <S>
        if not self.is_nonterminal(lhs):
            raise ValueError(f"LHS must be a nonterminal like <S>, got {lhs}")

        # overwrite rule if it already exists
        self.rules[lhs] = alternatives

    def is_nonterminal(self, sym: Symbol) -> bool:
        # in our format, nonterminals are wrapped in angle brackets
        return len(sym) >= 3 and sym[0] == "<" and sym[-1] == ">"

    def get_rule(self, lhs: Symbol) -> List[Alternative]:
        # return [] if rule doesn't exist (avoids KeyError)
        return self.rules.get(lhs, [])


if __name__ == "__main__":
    # quick test run so we can execute this file directly
    g = CFG()

    # example: <LEVEL> -> R | G | B
    g.add_rule("<LEVEL>", [
        Alternative(["R"]),
        Alternative(["G"]),
        Alternative(["B"]),
    ])

    # print what got stored
    print("Rules loaded:", list(g.rules.keys()))
    print("<LEVEL> alternatives:")
    for i, alt in enumerate(g.get_rule("<LEVEL>"), start=1):
        print(f"  {i}. seq={alt.seq}, weight={alt.weight}")

    # sanity checks
    print("is_nonterminal('<LEVEL>'):", g.is_nonterminal("<LEVEL>"))
    print("is_nonterminal('R'):", g.is_nonterminal("R"))
