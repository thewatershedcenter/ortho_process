#!/bin/python
# 
#%%
import os
import numpy as np
import pdal
import argparse
import subprocess
import json
from osgeo import gdal
from time import time

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
        help='Input file. laz or las',
    )

    parser.add_argument(
        '--outfile',
        type=str,
        required=True,
        help='Output tif',
    )

    parser.add_argument(
        '--tr',
        type=str,
        required=True,
        help='File from which target resolution will be determined',
    )

    # parse the args
    args = parser.parse_args()

    return(args)


def norm_rgb(arr):
    '''returns normed RGB'''
    total = arr['Red'] + arr['Green'] + arr['Blue']
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


def get_tr(f):
    ras =  rasterio.open(f)
    gt = ras.transform
    tr = f'-tr {gt[0]} {gt[4]}'
    txe = f'-txe {ras.bounds.left} {ras.bounds.right}'
    tye = f'-tye {ras.bounds.bottom} {ras.bounds.top}'
    ras.close()

    return(tr, txe, tye)


if __name__ == '__main__':

    # start time
    t0 = time()

    # bag the args
    args = parse_arguments()

    # find the srs
    srs = get_srs(args.infile)

    # read the points
    pipeline = pdal.Reader.las(filename=args.infile).pipeline()
    n = pipeline.execute()
    print(f'\n{n} points read.')
    arr = pipeline.arrays[0]

    #  normalize color ratios
    normR, normG, normB = norm_rgb(arr)

    # calc triangular greenness index
    tgi = normG - 0.39 * normR - 0.61 * normB

    # threshold for dropping TGI
    # TODO: move to args 
    thresh = 0.10

    # make a new data type with a TGI entry
    new_dt = np.dtype(arr.dtype.descr + [('TGI', 'f8')])

    # make mepty new array with same number of entries as old
    new_arr = np.empty(arr.shape, dtype=new_dt)

    # copy data from old array
    for dt in arr.dtype.descr:
        new_arr[dt[0]] = arr[dt[0]]

    # add TGI dimmension data
    new_arr['TGI'] = tgi

    # drop points with TGI > thresh
    new_arr = new_arr[new_arr['TGI'] <= thresh]

    # print message regarding how many points droped based on TGI
    msg = f'{n - new_arr.shape[0]} points dropped based on TGI.'
    print(msg)

    # params
    # TODO: move to args
    window = 10
    slope = 0.13
    threshold = 0.35
    scalar = 0.9
    resolution=10.0217100000000000001

    # create ground filter
    ground = pdal.Filter.smrf(window=window,
                              slope=slope,
                              threshold=threshold,
                              scalar=scalar)

    # make into pipeline
    pipeline = ground.pipeline(new_arr)

    # execute ground filter pipeline
    m = pipeline.execute()

    # overwrite new_arr with classified pc
    new_arr = pipeline.arrays[0]

    # drop not-ground
    new_arr = new_arr[new_arr['Classification'] == 2]

    # print message wrt number of points
    msg = (f'{m - new_arr.shape[0]} non-ground points dropped.'
           + f'\nThere are {new_arr.shape[0]} ground points.'
           + f'\n--- Elapsed time: {round(time() - t0, 1)} seconds ---'
           + '\nInterpolating DEM may take a while ...')
    print(msg)

    # create writer
    writer = pdal.Writer.gdal(filename=args.outfile,
                              resolution=resolution,
                              dimension='Z',
                              output_type='max',
                              window_size=40,
                              default_srs=srs)



    # execute pipeline to create DEM
    pipeline = writer.pipeline(new_arr) 
    pipeline.execute()

    msg = (f'Results written to {args.outfile}'
           + f'\n--- Total time: {round((time() - t0) / 60, 2)} minutes ---')
    print(msg)

