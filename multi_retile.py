#%%
import threading

import pdal
from osgeo import gdal
import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
import numpy as np


from dask.distributed import Client, LocalCluster, Lock
from dask.utils import SerializableLock
from dask.diagnostics import ProgressBar
import rioxarray
import argparse

# path to files
ortho = os.path.join('/media', 'storage', 'SFM3', 'South_Fork_Mountain_Phase_1_orthomosaic.tiff')
dsm = os.path.join('/media', 'storage', 'SFM3', 'South_Fork_Mountain_Phase_1_dsm.tiff')
copc = None
out_dir = os.path.join('/media', 'storage', 'SFM3', 'tiled_ortho')
axis = 1

args = argparse.Namespace(ortho=ortho, dsm=dsm, copc=copc, other_tifs=None, out_dir=out_dir, axis=axis)

#%%

# open the ortho
ortho = rioxarray.open_rasterio(
        args.ortho,
        chunks=True,
        lock=False)

# open the dsm
dsm = rioxarray.open_rasterio(
      args.dsm,
      chunks=True,
      lock=False)
# %%

# get spatial info from ortho
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

# make directories for tiles
ortho_out = os.path.join(os.path.dirname(args.ortho), 'tiled_ortho')
os.makedirs(ortho_out, exist_ok=True)

dsm_out = os.path.join(os.path.dirname(args.dsm), 'tiled_dsm')
os.makedirs(dsm_out, exist_ok=True)

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
    sub_ortho = ortho.rio.clip_box(minx=xmin,
                                   miny=ymin,
                                   maxx=xmax,
                                   maxy=ymax)

    # find the first and last occurence of the valid data on tranche axis
    validity = sub_ortho.data[0, ...] > 0
    firsts = validity.argmax(axis=args.axis)
    try:
        first = firsts[firsts > 0].min().compute()
    except ValueError:
        # in case values go all the way to edge
        first = 0

    if args.axis == 0:
        val = validity[::-1]
    else:
        val = validity[:, ::-1]

    lasts = val.argmax(axis=args.axis)

    try:
        last = last = -(lasts[lasts > 0].min() - 1)
    except:
        # in case values go all the way to edge
        last = -1

    # now assign the new edges to the tranche
    if args.axis == 0:
        ymin = yrange[first]
        ymax = yrange[last]
    else:
        xmin = xrange[first]
        xmax = xrange[last]

    # clip subs down to new edges
    sub_ortho = sub_ortho.rio.clip_box(minx=xmin,
                                       miny=ymin,
                                       maxx=xmax,
                                       maxy=ymax)

    sub_dsm = dsm.rio.clip_box(minx=xmin,
                               miny=ymin,
                               maxx=xmax,
                               maxy=ymax)

    # make filename for ortho tile
    dst = os.path.join(ortho_out,
                       f'_{i}'.join(os.path.splitext(
                            os.path.basename(args.ortho))))

    # write ortho tile
    print(f'writing {dst}')
    with ProgressBar():
        sub_ortho.rio.to_raster(dst, lock=threading.Lock())

    # make filename for dsm tile
    dst = os.path.join(dsm_out,
                       f'_{i}'.join(os.path.splitext(
                            os.path.basename(args.dsm))))

    # write dsm tile
    print(f'writing {dst}')
    with ProgressBar():
        sub_dsm.rio.to_raster(dst, lock=threading.Lock())


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
tindex = os.path.join(os.path.dirname(args.ortho), 'tindex.gpkg')
print(f'writing {tindex}')
gdf.to_file(tindex)
# %%










# %%


# %%
gdf.to_file('/media/storage/SFM3/box.gpkg')