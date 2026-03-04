import unittest
from City_implementation import CityParams, generate_city, inspect_cell

class TestCityGeneration(unittest.TestCase):
    def test_city_dimensions(self):
        # Settting up the parameters
        params = CityParams(seed=123, empty_prob=0.0, min_height=2, max_height=8, dominant_prob=0.70)
        
        # Generate a small 5x5 city
        width, height = 5, 5
        city = generate_city(width=width, height=height, params=params)
        
        # Check if the grid actually matches the width and height requested
        self.assertEqual(len(city), height, "City height does not match expected rows")
        self.assertEqual(len(city[0]), width, "City width does not match expected columns")

if __name__ == '__main__':
    unittest.main()
