import random
from dataclasses import dataclass
from typing import List

#just simple buildings 
Color = str
Stack = List(Color)
City = List[List(Stack)]  # this is for 2D grid : city[y][x]

#start with basic parameter first
@dataclass
class CityParams:
    seed: int = 42

    #chance that a grid cell has no building
    empty_prob: float = 0.30

    #deciding the range of height of the building
    min_height: int = 1
    max_height: int = 7

# Randomize the color for now.
# need to connect with cfg file and probabilties later.

def random_color(rng: random.Random) -> Color:
    return rng.choice(["R", "G", "B"])

def make_stack(rng: random.Random, params: CityParams) -> Satck:
    """
    Creates one buikding stack.

    Height is random between min_height and max_height,
    then we fill it random cube colors.
    """
    height = rng.randint(params.min_height, params.max_heigth)

    stack = []
    for _ in range(height):
     stack.appenf(random_color(rng))

    return stack
## syntax errors fixed remember the intedentation for next time

def generate_city(width: int, height: int, params: CityParams) -> City:
   """
   Generates a simple grid.

   Each cell:
    - empty lot OR
    - building stack
   """
   rng = random.Random(params.seed)
   city: City = []
   for y in range(height):
      row = []
      for x in range(width):
         # decide if this spot stays the empty
         if rng.random() < params.empty_prob:
            row.append([])
         else:
          row.append(make_stack(rng, parmas))
      city.append(row)
   return city

#simple visualization 
def print_height_map(city: City):
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

# inspect for debugginh 
def inspect_cell(city: City, x: int, y: int):
   stack = city[y][x]

   if not stack:
      print(f"Cell ({x},{y}) is empty.")
   else:
      print(f"Cell ({x},{y}) height={;en(stack)} colors={stack}.")
      

# REMEMBER TO MAKE A TEMPORARY MAIN HERE FOR TESTING 
def main():
    params = CityParams(
        seed=123,
        empty_prob=0.35,
        min_height=2,
        max_height=8
    )

    city = generate_city(width=12, height=8, params=params)

    print_height_map(city)

    print("\nChecking a few cells:")
    inspect_cell(city, 0, 0)
    inspect_cell(city, 5, 3)
    inspect_cell(city, 11, 7)


if __name__ == "__main__":
    main()