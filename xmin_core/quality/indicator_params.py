from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class IndicatorParams:
    topic: str
    bpolys: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CustomTopicParams(IndicatorParams):
    topicTitle: str
    topicFilter: str


@dataclass
class AttributeCompleteness(CustomTopicParams):
    attributeTitle: str
    attributeFilter: str


def get_indicator_params(
    indicator: str,
    topic: str,
    bpolys: dict,
    title: str,
    filter: str,
    attribute_title: Optional[str] = None,
    attribute_filter: Optional[str] = None,
) -> dict[str, str | dict]:
    match indicator:
        case "map_saturation" | "currentness":
            params = CustomTopicParams(
                topic=topic,
                bpolys=bpolys,
                topicTitle=title,
                topicFilter=filter,
            )
        case "attribute_completeness":
            assert (attribute_title is not None) and (attribute_filter is not None), (
                "For attribute_completeness, attribute_tile and attribute_filter shouldn't be empty"
            )
            params = AttributeCompleteness(
                topic=topic,
                bpolys=bpolys,
                topicTitle=title,
                topicFilter=filter,
                attributeTitle=attribute_title,
                attributeFilter=attribute_filter,
            )
        case _:
            raise ValueError(
                f"Invalid indicator: {indicator!r}. "
                "Expected one of: map_saturation, currentness, attribute_completeness"
            )

    return params.to_dict()
