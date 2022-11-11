#%%

import argparse
import pdal
import os
import numpy as np
import subprocess
import json


def parse_arguments():
    '''parses the arguments, returns args'''

    # init parser
    parser = argparse.ArgumentParser()

    # add args
    parser.add_argument(
        '-i', '--fixed',
        type=str,
        required=True,
        help='Path to fixed input file',
    )

    parser.add_argument(
        '-i', '--moving',
        type=str,
        required=True,
        help='Path to input file to be transformed',
    )


    parser.add_argument(
        '--out_file',
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

    # parse the args
    args = parser.parse_args()

    return(args)


def mak_test_args():
    args = argparse.Namespace()
    args.moving = '/home/michael/WRTC/coffee_creek/plots/unit_1_classified_pc_plot_2.laz'
    args.fixed = '/home/michael/WRTC/coffee_creek/plots/USGS_LPC_CA_CarrHirzDeltaFires_2019_B19_Coffee_Creek_plot_2.laz'
    args.outfile = '/home/michael/work/ortho_process/tmp/out.laz'
    args.step = 5

    return(args)



# %%
args = mak_test_args()

# get the srs of moving pc by reading one point
pipeline = pdal.Pipeline()
pipeline |= pdal.Reader.las(filename=args.moving, count=1)
_ = pipeline.execute()
m_srs = pipeline.quickinfo['readers.las']['srs']['wkt']

# now read and decimate the moving input in streaming mode
reader = pdal.Reader.las(filename=args.moving)
range = pdal.Filter.range(limits='Classification[2:2]')
decimator = pdal.Filter.decimation(step=args.step)
pipeline = reader | range | decimator

moving = []
for array in pipeline.iterator():
    moving.append(array)

moving = np.concatenate(moving)

# %%
# read the fixed pc ground returns
reader = pdal.Reader.las(filename=args.fixed)
pipeline = reader | range
n = pipeline.execute()
fixed = pipeline.arrays[0]
f_srs = pipeline.quickinfo['readers.las']['srs']['wkt']

#%%

# now make and run icp pipline on arr and write
icp =  pdal.Filter.icp()
writer = pdal.Writer.las(args.outfile, a_srs=f_srs)

pipeline = icp.pipeline(fixed, moving)
pipeline |= writer

_ = pipeline.execute()



# %%
