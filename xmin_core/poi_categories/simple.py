from xmin_core.poi_categories.base import POICatogories

CATEGORY_BENCHMARKS = {
    "commerce": 5,
    "healthcare": 5,
    "education": 5,
    "entertainment": 20,
    "living": 2000,
}


class SimpleFacilitiesCategories(POICatogories):
    commerce = (
        'shop in (supermarket, convenience, bakery, grocery) or '
        'amenity in (marketplace, bank, post_box, atm, post_office)'
    )

    healthcare = (
        'amenity in (pharmacy, doctors, dentist, hospital, clinic) or '
        'leisure in (park, garden, fitness_centre, fitness_station, playground, sports_centre) or '
        'landuse in (recreation_ground, forest) or '
        'club=sport'
    )

    education = 'amenity in (kindergarten, childcare, school)'

    entertainment = (
        'amenity in '
        '(restaurant, fast_food, café, bar, pub, ice_cream, night_club, biergarten,'
        ' library, theatre, museum, cinema, arts_centre, community_centre, events_venue) or '
        'sport=swimming'
    )

    @staticmethod
    def cate_benchmarks():
        return CATEGORY_BENCHMARKS


if __name__ == "__main__":
    print(SimpleFacilitiesCategories.obtain_benchmark("commerce"))
    for category in SimpleFacilitiesCategories:
        print(category.name, category.value)
