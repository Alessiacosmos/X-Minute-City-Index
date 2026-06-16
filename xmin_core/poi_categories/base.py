from dataclasses import dataclass
from enum import Enum


@dataclass
class SubCategory:
    name: str
    tag: str
    sub_weight: float
    benchmark: float | int | object | None = None


@dataclass
class Category:
    weight: float
    subcategories: list[SubCategory]
    group: str | None = None


class POICatogories(Enum):
    @staticmethod
    def cate_benchmarks():
        pass

    @classmethod
    def obtain_benchmark(cls, category_name: str):
        """return the benchmark value for each poi category"""
        return cls.cate_benchmarks().get(category_name)

    @staticmethod
    def obtain_sub_weights_and_benchmarks(subcategories: list):
        return {
            sub_cate.name: dict(
                weight=sub_cate.sub_weight, benchmark=sub_cate.benchmark
            )
            for sub_cate in subcategories
        }

    @classmethod
    def obtain_weights_and_benchmarks(cls, category_name: str):
        """return weight of each poi (sub)category"""
        category_value: Category = cls[category_name].value
        parent_weight = category_value.weight

        sub_weights = dict()
        for sub_cate in category_value.subcategories:
            if isinstance(sub_cate, Category):
                sub_weights[sub_cate.group] = dict(
                    weight=sub_cate.weight,
                    group=cls.obtain_sub_weights_and_benchmarks(sub_cate.subcategories),
                )
            else:
                sub_weights[sub_cate.name] = dict(
                    weight=sub_cate.sub_weight, benchmark=sub_cate.benchmark
                )

        return dict(
            parent_weight=parent_weight,
            sub_weights_benchmarks=sub_weights,
        )
