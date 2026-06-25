from dataclasses import dataclass, asdict


@dataclass
class IndicatorParams:
    topic: str
    bpolys: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MapSaturationOrCurrentness(IndicatorParams):
    topicTitle: str
    topicFilter: str


@dataclass
class AttributeCompleteness(IndicatorParams):
    attributeTitle: str
    attributeFilter: str


def get_indicator_params(
    indicator: str,
    topic: str,
    bpolys: dict,
    title: str,
    filter: str,
) -> dict[str, str | dict]:
    match indicator:
        case "map_saturation" | "currentness":
            params = MapSaturationOrCurrentness(
                topic=topic,
                bpolys=bpolys,
                topicTitle=title,
                topicFilter=filter,
            )
        case "attribute_completeness":
            params = AttributeCompleteness(
                topic=topic,
                bpolys=bpolys,
                attributeTitle=title,
                attributeFilter=filter,
            )
        case _:
            raise ValueError(
                f"Invalid indicator: {indicator!r}. "
                "Expected one of: map_saturation, currentness, attribute_completeness"
            )

    return params.to_dict()
