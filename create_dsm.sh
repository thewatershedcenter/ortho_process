#!/bin/bash

las_dir=$1
threads=$2
srs=$3

# go to the right directory
cd $las_dir
cd ../

# make dirs for  DEMs
mkdir -p tiled_DEM_p2m    # 0.2m resolution
mkdir -p tiled_DEM_1m     # 1.0m resolution

# make 0.2 resolution DEM
ls $las_dir | parallel --progress -I{} -j $threads \
pdal translate $las_dir/{} \
tiled_DEM_p2m/{/.}_p2m.tif \
--writer writers.gdal \
--writers.gdal.resolution=0.2 \
--writers.gdal.output_type=mean
--writers.default_srs=$srs

# make 1m resolution DEM
ls $las_dir | parallel --progress -I{} -j $threads \
pdal translate $las_dir/{} \
tiled_DEM_1m/{/.}_1m.tif \
--writer writers.gdal \
--writers.gdal.resolution=1 \
--writers.gdal.output_type=mean
--writers.default_srs=$srs