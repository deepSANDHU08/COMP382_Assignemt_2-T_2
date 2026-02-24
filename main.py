from City_implementation import CityParams, generate_city, print_height_map


def main():
    # basic parameters for the city
    params = CityParams(
        seed=123,
        empty_prob=0.35,
        min_height=2,
        max_height=8,
        dominant_prob=0.70
    )

    # generate city grid
    city = generate_city(width=12, height=8, params=params)

    # simple console visualization
    print_height_map(city)


if __name__ == "__main__":
    main()