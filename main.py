from City_implementation import CityParams, generate_city, print_height_map


def main():
    params = CityParams(
        seed=999,             
        empty_prob=0.15,      
        min_height=3,         
        max_height=12,        
        dominant_prob=0.80    
    )

    # generate city grid
    city = generate_city(width=12, height=8, params=params)

    # simple console visualization
    print_height_map(city)


if __name__ == "__main__":
    main()