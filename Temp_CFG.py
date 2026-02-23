"""
COMP 382 Assignment 2 — CFG + Random Variables

TOPIC:
Procedurally generate stacks of three coloured cubes (R, G, B) on a flat grid.
Stacks are controlled by random variables (statistics) and guided by an input CFG.

------------------------------------------------------------
CFG (Formal Definition)
------------------------------------------------------------
Terminals:     {R, G, B}
Non-terminals: {CITY, STACK, COLUMN, CUBE}
Start symbol:  CITY

Production Rules:
  CITY   -> STACK CITY   (keep adding stacks)
  CITY   -> STACK         (stop — base case)
  STACK  -> COLUMN
  COLUMN -> CUBE COLUMN   (keep stacking cubes)
  COLUMN -> CUBE           (stop — base case)
  CUBE   -> R | G | B

------------------------------------------------------------
Random Variables (RV / Statistics)
------------------------------------------------------------
1) num_stacks     ~ UniformInt(min_stacks, max_stacks)
     Controls how many times CITY -> STACK CITY is applied vs CITY -> STACK
2) height(stack)  ~ UniformInt(min_height, max_height)
     Controls how many times COLUMN -> CUBE COLUMN is applied vs COLUMN -> CUBE
3) grid_position  ~ Uniform among free cells (no overlap)
4) dominant_color ~ Uniform choice from {R, G, B}
5) color_per_cube given dominant_color:
     P(dominant) = dominant_prob
     Remaining probability split equally among the other two
"""

from __future__ import annotations
import json
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional


# ============================================================
# Formal CFG Definition
# ============================================================
# Production rules stored as a dictionary.
# Each non-terminal maps to a list of possible productions.
# Each production is a list of symbols (strings).

CFG_RULES: Dict[str, List[List[str]]] = {
    "CITY":   [["STACK", "CITY"],   # recursive: add another stack
               ["STACK"]],           # base case: stop
    "STACK":  [["COLUMN"]],         # a stack is just a column of cubes
    "COLUMN": [["CUBE", "COLUMN"],  # recursive: add another cube
               ["CUBE"]],           # base case: stop
    "CUBE":   [["R"],               # terminal: red
               ["G"],               # terminal: green
               ["B"]],              # terminal: blue
}

TERMINALS = {"R", "G", "B"}
START_SYMBOL = "CITY"


# ============================================================
# Data structure for output
# ============================================================
@dataclass
class Stack:
    x: int
    z: int
    height: int
    dominant_color: str      # which color was biased for this stack
    colors: List[str]        # bottom -> top


# ============================================================
# Random Variable Helpers
# ============================================================
def choose_dominant_color() -> str:
    """RV4: dominant color ~ Uniform({R, G, B})"""
    return random.choice(["R", "G", "B"])


def choose_cube_color(dominant: str, dominant_prob: float = 0.7) -> str:
    """
    RV5: color selection weighted by dominant color.
    Example: if dominant='B' and dominant_prob=0.7
      P(B)=0.7, P(R)=0.15, P(G)=0.15
    """
    others = [c for c in ["R", "G", "B"] if c != dominant]
    r = random.random()
    if r < dominant_prob:
        return dominant
    else:
        return random.choice(others)


# ============================================================
# CFG Expansion Engine
# ============================================================
def expand_city(num_stacks: int) -> int:
    """
    Expand CITY using the grammar rules.
    Applies CITY -> STACK CITY  (num_stacks - 1) times,
    then   CITY -> STACK        once (base case).

    RV1 (num_stacks) controls which production is chosen at each step.
    Returns the number of stacks produced (for verification).
    """
    derivation = [START_SYMBOL]
    stacks_remaining = num_stacks

    while stacks_remaining > 0:
        if stacks_remaining > 1:
            # Apply: CITY -> STACK CITY
            production = CFG_RULES["CITY"][0]  # ["STACK", "CITY"]
        else:
            # Apply: CITY -> STACK (base case)
            production = CFG_RULES["CITY"][1]  # ["STACK"]

        # Replace the rightmost CITY in derivation
        idx = len(derivation) - 1 - derivation[::-1].index("CITY")
        derivation = derivation[:idx] + production + derivation[idx + 1:]
        stacks_remaining -= 1

    return derivation.count("STACK")


def expand_column(height: int, dominant: str, dominant_prob: float) -> List[str]:
    """
    Expand STACK -> COLUMN -> sequence of CUBEs using the grammar rules.

    Applies COLUMN -> CUBE COLUMN  (height - 1) times,
    then    COLUMN -> CUBE          once (base case).
    Then each CUBE is expanded to a terminal {R, G, B} using RV5.

    RV2 (height) controls which COLUMN production is chosen.
    RV5 (color weighting) controls which CUBE production is chosen.
    """
    # Step 1: Expand STACK -> COLUMN (only one production)
    derivation = CFG_RULES["STACK"][0]  # ["COLUMN"]

    # Step 2: Expand COLUMN into a sequence of CUBEs
    cubes_remaining = height
    while cubes_remaining > 0:
        # Find the COLUMN non-terminal to expand
        col_idx = derivation.index("COLUMN")

        if cubes_remaining > 1:
            # Apply: COLUMN -> CUBE COLUMN
            production = CFG_RULES["COLUMN"][0]  # ["CUBE", "COLUMN"]
        else:
            # Apply: COLUMN -> CUBE (base case)
            production = CFG_RULES["COLUMN"][1]  # ["CUBE"]

        derivation = derivation[:col_idx] + production + derivation[col_idx + 1:]
        cubes_remaining -= 1

    # Step 3: Expand each CUBE -> terminal color using weighted RV
    colors = []
    for symbol in derivation:
        if symbol == "CUBE":
            color = choose_cube_color(dominant, dominant_prob)
            # This is choosing among CUBE -> R | G | B
            colors.append(color)

    return colors


def log_derivation_example(num_stacks: int, height: int, dominant: str,
                           dominant_prob: float) -> str:
    """
    Returns a string showing one full derivation trace for documentation.
    Useful for the report/presentation to show the CFG is actually being applied.
    """
    lines = []
    lines.append(f"--- CFG Derivation Trace (stacks={num_stacks}, height={height}) ---")
    lines.append(f"Start: {START_SYMBOL}")

    # Show CITY expansion
    form = [START_SYMBOL]
    for i in range(num_stacks):
        if i < num_stacks - 1:
            rule_used = "CITY -> STACK CITY"
            idx = len(form) - 1 - form[::-1].index("CITY")
            form = form[:idx] + ["STACK", "CITY"] + form[idx + 1:]
        else:
            rule_used = "CITY -> STACK"
            idx = len(form) - 1 - form[::-1].index("CITY")
            form = form[:idx] + ["STACK"] + form[idx + 1:]
        lines.append(f"  Apply {rule_used}:  {' '.join(form)}")

    lines.append("")
    lines.append(f"Expanding first STACK (height={height}, dominant={dominant}):")

    # Show STACK -> COLUMN
    lines.append(f"  Apply STACK -> COLUMN:  COLUMN")

    # Show one COLUMN expansion
    col_form = ["COLUMN"]
    for i in range(height):
        if i < height - 1:
            rule_used = "COLUMN -> CUBE COLUMN"
            idx = col_form.index("COLUMN")
            col_form = col_form[:idx] + ["CUBE", "COLUMN"] + col_form[idx + 1:]
        else:
            rule_used = "COLUMN -> CUBE"
            idx = col_form.index("COLUMN")
            col_form = col_form[:idx] + ["CUBE"] + col_form[idx + 1:]
        lines.append(f"  Apply {rule_used}:  {' '.join(col_form)}")

    # Show CUBE -> terminal
    final = []
    for sym in col_form:
        if sym == "CUBE":
            c = choose_cube_color(dominant, dominant_prob)
            final.append(c)
    lines.append(f"  Apply CUBE -> color:  {' '.join(final)}")

    return "\n".join(lines)


# ============================================================
# Grid Placement (no overlap) — RV3
# ============================================================
def generate_unique_positions(grid_w: int, grid_d: int, count: int) -> List[Tuple[int, int]]:
    """
    RV3: grid_position ~ Uniform among free cells.
    Picks unique (x, z) cells from the grid so stacks don't overlap.
    """
    all_cells = [(x, z) for x in range(grid_w) for z in range(grid_d)]
    random.shuffle(all_cells)
    count = min(count, grid_w * grid_d)
    return all_cells[:count]


# ============================================================
# Main Generator — Drives CFG Expansion with RVs
# ============================================================
def generate_city(
    grid_w: int = 10,
    grid_d: int = 10,
    min_stacks: int = 20,
    max_stacks: int = 50,
    min_height: int = 1,
    max_height: int = 10,
    dominant_prob: float = 0.7,
    seed: Optional[int] = None,
) -> List[Dict]:
    """
    Generates a CITY by expanding the CFG with random variables.

    Pipeline:
      1. RV1 decides num_stacks  -> controls CITY expansion
      2. RV3 picks grid positions -> unique (x,z) per stack
      3. For each STACK:
         a. RV2 decides height   -> controls COLUMN expansion
         b. RV4 picks dominant   -> biases CUBE expansion
         c. RV5 picks each color -> expands CUBE -> R|G|B
    """
    if seed is not None:
        random.seed(seed)

    # RV1: how many stacks
    num_stacks = random.randint(min_stacks, max_stacks)

    # Verify CFG expansion produces correct count
    expanded_count = expand_city(num_stacks)
    assert expanded_count == num_stacks, "CFG expansion mismatch!"

    # RV3: grid positions
    positions = generate_unique_positions(grid_w, grid_d, num_stacks)

    # Expand each STACK via CFG
    stacks: List[Stack] = []
    for (x, z) in positions:
        h = random.randint(min_height, max_height)    # RV2
        dom = choose_dominant_color()                   # RV4
        colors = expand_column(h, dom, dominant_prob)   # RV5 via CFG expansion
        stacks.append(Stack(x=x, z=z, height=h, dominant_color=dom, colors=colors))

    return [asdict(s) for s in stacks]


def save_city_to_json(filepath: str = "city_output.json", **kwargs) -> str:
    """Generate city and save to JSON."""
    data = generate_city(**kwargs)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return filepath


# ============================================================
# Quick test / demo
# ============================================================
if __name__ == "__main__":
    city = generate_city(seed=42)
    print(f"Generated {len(city)} stacks\n")

    # Show first 3 stacks
    for i, s in enumerate(city[:3]):
        print(f"Stack {i}: pos=({s['x']},{s['z']})  h={s['height']}  "
              f"dominant={s['dominant_color']}  colors={s['colors']}")

    # Show a derivation trace
    print()
    random.seed(42)
    trace = log_derivation_example(num_stacks=4, height=3, dominant="B", dominant_prob=0.7)
    print(trace)

    # Save output
    save_city_to_json("city_output.json", seed=42)
    print("\nSaved: city_output.json")