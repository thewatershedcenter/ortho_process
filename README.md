# High resolution ortho imagery and pointcloud processing tools #

## UAV ortho processing workflow ##
1. Run `skinny_tile.py`. It will retile the orthophoto, DSM, and pointcloud into the same tiling scheme.  It will also create a tile index. It does this by reading a slice (from henceforth, and within the scripts comments,  called a _tranche_ in order to avoid confusion with the notion of an array slice in python) of each the orthophoto and the DSM into respective arrays,  then finding the range of valid data within that slice along the axis perpendicular to the tranche.  The extent of the data arrays within the tranche is then adjusted to the new bounds.  Then, for each tranche the arrays are clipped as squares and written to tiles.  The tiles are saved as polygons which are then used to a) create tiled point clouds by reading windows of the input pointcloud (formatted as copc) and b) create the tile index.

It requires the orthophoto, DSM and pointcloud as arguments.  Otionally one may specify the `--tranche_size` argument which determins the thickness of the tranche in map units.  The default tranche thickness is 500. In the case of a high resolution image and map units of meters can be a very large file and may exhaust memory on some machines.  In the future it will be possible to choose which axis the initial slicing will take place, but at the moment it always occurs along the y axis.

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
    |__tiled_dsm
    |            |__dsm_0_0.tif
    |            |__dsm_0_1.tif
    |            |__ ...
    |            |__dsm_22_3.tif
    |__tiled_points
                 |__points_0_0.las
                 |__points_0_1.las
                 |__ ...
                 |__points_22_3.las
```

2. Run `normalize.py`.  Create a directory for pointclouds with high normalized greeness points removed.  Set the upper limit of normalized green (`--Glim`) to remove (most of) points that are vegetation.  Typically 1.1 or 1.2 is a reasonable value for `--Glim` but the needed value will vary across diffent landcover types and seasons.

For this example we will call the output directory `tiled_ungreen` and working in the directory structure created in step 1. Due to the fact that `normalize.py' is single threaded the process will be sped up greatly by running the tiles in parallel. Here we use GNU parallel, but it could be parallelized in other ways, or just run in a for loop:

```
ls tiled_points | parallel --progress -I{} -j 3 \
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
    |__tiled_dsm___
    |              |__dsm_0_0.tif
    |              |__dsm_0_1.tif
    |              |__ ...
    |              |__dsm_22_3.tif
    |__tiled_points
    |              |__points_0_0.las
    |              |__points_0_1.las
    |              |__ ...
    |              |__points_22_3.las
    |__tiled_ungreen
                   |__points_0_0_ungr.las
                   |__points_0_1_ungr.las
                   |__ ...
                   |__points_22_3_ungr.las
```






2. Run `create_dsm.sh`.  __NOT YET COMPLETE__ This takes the tiled_points directory as input and creates three new directories of outputs.  The first, `tiled_ungreen` contains tiled pointclouds with in which normailzed greenness ab