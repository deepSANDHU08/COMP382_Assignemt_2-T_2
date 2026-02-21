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
   # nested for loops for range in height and range in width
   # try to do it 3D, brains stroms some idea.

def print_height_map():
   # this one is for visulization

# REMEMBER TO MAKE A TEMPORARY MAIN HERE FOR TESTING 
# THINK ABOUT RANDOM VARAIBLES AND PROPBABBILIES OF COLORS
