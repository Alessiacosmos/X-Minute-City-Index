from pathlib import Path

from omegaconf import OmegaConf, DictConfig

from xmin_core.poi_categories import category_settings


def initialize_configs(config_descriptor: Path) -> DictConfig:
    configs = OmegaConf.load(config_descriptor)
    configs.poi_setting = category_settings[configs.poi_setting]

    configs = initialize_xmin_index_settings(configs)

    return configs


def initialize_xmin_index_settings(configs) -> DictConfig:
    xmin_timeframes = configs.xmin_timeframes
    mode_speeds = configs.mode_speeds

    configs.buffer_distance = {
        mode: {t: speed * t * 60 for t in xmin_timeframes}
        for mode, speed in mode_speeds.items()  # m
    }
    configs.max_buffer_distance = max(mode_speeds.values()) * max(xmin_timeframes) * 60

    return configs
