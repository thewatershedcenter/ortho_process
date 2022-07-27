# High resolution ortho imagery and pointcloud processing tools #

## UAV ortho processing workflow ##
1. Run `skinny_tile.py`. It will retile the orthophoto, DSM, and pointcloud into the same tiling scheme.  It will also create a tile index. It does this by reading a slice (from henceforth, and within the scripts comments,  called a _tranche_ in order to avoid confusion with the notion of an array slice in python) of each the orthophoto and the DSM into respective arrays,  then finding the range of valid data within that slice along the axis perpendicular to the tranche.  The extent of the data arrays within the tranche is then adjusted to the new bounds.  Then, for each tranche the arrays are clipped as squares and written to tiles.  The tiles are saved as polygons which are then used to a) create tiled point clouds by reading windows of the input pointcloud (formatted as copc) and b) create the tile index.

It requires the orthophoto, DSM and pointcloud as arguments.  Optionally one may specify the `--tranche_size` argument which determines the thickness of the tranche in map units.  The default tranche thickness is 500. In the case of a high resolution image and map units of meters can be a very large file and may exhaust memory on some machines.  In the future it will be possible to choose which axis the initial slicing will take place, but at the moment it always occurs along the y axis.

The tiled data will be written to their own directories within the directory housing the orthophoto.  If the orthophoto, DSM and pointcloud are called `ortho.tif`, `dsm.tif`, and `points.copc.laz`, and are all in the same directory, called `data`,  after running `skinny_tile.py` like so:

```
python skinny_tile.py \
--ortho=ortho.tif \
--dsm=dsm.tif \
--copc=points.copc.laz \
```

that directory will have a structure like:

```
data/
    |__ortho.tif
    |__dsm.tif
    |__points.copc.las
    |__tindex.gpkg
    |__tiled_ortho
    |            |__ortho_0_0.tif
    |            |__ortho_0_1.tif
    |            |__ ...
    |            |__ortho_22_3.tif
    |
    |__tiled_dsm
    |            |__dsm_0_0.tif
    |            |__dsm_0_1.tif
    |            |__ ...
    |            |__dsm_22_3.tif
    |
    |__tiled_points
                 |__points_0_0.laz
                 |__points_0_1.laz
                 |__ ...
                 |__points_22_3.laz
```

2. Run `normalize.py`.  Create a directory for pointclouds with high normalized greenness points removed.  Set the upper limit of normalized green (`--Glim`) to remove (most of) points that are vegetation.  Typically 1.1 or 1.2 is a reasonable value for `--Glim` but the needed value will vary across different landcover types and seasons.

For this example we will call the output directory `tiled_ungreen` and working in the directory structure created in step 1. Due to the fact that `normalize.py' is single threaded the process will be sped up greatly by running the tiles in parallel. Here we use GNU parallel, but it could be parallelized in other ways, or just run in a for loop:

```
ls tiled_points | parallel --progress -I{} -j 12 \
python normalize.py \
--infile=tiled_points/{} \
--outfile=tiled_ungreen/{/.}_ungr.las \
--Glim=1.1
```

This results in the following directory structure:
```
data/
    |__ortho.tif
    |__dsm.tif
    |__points.copc.las
    |__tindex.gpkg
    |__tiled_ortho_
    |              |__ortho_0_0.tif
    |              |__ortho_0_1.tif
    |              |__ ...
    |              |__ortho_22_3.tif
    |
    |__tiled_dsm___
    |              |__dsm_0_0.tif
    |              |__dsm_0_1.tif
    |              |__ ...
    |              |__dsm_22_3.tif
    |
    |__tiled_points
    |              |__points_0_0.laz
    |              |__points_0_1.laz
    |              |__ ...
    |              |__points_22_3.laz
    |
    |__tiled_ungreen
                   |__points_0_0_ungr.las
                   |__points_0_1_ungr.las
                   |__ ...
                   |__points_22_3_ungr.las
```



3. Run `create_dsm.sh`.  This takes two positional arguments, the directory of input point cloud files, in this case `tiled_ungreen`, and the number of threads to use.  It creates two new directories of outputs.  The first, `tiled_DEM_p2m` contains tiled 0.2m DEMs, the second `tiled_DEM_1m` contains tiled 1m DEMs. For example if we want to use 12 threads:

```
./create_dsm.sh data/tiled_ungreen 12
```

This results in the following directory structure:
```
data/
    |__ortho.tif
    |__dsm.tif
    |__points.copc.las
    |__tindex.gpkg
    |__tiled_ortho_
    |              |__ortho_0_0.tif
    |              |__ortho_0_1.tif
    |              |__ ...
    |              |__ortho_22_3.tif
    |
    |__tiled_dsm___
    |              |__dsm_0_0.tif
    |              |__dsm_0_1.tif
    |              |__ ...
    |              |__dsm_22_3.tif
    |
    |__tiled_points
    |              |__points_0_0.laz
    |              |__points_0_1.laz
    |              |__ ...
    |              |__points_22_3.laz
    |
    |__tiled_ungreen
    |              |__points_0_0_ungr.las
    |              |__points_0_1_ungr.las
    |              |__ ...
    |              |__points_22_3_ungr.las
    |
    |__tiled_DEM_p2m
    |              |__points_0_0_ungr.tif
    |              |__points_0_1_ungr.tif
    |              |__ ...z`
    |              |__points_22_3_ungr.tif
    |
    |__tiled_DEM_1m
                   |__points_0_0_ungr.tif
                   |__points_0_1_ungr.tif
                   |__ ...
                   |__points_22_3_ungr.tif
```

4. Make vrts for the DEMs using `gdalbuildvrt`. Something like this:

```
gdalbuildvrt tiled_DEM_1m/sfm_dem_1m.vrt tiled_DEM_1m/*.tif
gdalbuildvrt tiled_DEM_p2m/sfm_dem_p2m.vrt tiled_DEM_p2m/*.tif
```

This will add the vrts to the DEM directories:

```
...
    |
    |__tiled_DEM_p2m
    |              |__points_0_0_ungr.tif
    |              |__points_0_1_ungr.tif
    |              |__ ...z`
    |              |__points_22_3_ungr.tif
    |              |__sfm_dem_1m.vrt 
    |
    |__tiled_DEM_1m
                   |__points_0_0_ungr.tif
                   |__points_0_1_ungr.tif
                   |__ ...
                   |__points_22_3_ungr.tif
                   |__sfm_dem_p2m.vrt
```

5. fill in the missing data in DEMs from most recent 3DEP

6. Make slope maps from the DEMs:

```
gdaldem slope $SRC $DST -alg Horn
```
