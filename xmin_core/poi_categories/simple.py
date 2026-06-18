from typing import override

from xmin_core.poi_categories.base import POICatogories, Category, SubCategory

CATEGORY_BENCHMARKS = {
    "commerce": 5,
    "healthcare": 5,
    "education": 5,
    "entertainment": 20,
    "population": 2000,
}


class SimpleFacilitiesCategories(POICatogories):
    commerce = Category(
        weight=1,
        subcategories=[
            SubCategory(
                name="all",
                sub_weight=1,
                tag=(
                    "shop in (supermarket, convenience, bakery, grocery) or "
                    "amenity in (marketplace, bank, post_box, atm, post_office)"
                ),
            )
        ],
    )

    healthcare = Category(
        weight=1,
        subcategories=[
            SubCategory(
                name="all",
                sub_weight=1,
                tag=(
                    "amenity in (pharmacy, doctors, dentist, hospital, clinic) or "
                    "leisure in (park, garden, fitness_centre, fitness_station, playground, sports_centre) or "
                    "landuse in (recreation_ground, forest) or "
                    "club=sport"
                ),
            )
        ],
    )

    education = Category(
        weight=1,
        subcategories=[
            SubCategory(
                name="all",
                sub_weight=1,
                tag="amenity in (kindergarten, childcare, school)",
            )
        ],
    )

    entertainment = Category(
        weight=1,
        subcategories=[
            SubCategory(
                name="all",
                sub_weight=1,
                tag=(
                    "amenity in "
                    '(restaurant, fast_food, "café", bar, pub, ice_cream, night_club, biergarten,'
                    " library, theatre, museum, cinema, arts_centre, community_centre, events_venue) or "
                    "sport=swimming"
                ),
            )
        ],
    )

    @override
    @staticmethod
    def cate_benchmarks():
        return CATEGORY_BENCHMARKS


if __name__ == "__main__":
    print(SimpleFacilitiesCategories.obtain_benchmark("commerce"))
    for category in SimpleFacilitiesCategories:
        print(category.name, category.value)
        print(SimpleFacilitiesCategories.obtain_weights_and_benchmarks(category.name))
