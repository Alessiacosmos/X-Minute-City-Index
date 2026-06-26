#!/bin/bash -l

#SBATCH --job-name xmin:cli_60_cities_quality
#SBATCH --partition=cpu-single
#SBATCH --time=1:00:00
#SBATCH --mem=2gb
#SBATCH --mail-user gefei.kong@heigit.org
#SBATCH --mail-type ALL         # ALL will alert you of job beginning, completion, failure etc
#SBATCH --output=slurm/logs/%x.%j.out


# 1. Dynamically retrieve your workspace path and assign it to a variable
# Replace 'my_workspace' with the exact name you used in 'ws_allocate'
export MY_WORKSPACE=$(ws_find xmin)

uv run xmin_core/cli.py --aoi_descriptor resources/explored_cities.gpkg --aoi_id_col URAU_CODE --config_descriptor configs/default.yaml --output_dir $MY_WORKSPACE --activated_funcs=['quality'] --quality_indicators=['map_saturation']