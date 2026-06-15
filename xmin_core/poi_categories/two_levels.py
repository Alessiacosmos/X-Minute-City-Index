from xmin_core.poi_categories.base import POICatogories, Category, SubCategory

# todo: refactor it based on newest poi settings
CATEGORY_BENCHMARKS = {
    "commerce": 5,
    "healthcare": 5,
    "education": 5,
    "entertainment": 20,
    "living": 2000,
}


class TwoLvlFacilitiesCategories(POICatogories):
    # todo: the sum of sub_weights in each category is not always 1.0, need to check.
    education = Category(
        weight=0.2,
        subcategories=[
            SubCategory(
                name="primary", sub_weight=0.8, tag="amenity=school and isced:level=1"
            ),
            SubCategory(
                name="secondary",
                sub_weight=0.2,
                tag="amenity=school and (isced:level=2 or isced:level=3)",
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
            ),
            SubCategory(
                name="early_education", sub_weight=0.5, tag="amenity=kindergarten"
            ),
            SubCategory(
                name="play",
                sub_weight=0.2,
                tag="amenity=toy_library or leisure=playground or leisure=indoor_play",
            ),
        ],
    )

    healthcare = Category(
        weight=0.1,
        subcategories=[
            SubCategory(
                name="primary_care",
                sub_weight=0.3,
                tag="(amenity=doctors or healthcare=doctor or amenity=clinic ) and "
                "(healthcare:speciality=general or healthcare:speciality=internal)",
            ),
            SubCategory(
                name="dentist",
                sub_weight=0.2,
                tag="amenity=dentist or healthcare=dentist",
            ),
            SubCategory(
                name="pharmacy",
                sub_weight=0.5,
                tag="amenity=pharmacy or healthcare=pharmacy",
            ),
            SubCategory(
                name="specialist",
                sub_weight=0.1,
                tag="healthcare:speciality=* and (healthcare:speciality!=general or healthcare:speciality=internal)",
            ),
        ],
    )

    daily_living = Category(
        weight=0.4,
        subcategories=[
            # todo: grocery will be seperated to 3 level: large, medium, and specialty. The levels OR following update should consider it.
            SubCategory(name="grocery_large", sub_weight=0.8, tag="shop=supermarket"),
            SubCategory(
                name="grocery_medium",
                sub_weight=0.8,
                tag="amenity=marketplace or shop=convenience",
            ),
            SubCategory(
                name="grocery_specialbase",
                sub_weight=0.8,
                tag="shop in "
                "(cheese, coffee, deli, farm, frozen_food, health_food, organic, "
                "water, bakery, butcher, dairy, food, greengrocer, grocery, seafood)",
            ),
            SubCategory(
                name="grocery_specialluxury",
                sub_weight=0.8,
                tag="shop in (alcohol, beverages, chocolate, ice_cream, pastry, spices, tea, water, wine, confectionery)",
            ),
            # all above are related to groceery
            SubCategory(
                name="post",
                sub_weight=0.1,
                tag="amenity=post_box or amenity=post_office",
            ),
            SubCategory(
                name="drugstore", sub_weight=0.1, tag="shop=drugstore or shop=chemist"
            ),
            SubCategory(
                name="money", sub_weight=0.05, tag="amenity=atm or amenity=bank"
            ),
            SubCategory(
                name="various",
                sub_weight=0.1,
                tag="shop in (hairdresser, dry_cleaning,  copyshop) or "
                "craft in (shoemaker, tailor, electronics_repair, photographer)",
            ),
        ],
    )

    public_transport = Category(
        weight=0.1,
        subcategories=[
            SubCategory(name="bus_stop", sub_weight=0.1, tag="highway=bus_stop"),
            SubCategory(name="tram_stop", sub_weight=0.25, tag="railway=tram_stop"),
            SubCategory(
                name="train_station",
                sub_weight=0.7,
                tag="station=subway or railway=station or railway=halt or railway=stop",
            ),
        ],
    )

    nature_space = Category(
        weight=0.05,
        subcategories=[
            SubCategory(
                name="all",
                sub_weight=1,
                tag="",  # todo, update nature space query tag.
            ),
        ],
    )

    culture_leisure = Category(
        weight=0.02,
        subcategories=[
            SubCategory(
                name="culture_entertainment",
                sub_weight=0.5,
                tag="amenity in (cinema, library, public_bookcase, community_centre) or"
                "museum=culture or tourism=museum or amenity in (planetarium, theatre, arts_centre)",
            ),
            SubCategory(
                name="sport_recreation",
                sub_weight=0.5,
                tag="leisure in (fitness_centre, fitness_station, sports_centre, swimming_pool)",
            ),
        ],
    )

    eating_out = Category()

    pets = Category()

    @staticmethod
    def cate_benchmarks():
        return CATEGORY_BENCHMARKS
