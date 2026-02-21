"""
COMP 382 Assignment 2 — CFG + Random Variables

TOPIC:
Procedurally generate stacks of three coloured cubes (R, G, B) on a flat grid.
Stacks are controlled by random variables (statistics) and guided by an input CFG.

------------------------------------------------------------
CFG (simple and clear)
------------------------------------------------------------
CITY   -> STACK CITY | STACK
STACK  -> COLUMN
COLUMN -> CUBE COLUMN | CUBE
CUBE   -> R | G | B

Meaning:
- A CITY is a list of STACKs.
- Each STACK is a vertical COLUMN of CUBEs.
- Each CUBE is one of {R, G, B}.

------------------------------------------------------------
Random Variables (RV / Statistics)
------------------------------------------------------------
1) num_stacks ~ UniformInt(min_stacks, max_stacks)
2) height(stack) ~ UniformInt(min_height, max_height)
3) grid_position(stack) ~ Uniform among free cells in a grid (no overlap)
4) dominant_color(stack) ~ Uniform choice from {R,G,B}
5) color_per_cube given dominant_color:
   - P(dominant) = dominant_prob
   - remaining probability split equally among the other two colors
This gives variety but still looks "organized" per stack.
"""

from __future__ import annotations
import json
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional


# ----------------------------
# Data structure
# ----------------------------
@dataclass
class Stack:
    x: int
    z: int
    height: int
    colors: List[str]  # bottom -> top


# ----------------------------
# Random variable helpers
# ----------------------------
def choose_dominant_color() -> str:
    return random.choice(["R", "G", "B"])


def choose_cube_color(dominant: str, dominant_prob: float = 0.7) -> str:
    """
    Weighted color selection.
    Example: if dominant='B' and dominant_prob=0.7
      P(B)=0.7, P(R)=0.15, P(G)=0.15
    """
    others = [c for c in ["R", "G", "B"] if c != dominant]
    # Simple weighted pick without external libs
    r = random.random()
    if r < dominant_prob:
        return dominant
    else:
        # split remaining probability equally
        return random.choice(others)


def random_height(min_h: int, max_h: int) -> int:
    return random.randint(min_h, max_h)


def random_num_stacks(min_s: int, max_s: int) -> int:
    return random.randint(min_s, max_s)


# ----------------------------
# Grid placement (no overlap)
# ----------------------------
def generate_unique_positions(grid_w: int, grid_d: int, count: int) -> List[Tuple[int, int]]:
    """
    Picks unique (x,z) cells from a grid.
    If count > grid_w*grid_d, it will cap to max possible.
    """
    all_cells = [(x, z) for x in range(grid_w) for z in range(grid_d)]
    random.shuffle(all_cells)
    max_possible = grid_w * grid_d
    count = min(count, max_possible)
    return all_cells[:count]


# ----------------------------
# Main generator (CFG-guided)
# ----------------------------
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
    Generates a CITY -> list of STACKs.
    Output is list[dict] so it's easy to dump to JSON and use in Blender/Godot/etc.
    """
    if seed is not None:
        random.seed(seed)

    n = random_num_stacks(min_stacks, max_stacks)
    positions = generate_unique_positions(grid_w, grid_d, n)

    stacks: List[Stack] = []
    for (x, z) in positions:
        h = random_height(min_height, max_height)
        dom = choose_dominant_color()
        colors = [choose_cube_color(dom, dominant_prob) for _ in range(h)]
        stacks.append(Stack(x=x, z=z, height=h, colors=colors))

    # Convert to dicts for JSON
    return [asdict(s) for s in stacks]


def save_city_to_json(filepath: str = "city_output.json", **kwargs) -> str:
    """
    Convenience function: generates and saves output to JSON.
    Returns the filepath.
    """
    data = generate_city(**kwargs)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return filepath


# ----------------------------
# Quick test run
# ----------------------------
if __name__ == "__main__":
    # Example test: change seed to see different cities
    city = generate_city(seed=42)
    print("Generated stacks:", len(city))
    print(city[:3])  # print first 3 stacks
    save_city_to_json("city_output.json", seed=42)
    print("Saved: city_output.json")