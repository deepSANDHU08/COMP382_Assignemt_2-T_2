import random
from dataclasses import dataclass
from typing import List

#just simple buildings 
Color = str
Stack = List(Color)
City = List[List(Stack)]  # this is for 2D grid : city[y][x]

#start with basic parameter first
@dataclass
class CityParams
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

