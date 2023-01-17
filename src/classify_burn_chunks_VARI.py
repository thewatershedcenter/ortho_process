#!/bin/python
# 
#%%
import os
import numpy as np
import pdal
import argparse
import subprocess
import json
from time import time
from shapely.geometry import Polygon
from math import ceil
from shapely import wkt
from dask import delayed, compute
from tqdm import tqdm

#%%

def parse_arguments():
    '''parses the arguments, returns args'''

    # init parser
    parser = argparse.ArgumentParser()

    # add args
    parser.add_argument(
        '--infile',
        type=str,
        required=True,
        help='Input copc',
    )

    parser.add_argument(
        '--tile_size',
        type=int,
        required=False,
        default=500,
        help='''Optional. Single integer value determining x and y dimensions of tiles.
        Default=500.Currently only supports square tiles. '''
    )

    parser.add_argument(
        '--vari_thresh',
        type=float,
        required=False,
        default=0.0,
        help='''Triangular Greenness Index value above which
        points will be dropped. Default value is 0.0''',
    )

    parser.add_argument(
        '--csf_rigidness',
        type=float,
        required=False,
        default=1,
        help='Rigidness for CSF filter, defaults to 1'
    )

    parser.add_argument(
        '--csf_step',
        type=float,
        required=False,
        default=1,
        help='Step for CSF filter, defaults to 1'
    )

    # parse the args
    args = parser.parse_args()


    return(args)


def norm_rgb(arr):
    '''returns normed RGB'''
    total = (
        arr['Red'].astype('f8') +
        arr['Green'].astype('f8') +
        arr['Blue'].astype('f8')
    )
    normR = arr['Red'] / total
    normG = arr['Green'] / total
    normB = arr['Blue'] / total

    return(normR, normG, normB)


def get_srs(f):
    '''returns srs of file as wkt using pdal info'''
    cmd = f'pdal info {f} --metadata'
    out = subprocess.run(cmd, shell=True, capture_output=True)
    info = json.loads(out.stdout.decode('utf8'))
    srs = info['metadata']['srs']['wkt']

    return srs

def get_bbox(f):
    '''returns bbox of file as dict using pdal info'''
    cmd = f'pdal info {f} --summary'
    out = subprocess.run(cmd, shell=True, capture_output=True)
    info = json.loads(out.stdout.decode('utf8'))
    bbox = info['summary']['bounds']

    return bbox


def pipe_chunk(filename, poly_wkt, outfile, a_srs):

    # make pipeline
    pipeline = pdal.Reader.copc(filename=filename, polygon=poly_wkt).pipeline()
    
    # execute pipeline
    n = pipeline.execute()

    # if it is an empty chunkl skip it
    if n==0:
        return None

    arr = pipeline.arrays[0]

    # make a new data type with a TGI entry
    new_dt = np.dtype(arr.dtype.descr + [('VARI', 'f8')])

    # make empty new array with same number of entries as old
    new_arr = np.empty(arr.shape, dtype=new_dt)

    # copy data from old array
    for dt in arr.dtype.descr:
        new_arr[dt[0]] = arr[dt[0]]

    # ditch arr to free up memory
    del arr

    #  normalize color ratios
    normR, normG, normB = norm_rgb(new_arr)

    # Visible Atmospherically Resistant Index - Gitelson et al. 2002
    vari  = (normG - normR) / (normG + normR + normB)
    new_arr['VARI'] = vari

    # filter ground and do hag
    ground = pdal.Filter.csf(
        rigidness=args.csf_rigidness,
        step=args.csf_step,
        where=f'VARI < {args.vari_thresh}'
        ).pipeline(new_arr)
    hag = pdal.Filter.hag_nn(count=4)
    pipeline |= hag
    n = pipeline.execute()
    new_arr = pipeline.arrays[0]

    # change classification based on  vari
    classification = new_arr['Classification']
    classification[vari >= args.vari_thresh] = 3
    new_arr['Classification'] = classification
    
    # reclassify any low veg above 2m as med or high veg
    classification = new_arr['Classification']
    classification[(new_arr['Classification'] == 3) &
                   (2 < new_arr['HeightAboveGround']) &
                   (5 > new_arr['HeightAboveGround'])] = 4
    classification[(new_arr['Classification'] == 3) & (5 < new_arr['HeightAboveGround'])] = 5    
    new_arr['Classification'] = classification

    out = os.path.join(
            os.path.dirname(args.infile),
            f'tiled_las_vari_{int(args.vari_thresh * 10)}'
            )
    os.makedirs(out, exist_ok=True)
    out = os.path.join(out, outfile + '.laz')

    writer = pdal.Writer.las(filename=out,
                             extra_dims='all',
                             compression=True,
                             a_srs=a_srs)

    range = pdal.Filter.range(limits='Classification[2:2]')

    out = os.path.join(
            os.path.dirname(args.infile),
            f'tiled_dem4_vari_{int(args.vari_thresh * 10)}'
            )
    os.makedirs(out, exist_ok=True)
    out = os.path.join(out, outfile + '.tif')

    dem_4 = pdal.Writer.gdal(filename=out,
                             resolution=4,
                             output_type='mean',
                             window_size=10
                             )

    out = os.path.join(
            os.path.dirname(args.infile),
            f'tiled_dem1_vari_{int(args.vari_thresh * 10)}'
            )
    os.makedirs(out, exist_ok=True)
    out = os.path.join(out, outfile + '.tif')
   

    dem_1 = pdal.Writer.gdal(filename=out,
                             resolution=1,
                             output_type='mean',
                             window_size=7
                             )

    # execute pipeline
    pipeline = writer.pipeline(new_arr)
    pipeline |= range
    pipeline |= dem_4 
    pipeline |= dem_1
    pipeline.execute()

#%%

if __name__ == '__main__':

    # bag the args
    args = parse_arguments()

    # find the srs and bounds
    srs = get_srs(args.infile)
    bbox = get_bbox(args.infile)

    # calculate height and width
    height = bbox['maxy'] - bbox['miny']
    width = bbox['maxx'] - bbox['minx']

    # number of tiles along each axis
    n_tilesx = ceil(width / args.tile_size)
    n_tilesy = ceil(height / args.tile_size)

    # steps
    xsteps = [bbox['minx'] + args.tile_size * n for n in range(n_tilesx + 1)]
    ysteps = [bbox['maxy'] - args.tile_size * n for n in range(n_tilesy + 1)]

    # empty list for things we will need
    geometry = []
    ids = []

    lazy = []

    for i in tqdm(range(len(ysteps) - 1)):
        for j in range(len(xsteps) -1):

            # get bounds of tile
            ymax = ysteps[i]
            ymin = ysteps[i + 1]
            xmin = xsteps[j]
            xmax = xsteps[j + 1]

            # make tindex polygon
            poly = Polygon(((xmin, ymax),
                            (xmax, ymax),
                            (xmax, ymin),
                            (xmin, ymin),
                            (xmin, ymax)))

            # append to list for later
            geometry.append(poly)
            ids.append(f'{i}_{j}')

            # make las tile  name
            las_tile = f'{i}_{j}'

            # convert poly to wkt string
            poly_wkt = wkt.dumps(poly)

            pipe_chunk(args.infile, poly_wkt, las_tile, srs)

    #with ProgressBar():
    #    _ = compute(**lazy)
# %%
