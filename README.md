# Procedural Stack Generation

A Python program that uses a context-free grammar (CFG) to generate a city of coloured cube stacks on a flat grid. Each stack is made up of red, green, and blue cubes, and the grammar controls how the city is built while random variables add variety.

## How It Works

The program follows three steps:

1. **Grammar expansion** — A CFG decides the structure. It starts from a `CITY`, breaks it into `STACK`s, breaks each stack into a `COLUMN` of `CUBE`s, and then assigns each cube a colour (`R`, `G`, or `B`).

2. **Random variables** — At each step, randomness controls the outcome:
   - How many stacks to place (some grid cells stay empty)
   - How tall each stack is (between a min and max height)
   - A dominant colour per stack (one colour shows up ~70% of the time)

3. **Grid placement** — Stacks are placed on a 2D grid. Empty cells are marked with `.` and stacks show their height as a number.

## Project Structure

```
Temp_CFG.py              — Grammar rules + expansion engine
City_implementation.py   — City grid builder (imports from Temp_CFG)
main.py                  — Entry point, generates and displays a city
gui.py                   — Desktop GUI visualizer (2D + optional 3D)
city_output.json         — Sample output from the generator
requirements.txt         — GUI dependencies
```

## Running It (Console Version)

Make sure you have Python 3 installed, then:

```bash
python3 main.py
```

This prints a height map of the generated city:

```
. . 2 8 . 4 . . . 7 . .
2 5 . . 2 . . 2 . 5 . 8
. 5 . 6 4 . 7 7 8 8 7 6
. 3 2 7 . . 2 5 4 . 8 2
3 6 2 5 7 6 3 . 5 2 . 2
. 4 7 2 6 2 . 8 2 7 4 .
8 5 . 3 5 . 3 3 8 2 5 3
8 8 4 . 6 . . 5 . . 4 7
```

Each number is a stack that many cubes tall. Each `.` is an empty lot.

## Running It (GUI Version)

The GUI gives an interactive view for presentation/demo.

Install dependencies:

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

Run:

```bash
python3 gui.py
```

## GUI Features (Simple Overview)

- Change `width`, `height`, `seed`, and probability settings
- Click **Generate** to make a new city
- Switch between **2D** and **3D view**
- Turn on **Compare seeds (A/B)** to show two seeds side by side
- Click a stack to see:
  - coordinates
  - height
  - dominant colour
  - full colour list
  - derivation trace
- **Save JSON** exports city data
- **Export PNG** saves an image of the current view
- **Demo (123 vs 999)** quickly shows two seed results and saves demo images

## Inspecting a Stack

To see the actual colours inside a specific cell:

```python
from City_implementation import CityParams, generate_city, inspect_cell

params = CityParams(seed=123, empty_prob=0.35, min_height=2, max_height=8, dominant_prob=0.70)
city = generate_city(width=12, height=8, params=params)
inspect_cell(city, 3, 0)
```

Output:
```
Cell (3,0) height=8 colors=['G', 'G', 'R', 'G', 'G', 'G', 'G', 'B'].
```

## Configuration

You can tweak the city by changing the parameters in `main.py` or in the GUI panel:

| Parameter | Default | What it does |
|---|---|---|
| `seed` | 123 | Random seed for reproducibility |
| `empty_prob` | 0.35 | Chance a grid cell has no building |
| `min_height` | 2 | Shortest possible stack |
| `max_height` | 8 | Tallest possible stack |
| `dominant_prob` | 0.70 | How strongly the dominant colour shows up |
| `width` | 12 | Grid width |
| `height` | 8 | Grid depth |

## Built With

- Python 3
- PySide6 (GUI)
- matplotlib + numpy (3D visualization)

## Bibliography / Acknowledgements

- OpenAI Codex was used to help design and implement the Python GUI (`gui.py`) and related setup files.
- Anthropic AI was used to better understand context-free grammar (CFG) concepts during development.
- Sipser, Michael. *Introduction to the Theory of Computation* (3rd Edition) was used as a textbook reference for formal language and CFG ideas.
