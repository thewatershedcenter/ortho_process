#!/bin/bash

las_dir=$1

# go to the right directory
cd $las_dir
cd ../

# make directory for normalized greeness filtered pointcloud
mkdir -p tiled_ungreen

# drop the high normalised green points
ls $las_dir/*.las | parallel --progress -I{} -j 3 \
python normalize.py \
--infile=./$las_dir/{/.}.las \
--outfile=./tiled_ungreen/{/.}_ungr.las \
--Glim=1.1

# make dirs for  DEMs
mkdir -p tiled_DEM_p2m    # 0.2m resolution
mkdir -p tiled_DEM_1m     # 1.0m resolution

# make 0.2 resolution DEM
ls tiled_ungreen | parallel --progress -I{} -j 3 \
pdal translate tiled_ungreen/{} \
tiled_DEM_p2m/{/.}.tif \
writers.gdal \
--writers.gdal.resolution=0.2 \
--writers.gdal.output_type=mean 

# make 1m resolution DEM
ls tiled_ungreen | parallel --progress -I{} -j 3 \
pdal translate tiled_ungreen/{} \
tiled_DEM_p2m/{/.}.tif \
writers.gdal \
--writers.gdal.resolution=1 \
--writers.gdal.output_type=mean 
