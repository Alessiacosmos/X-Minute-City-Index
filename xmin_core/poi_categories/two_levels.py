from typing import override

from xmin_core.poi_categories.base import POICatogories

CATEGORY_BENCHMARKS = {
        'commerce': 5,
        'healthcare': 5,
        'education': 5,
        'entertainment': 20,
        'living': 2000
    }

class SimpleFacilitiesCategories(POICatogories):
    commerce = {
        'shop': ['supermarket', 'convenience', 'bakery', 'grocery'],
        'amenity': ['marketplace', 'bank', 'post_box', 'atm', 'post_office']
    }

    healthcare = {
        'amenity': ['pharmacy', 'doctors', 'dentist', 'hospital', 'clinic'],
        'leisure': ['park', 'garden', 'fitness_centre', 'fitness_station', 'playground', 'sports_centre'],
        'landuse': ['recreation_ground', 'forest'],
        'club': ['sport'],
    }

    education = {
        'primary': {

        }
        'amenity': ['kindergarten', 'childcare', 'school']
    }

    entertainment = {
        'amenity': ['restaurant', 'fast_food', 'café', 'bar', 'pub', 'ice_cream', 'night_club', 'biergarten', 'library',
                    'theatre', 'museum', 'cinema', 'arts_centre', 'community_centre', 'events_venue'],
        'sport': ['swimming']
    }


    @staticmethod
    def cate_benchmarks():
        return CATEGORY_BENCHMARKS

if __name__ == '__main__':
    print(SimpleFacilitiesCategories.obtain_benchmark('commerce'))
    for category in SimpleFacilitiesCategories:
        print(category.name, category.value)
