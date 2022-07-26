# High resolution ortho imagery and pointcloud processing tools #

## UAV ortho processing workflow ##
1. Run `skinny_tile.py`. It will retile the orthophoto, DSM, and pointcloud into the same tiling scheme.  It will also create a tile index. It does this by reading a slice (from henceforth, and within the scripts comments,  called a _tranche_ in order to avoid confusion with the notion of an array slice in python) of each the orthophoto and the DSM into respective arrays,  then finding the range of valid data within that slice along the axis perpendicular to the tranche.  The extent of the data arrays within the tranche is then adjusted to the new bounds.  Then, for each tranche the arrays are clipped as squares and written to tiles.  The tiles are saved as polygons which are then used to a) create tiled point clouds by reading windows of the input pointcloud (formatted as copc) and b) create the tile index.

It requires the orthophoto, DSM and pointcloud as arguments.  Otionally one may specify the `--tranche_size` argument which determins the thickness of the tranche in map units.  The default tranche thickness is 500. In the case of a high resolution image and map units of meters can be a very large file and may exhaust memory on some machines.  In the future it will be possible to choose which axis the initial slicing will take place, but at the moment it always occurs along the y axis.

The tiled data will be written to their own directories within the directory housing the orthophoto.  If the orthophoto, DSM and pointcloud are called `ortho.tif`, `dsm.tif`, and `points.copc.las`, and are all in the same directory, called `data`,  after running `skinny_tile.py` that directory will have a structure like:

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

2. Run `create_dsm.sh`