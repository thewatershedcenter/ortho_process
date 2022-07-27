#!/bin/python

# python arbitrary_tindex_blaster.py --tindex=/media/storage/SFM3/tindex.gpkg --raster_to_blast=/media/storage/SFM3/South_Fork_Mountain_Phase_1_dsm.tiff --output_dir=/media/storage/tmp/BLASTED

import threading
import argparse
import geopandas as gpd
import xarray as xr
import rioxarray
from shapely import wkt
import numpy as np
import os
from dask.diagnostics import ProgressBar


def parse_arguments():
    '''parses the arguments, returns args'''

    # init parser
    parser = argparse.ArgumentParser()

    # add args
    parser.add_argument(
        '--tindex',
        type=str,
        required=True,
        help='Tile index which shall dictate the geometry of the blasting',
    )

    parser.add_argument(
        '--raster_to_blast',
        type=str,
        required=True,
        default=None,
        help='Raster which shall be blasted to bits!!!'
    )

    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        default=None,
        help='Directory where the blasted bits will be collected.'
    )

    # parse the args
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    '''Blast it brodyweasel!!!'''

    # parse the dang args!
    args = parse_arguments()

    # makes ure dir is there
    os.makedirs(args.output_dir, exist_ok=True)

    # read the tindex
    tindex = gpd.read_file(args.tindex)

    print()
    print('|^^^^^\  |||         ^         /^^^^^  ||||||||||||    ')
    print('|      | |||        / \\       |            |||  ')
    print('|      | |||       /   \\      \\            |||')
    print('|_____/  |||      /     \\      \\___        |||')
    print('|     \  |||     /_______\\         \\       |||')
    print('|      | |||    /---------\\         \\      |||')
    print('|      | |||   /           \\         |     |||')
    print('|      | |||  /             \\        /     |||')
    print('|_____/  ||| /               \\  ____/      |||')
    print()
    print(f'Blastin\' {args.raster_to_blast}!!!!!!!!!!!!!!!!!!!')

    # open the tif
    raster = rioxarray.open_rasterio(args.raster_to_blast, chunks=True, lock=False)

    for  j, g in enumerate(tindex.geometry):

        # some feedback
        print()
        print(f'YO!!! on tile {j} of {len(tindex)}')

        x, y = g.exterior.coords.xy

        tile = raster.rio.clip_box(minx=np.min(x),
                                miny=np.min(y),
                                maxx=np.max(x),
                                maxy=np.max(y))

        # make filename for tile
        dst = os.path.join(args.output_dir,
                        f'_{tindex.poly_ID[j]}'.join(os.path.splitext(
                                os.path.basename(args.raster_to_blast))))

        # write tile
        with ProgressBar():
            tile.rio.to_raster(dst, lock=threading.Lock())
