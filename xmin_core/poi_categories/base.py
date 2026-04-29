from enum import Enum


class POICatogories(Enum):
    @classmethod
    def obtain_benchmark(cls, category_name: str):
        """return the benchmark value for each poi category"""
        return cls.cate_benchmarks().get(category_name)

    def obtain_weight(self):
        """return weight of each poi (sub)category"""
        pass
