from dataclasses import dataclass, field
from enum import Enum
from typing import override


@dataclass
class SubCategory:
    name: str
    tag: str
    sub_weight: float


@dataclass
class Category:
    weight: float
    subcategories: list[SubCategory]




class POICatogories(Enum):
    @classmethod
    def obtain_benchmark(cls, category_name: str):
        """return the benchmark value for each poi category"""
        return cls.cate_benchmarks().get(category_name)

    @classmethod
    def obtain_weights(cls, category_name: str):
        """return weight of each poi (sub)category"""
        category_value: Category = cls[category_name].value
        parent_weight = category_value.weight
        sub_weights = {sub_cate.name: sub_cate.sub_weight for sub_cate in category_value.subcategories}

        return dict(
            parent_weight=parent_weight,
            sub_weights=sub_weights,
        )


