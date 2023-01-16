#%%

import argparse
import pdal
import os
import numpy as np
import time
from tqdm import tqdm
import json


#%%
def parse_arguments():
    '''parses the arguments, returns args'''

    # init parser
    parser = argparse.ArgumentParser()

    # add args
    parser.add_argument(
        '--fixed',
        type=str,
        required=True,
        help='Path to fixed input file',
    )

    parser.add_argument(
        '--moving',
        type=str,
        required=True,
        help='Path to input file to be transformed',
    )


    parser.add_argument(
        '--outfile',
        type=str,
        required=True,
        help='Path for output file'
    )

    parser.add_argument(
        '--step',
        type=int,
        required=True,
        help='Points skipped between sample points in decimation'
    )

    parser.add_argument('-v',
        action='store_true',
        help= 'verbose')

    # parse the args
    args = parser.parse_args()

    return(args)


def mak_test_args():
    args = argparse.Namespace()
    args.moving = '/home/michael/WRTC/coffee_creek/unit_1/unit_1_classified_pc.laz'
    args.fixed = '/home/michael/storage/snc/coffee_creek_overflow/USGS_pointclouds/unit_1_USGS_LPC_CA_CarrHirzDeltaFires.laz'
    args.outfile = '/home/michael/work/ortho_process/tmp/output.laz'
    args.step = 50

    return(args)

#%%


if __name__ == '__main__':

    args = parse_arguments()
    t0 = time.time()

    # get the srs of moving pc by reading one point
    if args.v: print('Getting srs of moving pc.')
    pipeline = pdal.Pipeline()
    pipeline |= pdal.Reader.las(filename=args.moving, count=1)
    _ = pipeline.execute()
    m_srs = pipeline.quickinfo['readers.las']['srs']['wkt']
    n_points = pipeline.quickinfo['readers.las']['num_points']

    # define stages of pipeline
    reader = pdal.Reader.las(filename=args.moving)
    range = pdal.Filter.range(limits='Classification[2:2]')
    decimator = pdal.Filter.decimation(step=args.step)
    pipeline = reader | range | decimator

    # now read and decimate the moving input in streaming mode
    t1 = time.time()
    if args.v: print('Reading and decimating moving pc...')
    moving = []

    chunk = 50_000
    n_iter = n_points // chunk + 1

    with tqdm(total=n_iter) as progress_bar:
        for array in tqdm(pipeline.iterator(chunk_size=chunk)):
            moving.append(array)
            progress_bar.update(1)

    # and concatenate into array
    moving = np.concatenate(moving)
    t2 = time.time()
    if args.v: print(f'Done. That took {round((t2 - t1)/60, 2)} min.')


    # read the fixed pc ground returns
    if args.v: print('Reading fixed pc...')
    reader = pdal.Reader.las(filename=args.fixed)
    pipeline = reader | range
    n = pipeline.execute()
    fixed = pipeline.arrays[0]
    f_srs = pipeline.quickinfo['readers.las']['srs']['wkt']
    t22 = time.time()
    if args.v: print(f'Done. That took {round((t22 - t2)/60, 2)} min.')

    # make filenames for DEMs
    half_m = os.path.splitext(args.outfile)[0] + '_p5m.tif'
    one_m = os.path.splitext(args.outfile)[0] + '_1m.tif'

    
    # now make and  icp / write pipeline
    icp =  pdal.Filter.icp()
    writer = pdal.Writer.las(args.outfile, a_srs=f_srs)

    dem_half = pdal.Writer.gdal(filename=half_m,
        resolution=0.5,
        output_type='mean',
        window_size=15
        )

    dem_1 = pdal.Writer.gdal(filename=one_m,
        resolution=1,
        output_type='mean',
        window_size=15
        )

    pipeline = icp.pipeline(fixed, moving)
    pipeline |= writer
    pipeline |= dem_half
    pipeline |= dem_1


    if args.v: print('Performing ICP...')
    t3 =time.time()
    _ = pipeline.execute()

    out_dir = os.path.dirname(args.outfile)
    base = os.path.splitext(os.path.basename(args.outfile))[0]
    json_path = os.path.join(out_dir, f'{base}_transform.json')

    meta = pipeline.metadata['metadata']['filters.icp']
    with open(json_path, 'w') as f:
        json.dump(meta, f, indent=6)

    if args.v:
        print(f'ICP done. That took {round((t3 - t2)/60, 2)} min.')
        print(f'The entire process took{round((t3 - t0)/60, 2)} min.')


# %%
