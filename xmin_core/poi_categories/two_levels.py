from xmin_core.poi_categories.base import POICatogories, Category, SubCategory


class TwoLvlFacilitiesCategories(POICatogories):
    @staticmethod
    def culture_leisure_benchmark(poi_count: int):
        match poi_count:
            case x if x < 1:
                return 0
            case 1:
                return 25
            case 2:
                return 25 + 15
            case x if x > 2:
                return min(100, 25 + 15 + (poi_count - 2) * 10)

    # todo: the sum of sub_weights in each category is not always 1.0, need to check.
    education = Category(
        weight=0.2,
        subcategories=[
            SubCategory(
                name="primary",
                sub_weight=0.8,
                tag="amenity=school and isced:level=1",
                benchmark=2,
            ),
            SubCategory(
                name="secondary",
                sub_weight=0.2,
                tag="amenity=school and (isced:level=2 or isced:level=3)",
                benchmark=1,
            ),
        ],
    )

    childcare = Category(
        weight=0.1,
        subcategories=[
            SubCategory(
                name="babycare",
                sub_weight=0.2,
                tag="amenity=childcare or amenity=nursery",
                benchmark=1,
            ),
            SubCategory(
                name="early_education",
                sub_weight=0.5,
                tag="amenity=kindergarten",
                benchmark=2,
            ),
            SubCategory(
                name="play",
                sub_weight=0.3,
                tag="amenity=toy_library or leisure=playground or leisure=indoor_play",
                benchmark=1,
            ),
        ],
    )

    healthcare = Category(
        weight=0.1,
        subcategories=[
            SubCategory(
                name="primary_care",
                sub_weight=0.3,
                tag="(amenity=doctors or healthcare=doctor or amenity=clinic) and "
                "(healthcare:speciality=general or healthcare:speciality=internal)",
                benchmark=3,
            ),
            SubCategory(
                name="dentist",
                sub_weight=0.2,
                tag="amenity=dentist or healthcare=dentist",
                benchmark=1,
            ),
            SubCategory(
                name="pharmacy",
                sub_weight=0.4,
                tag="amenity=pharmacy or healthcare=pharmacy",
                benchmark=2,
            ),
            SubCategory(
                name="specialist",
                sub_weight=0.1,
                tag="healthcare:speciality=* and (healthcare:speciality!=general or healthcare:speciality=internal)",
                benchmark=3,
            ),
        ],
    )

    daily_living = Category(
        weight=0.4,
        subcategories=[
            Category(
                group="grocery",
                weight=0.8,
                subcategories=[
                    SubCategory(
                        name="grocery_large",
                        sub_weight=1,
                        tag="shop=supermarket",
                        benchmark=1,
                    ),
                    SubCategory(
                        name="grocery_medium",
                        sub_weight=1,
                        tag="amenity=marketplace or shop=convenience",
                        benchmark=3,
                    ),
                    SubCategory(
                        name="grocery_specialbase",
                        sub_weight=1,
                        tag="shop in "
                        "(cheese, coffee, deli, farm, frozen_food, health_food, organic, "
                        "water, bakery, butcher, dairy, food, greengrocer, grocery, seafood)",
                        benchmark=5,
                    ),
                    SubCategory(
                        name="grocery_specialluxury",
                        sub_weight=0.5,
                        tag="shop in (alcohol, beverages, chocolate, ice_cream, pastry, spices, tea, water, wine, confectionery)",
                        benchmark=5,
                    ),
                ],
            ),
            Category(
                group="post",
                weight=0.1,
                subcategories=[
                    SubCategory(
                        name="post_office",
                        sub_weight=1,
                        tag="amenity=post_office",
                        benchmark=1,
                    ),
                    SubCategory(
                        name="post",
                        sub_weight=0.5,
                        tag="amenity=post_box",
                        benchmark=1,
                    ),
                ],
            ),
            SubCategory(
                name="drugstore",
                sub_weight=0.01,
                tag="shop=drugstore or shop=chemist",
                benchmark=1,
            ),
            SubCategory(
                name="money",
                sub_weight=0.05,
                tag="amenity=atm or amenity=bank",
                benchmark=3,
            ),
            SubCategory(
                name="various",
                sub_weight=0.04,
                tag="shop in (hairdresser, dry_cleaning,  copyshop) or "
                "craft in (shoemaker, tailor, electronics_repair, photographer)",
                benchmark=10,
            ),
        ],
    )

    public_transport = Category(
        weight=0.1,
        subcategories=[
            SubCategory(
                name="bus_stop",
                sub_weight=0.1,
                tag="highway=bus_stop",
                benchmark=4,
            ),
            SubCategory(
                name="tram_stop",
                sub_weight=0.2,
                tag="railway=tram_stop",
                benchmark=2,
            ),
            SubCategory(
                name="train_station",
                sub_weight=0.7,
                tag="station=subway or railway in (station, halt, stop)",
                benchmark=1,
            ),
        ],
    )

    nature_space = Category(
        weight=0.05,
        subcategories=[
            SubCategory(
                name="all",
                sub_weight=1,
                tag="(leisure=garden and (access!=private or garden:type!=residential)) or "
                "leisure=nature_reserve or leisure=park or natural=park or natural=beach or "
                "landuse=grass or landuse=forest",
                benchmark=0.3,  # area percent of nature sapce in isochrone
            ),
        ],
    )

    culture_leisure = Category(
        weight=0.02,
        subcategories=[
            SubCategory(
                name="culture_entertainment",
                sub_weight=0.5,
                tag="amenity in (cinema, library, public_bookcase, community_centre) or "
                "museum=culture or tourism=museum or amenity in (planetarium, theatre, arts_centre)",
                benchmark=culture_leisure_benchmark,
            ),
            SubCategory(
                name="sport_recreation",
                sub_weight=0.5,
                tag="leisure in (fitness_centre, fitness_station, sports_centre, swimming_pool)",
                benchmark=culture_leisure_benchmark,
            ),
        ],
    )

    eating_out = Category(
        weight=0.02,
        subcategories=[
            SubCategory(
                name="restaurants",
                sub_weight=0.4,
                tag="amenity in (restaurant, fast_food, food_court, canteen)",
                benchmark=3,
            ),
            SubCategory(
                name="cafes",
                sub_weight=0.4,
                tag="amenity=cafe",
                benchmark=2,
            ),
            SubCategory(
                name="pubs",
                sub_weight=0.2,
                tag="amenity in (pub, bar, biergarten)",
                benchmark=1,
            ),
        ],
    )

    pets = Category(
        weight=0.01,
        subcategories=[
            SubCategory(
                name="health",
                sub_weight=0.4,
                tag="amenity=veterinary",
                benchmark=1,
            ),
            SubCategory(
                name="leisure",
                sub_weight=0.3,
                tag="leisure=dog_park",
                benchmark=1,
            ),
            SubCategory(
                name="movement",
                sub_weight=0.2,
                tag="(amenity=waste_basket and waste=dog_excrement) or "
                "(amenity=vending_machine and vending=excrement_bags)",
                benchmark=2,
            ),
            SubCategory(
                name="leisure",
                sub_weight=0.1,
                tag="leisure=dog_park",
                benchmark=1,
            ),
        ],
    )
