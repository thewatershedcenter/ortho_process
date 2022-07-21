#%%
from ast import arg
import threading
import pdal
from osgeo import gdal
import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
import numpy as np

import rioxarray

from dask.distributed import Client, LocalCluster, Lock
from dask.utils import SerializableLock
from dask.diagnostics import ProgressBar

import rioxarray
import argparse
#%%

# path to file
tif = os.path.join('/media', 'storage', 'SFM3', 'South_Fork_Mountain_Phase_1_orthomosaic.tiff')
out_dir = os.path.join('/media', 'storage', 'SFM3', 'tiled_ortho')

args = argparse.Namespace(tif=tif, out_dir=out_dir)

#%%

# open the tif
ortho = rioxarray.open_rasterio(
    args.tif,
    chunks=True,
    lock=False)


# %%

# get spatial info
crs = ortho.rio.crs.to_epsg()
gt = [float(n) for n in ortho.spatial_ref.GeoTransform.split(' ')]
minx = float(gt[0])
maxy = float(gt[3])
res = float(gt[1])

# get x and y len of ortho
xlen = res * ortho.x.shape[0]
ylen = res * ortho.y.shape[0]

# target tile size (in map units)
tile_size = 75
n_tilesx = int(xlen // tile_size)
n_tilesy = int(ylen // tile_size)

# steps
xsteps = [minx + tile_size * n for n in range(n_tilesx + 1)]
ysteps = [maxy - tile_size * n for n in range(n_tilesy + 1)]


#%%




# TODO:
axis = 1





#%%
# make boxes for clipping
geometry = []
id = []

for i in [20]: #range(len(ysteps) - 1):

    ymax = ysteps[i]
    ymin = ysteps[i + 1]
    xmin = minx
    xmax = minx + xlen

    # ranges of pixel coords
    xrange = np.arange(xmin, xmax, res, dtype=np.float64)
    yrange = np.arange(ymax, ymin, -res, dtype=np.float64)

    # get the subset in the y slice
    sub = ortho.rio.clip_box(minx=xmin,
                             miny=ymin,
                             maxx=xmax,
                             maxy=ymax)

    # find the first and last occurence of the valid data on tranche axis
    validity = sub.data[0, ...] > 0
    firsts = validity.argmax(axis=axis)
    try:
        first = firsts[firsts > 0].min().compute()
    except ValueError:
        # in case values go all the way to edge
        first = 0

    if axis == 0:
        val = validity[::-1]
    else:
        val = validity[:, ::-1]

    lasts = val.argmax(axis=axis)

    try:
        last = last = -(lasts[lasts > 0].min() - 1)
    except:
        # in case values go all the way to edge
        last = -1

    # now assign the new edges to the tranche
    if axis == 0:
        ymin = yrange[first]
        ymax = yrange[last]
    else:
        xmin = xrange[first]
        xmax = xrange[last]

    # clip sub down to new edges
    sub = sub.rio.clip_box(minx=xmin,
                           miny=ymin,
                           maxx=xmax,
                           maxy=ymax)

    # make filename for tile
    dst = os.path.join(args.out_dir,
                      f'_{i}'.join(os.path.splitext(os.path.basename(tif))))

    # write tile
    with ProgressBar():
        sub.rio.to_raster(dst, lock=threading.Lock())

    # make tindex polygon
    poly = Polygon(((xmin, ymax),
                    (xmax, ymax),
                    (xmax, ymin),
                    (xmin, ymin),
                    (xmin, ymax)))

    geometry.append(poly)

    id.append(i)

gdf = pd.DataFrame(id, columns = ['poly_ID'])
gdf = gpd.GeoDataFrame(gdf, geometry=geometry)
gdf.crs = f'epsg:{crs}'


# make filename for tindex
base = os.path.basename(tif).split('.')[:-1][0]
tindex = os.path.join(args.out_dir, f'{base}_tindex.gpkg')
gdf.to_file(tindex)
# %%










# %%


# %%
gdf.to_file('/media/storage/SFM3/box.gpkg')