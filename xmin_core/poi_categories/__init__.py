from xmin_core.poi_categories.sp_healthcare import (
    DEHealthCareCategories,
    NLHealthCareCategories,
    ESHealthCareCategories,
)
from xmin_core.poi_categories.simple import SimpleFacilitiesCategories
from xmin_core.poi_categories.two_levels import TwoLvlFacilitiesCategories

category_settings = {
    "simple": SimpleFacilitiesCategories,
    "two_level": TwoLvlFacilitiesCategories,
    "healthcare_de": DEHealthCareCategories,
    "healthcare_nl": NLHealthCareCategories,
    "healthcare_es": ESHealthCareCategories,
}
