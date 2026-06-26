from xmin_core.poi_categories.base import POICatogories, Category, SubCategory


class DEHealthCareCategories(POICatogories):
    # todo: update this poi_category setting for Germany (DE)
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


class NLHealthCareCategories(POICatogories):
    # todo: update this poi_category setting for the Netherlands (NL)
    healthcare = Category(
        weight=0.1,
        subcategories=[],
    )


class ESHealthCareCategories(POICatogories):
    # todo: update this poi_category setting for Spain (ES)
    healthcare = Category(
        weight=0.1,
        subcategories=[],
    )
