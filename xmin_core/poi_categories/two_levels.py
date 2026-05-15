from xmin_core.poi_categories.base import POICatogories, Category, SubCategory

CATEGORY_BENCHMARKS = {
    "commerce": 5,
    "healthcare": 5,
    "education": 5,
    "entertainment": 20,
    "living": 2000,
}


class TwoLvlFacilitiesCategories(POICatogories):
    healthcare = Category()

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
                name="early_education",
                sub_weight=0.5,
                tag="amenity=kindergarten or building=kindergarten",
            ),
            SubCategory(
                name="play",
                sub_weight=0.2,
                tag="amenity=toy_library or leisure=playground or leisure=indoor_play",
            ),
        ],
    )

    daily_living = Category()

    public_transport = Category()

    green_space = Category()

    culture_leisure = Category()

    eating_out = Category()

    pets = Category()

    @staticmethod
    def cate_benchmarks():
        return CATEGORY_BENCHMARKS
