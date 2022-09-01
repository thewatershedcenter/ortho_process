#!/bin/python
# python skinny_tile.py --ortho=/media/storage/SFM3/South_Fork_Mountain_Phase_1_orthomosaic.tiff --dsm=/media/storage/SFM3/South_Fork_Mountain_Phase_1_dsm.tiff --copc=/media/storage/SFM3/South_Fork_Mountain_Phase_1-dense_point_cloud.copc.laz --tranche_size=250

#%%
import threading
import pdal
from osgeo import gdal
import os
import shutil
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from shapely import wkt
import numpy as np
from dask.distributed import Client, LocalCluster, Lock
from dask.utils import SerializableLock
from dask.diagnostics import ProgressBar
import rioxarray
import argparse


def parse_arguments():
    '''parses the arguments, returns args'''

    # init parser
    parser = argparse.ArgumentParser()

    # add args
    parser.add_argument(
        '--ortho',
        type=str,
        required=True,
        help='''Primary input tiff tiling will be based off of,
        likely and orthophoto.''',
    )

    parser.add_argument(
        '--dsm',
        type=str,
        required=True,
        default=None,
        help='''A dsm, or other tiff that will be tiledin the same
        scheme as ortho, must be same projection as ortho'''
    )

    parser.add_argument(
        '--copc',
        type=str,
        required=True,
        default=None,
        help='''copc pointcloud that will be tiled after ortho,
        must be same projection as ortho.'''
    )

    parser.add_argument(
        '--tranche_size',
        type=int,
        required=False,
        default=500,
        help='''Thickness of tranche along slacing axis.'''
    )

    # TODO: make this arg passable to change slice axis
    parser.add_argument(
        '--axis',
        type=int,
        required=False,
        default=1,
        help='''Axis olong which tif will be sliced, not yet implemented '''
    )

    # TODO: add a --tindex_only flag

    # parse the args
    args = parser.parse_args()

    return args


def clip_and_write(xmin, xmax, ymin, ymax):
    # clip to tile
    ortho_tile = sub_ortho.rio.clip_box(minx=xmin,
                                        miny=ymin,
                                        maxx=xmax,
                                        maxy=ymax)


    dsm_tile = dsm.rio.clip_box(minx=xmin,
                                miny=ymin,
                                maxx=xmax,
                                maxy=ymax)

    # make filename for ortho tile
    dst = os.path.join(ortho_out,
                    f'_{i}_{j}'.join(os.path.splitext(
                            os.path.basename(args.ortho))))

    # write ortho tile
    print(f'writing {dst}')
    with ProgressBar():
        ortho_tile.rio.to_raster(dst, lock=threading.Lock())

    # make filename for dsm tile
    dst = os.path.join(dsm_out,
                    f'_{i}_{j}'.join(os.path.splitext(
                            os.path.basename(args.dsm))))

    # write dsm tile
    print(f'writing {dst}')
    with ProgressBar():
        dsm_tile.rio.to_raster(dst, lock=threading.Lock())


    # make tindex polygon
    poly = Polygon(((xmin, ymax),
                    (xmax, ymax),
                    (xmax, ymin),
                    (xmin, ymin),
                    (xmin, ymax)))

    # append to list for later
    geometry.append(poly)
    id.append(f'{i}_{j}')

    # make las tile  name
    las_tile = f'_{i}_{j}'.join(os.path.splitext(
                            os.path.basename(args.copc)))

    # convert poly to wkt string
    poly = wkt.dumps(poly) + f'/ EPSG:{crs}'

    # make pdal pipeline
    reader = pdal.Reader.copc(args.copc, polygon=poly)
    ground = pdal.Filter.csf(ignore='Classification[7:7]')
    writer = pdal.Writer.las(filename=las_tile)
    pipeline = reader | ground | writer

    # execute pipeline
    results = pipeline.execute()
    print(f'{results} points read within')
    print(poly)

    # move the las file to destination
    # this is due to bug in pdal, will only write to pwd without
    # RuntimeError: writers.las: Couldn't open file ... for output.
    if os.path.isfile(os.path.join(las_out, las_tile)):
        os.remove(os.path.join(las_out, las_tile))
    _ = shutil.move(las_tile, las_out)


    # here you can exctract the points and do python stuff
    #points = pipeline.arrays[0]
    #description = points.dtype.descr


if __name__ == '__main__':
    '''This is very procedural!'''

    # fetch the args
    args = parse_arguments()

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
    tile_size = args.tranche_size
    n_tilesx = int(xlen // tile_size)
    n_tilesy = int(ylen // tile_size)

    # steps
    xsteps = [minx + tile_size * n for n in range(n_tilesx + 1)]
    ysteps = [maxy - tile_size * n for n in range(n_tilesy + 1)]

    # make directories for tiles
    ortho_out = os.path.join(os.path.dirname(args.ortho), 'tiled_ortho')
    os.makedirs(ortho_out, exist_ok=True)

    dsm_out = os.path.join(os.path.dirname(args.dsm), 'tiled_dsm')
    os.makedirs(dsm_out, exist_ok=True)

    las_out = os.path.join(os.path.dirname(args.copc), 'tiled_las')
    os.makedirs(las_out, exist_ok=True)

    # make boxes for clipping
    geometry = []
    id = []

    for i in range(len(ysteps) - 1):
        print(f'loop {i + 1} of {len(ysteps)}')

        ymax = ysteps[i]
        ymin = ysteps[i + 1]
        xmin = minx
        xmax = minx + xlen

        # ranges of pixel coords
        xrange = np.arange(xmin, xmax, res, dtype=np.float64)
        yrange = np.arange(ymax, ymin, -res, dtype=np.float64)

        # get the y tranche
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
            last = -(lasts[lasts > 0].min() - 1)
        except:
            # in case values go all the way to edge
            last = -1

        # now assign the new edges to the tranche
        if args.axis == 0:
            ymin = yrange[first]
            ymax = yrange[last]
        else:
            tile_min = xmin = xrange[first]
            xmax = xrange[last]

            # for each full tile
            width = int((xmax - xmin) // tile_size)
            for j in range(width):

                # label number
                j

                # calculate max edge of tile
                tile_max = tile_min + tile_size
                print()
                print(f'tile{j + 1} of {width} within tranche {i} of {len(ysteps)}')
                print(f'tile x bounds:{int(tile_min)}, {int(tile_max)}')
                print(f'out of: {int(xmax)}, {int(xmax)} for the tranche.')

                # TODO i, j in to clip_and_write to make less confusing
                # clip the tile and write outputs
                clip_and_write(tile_min, tile_max, ymin, ymax)

                # set new tile min
                tile_min = tile_max

            if xmax % tile_size > 0:
                # increment j
                j = j + 1

                # make tile for the remainder
                tile_max = xmax

                print()
                print(j)
                print(int(xmin), int(tile_min), int(tile_max), int(xmax))

                # clip the tile and write outputs
                clip_and_write(tile_min, tile_max, ymin, ymax)

    gdf = pd.DataFrame(id, columns = ['poly_ID'])
    gdf = gpd.GeoDataFrame(gdf, geometry=geometry)
    gdf.crs = f'epsg:{crs}'

    # make filename for tindex
    tindex = os.path.join(os.path.dirname(args.ortho), 'tindex.gpkg')
    print(f'writing {tindex}')
    gdf.to_file(tindex)




