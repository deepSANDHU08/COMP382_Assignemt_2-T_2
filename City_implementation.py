import random
from dataclasses import dataclass
from typing import List
from Temp_CFG import choose_dominant_color, expand_column
import json

# just simple buildings
Color = str
Stack = List[Color]
City = List[List[Stack]]  # this is for 2D grid: city[y][x]


# start with basic parameter first
@dataclass
class CityParams:
    seed: int = 42

    # chance that a grid cell has no building
    empty_prob: float = 0.30

    # deciding the range of height of the building
    min_height: int = 1
    max_height: int = 7

    # probability that cube matches dominant color (RV5)
    dominant_prob: float = 0.70


# Randomize the color for now.
# Will chnage this later. we do't need it
def random_color(rng: random.Random) -> Color:
    return rng.choice(["R", "G", "B"])


def make_stack(rng: random.Random, params) -> List[str]:
    """
    Implementation-side stack builder that uses the CFG module.

    Height is chosen here (RV2).
    Dominant color + cube colors come from Temp_CFG.py (RV4 + RV5).
    """
    # RV2: choose stack height
    height = rng.randint(params.min_height, params.max_height)

    # RV4: choose dominant color
    dominant = choose_dominant_color()

    # CFG + RV5: expand COLUMN into cube colors (bottom -> top)
    colors = expand_column(height, dominant, params.dominant_prob)

    return colors


# syntax errors fixed remember the indentation for next time
def generate_city(width: int, height: int, params: CityParams) -> City:
    """
    Generates a simple grid.

    Each cell:
     - empty lot OR
     - building stack
    """
    rng = random.Random(params.seed)
    city: City = []

    for _y in range(height):
        row: List[Stack] = []
        for _x in range(width):
            # decide if this spot stays empty
            if rng.random() < params.empty_prob:
                row.append([])
            else:
                row.append(make_stack(rng, params))
        city.append(row)

    return city


# simple visualization
def print_height_map(city: City) -> None:
    print("\nCity height map:\n")

    for row in city:
        line = []
        for stack in row:
            h = len(stack)
            if h == 0:
                line.append(".")
            else:
                line.append(str(min(h, 9)))  # cap display at 9
        print(" ".join(line))


# inspect for debugging
def inspect_cell(city: City, x: int, y: int) -> None:
    stack = city[y][x]

    if not stack:
        print(f"Cell ({x},{y}) is empty.")
    else:
        print(f"Cell ({x},{y}) height={len(stack)} colors={stack}.")


# for the json output
def export_to_json(city: City, filepath: str = "city_output.json") -> None:
    """
    Converts grid city[y][x] into a Blender-friendly cube list
    and automatically writes a JSON file.
    """
    cubes = []

    for y, row in enumerate(city):
        for x, stack in enumerate(row):
            for z, color in enumerate(stack):
                cubes.append(
                    {
                        "x": x,
                        "y": y,
                        "z": z,
                        "color": color,
                    }
                )

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(cubes, file, indent=2)
