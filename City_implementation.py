import random
from dataclasses import dataclass
from typing import List
from Temp_CFg import choose_dominant_color, expand_column

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


# Randomize the color for now.
# need to connect with cfg file and probabilities later.
def random_color(rng: random.Random) -> Color:
    return rng.choice(["R", "G", "B"])


def make_stack(rng: random.Random, params) -> list[str]:
    """
    Implementation-side stack builder that uses the CFG module.

    Needs in params:
      - min_height
      - max_height
      - dominant_prob
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


# REMEMBER TO MAKE A TEMPORARY MAIN HERE FOR TESTING
def main() -> None:
    params = CityParams(
        seed=123,
        empty_prob=0.35,
        min_height=2,
        max_height=8,
    )

    city = generate_city(width=12, height=8, params=params)

    print_height_map(city)

    print("\nChecking a few cells:")
    inspect_cell(city, 0, 0)
    inspect_cell(city, 5, 3)
    inspect_cell(city, 11, 7)


if __name__ == "__main__":
    main()
