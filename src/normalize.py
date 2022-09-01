#!/bin/python


import numpy as np
import pdal
import argparse
import subprocess
import json


def parse_arguments():
    '''parses the arguments, returns args'''

    # init parser
    parser = argparse.ArgumentParser()

    # add args
    parser.add_argument(
        '--infile',
        type=str,
        required=True,
        help='Input file',
    )

    parser.add_argument(
        '--outfile',
        type=str,
        required=True,
        help='Output file',
    )

    # add args
    parser.add_argument(
        '--Rlim',
        type=float,
        required=False,
        help='Limit of redness above which points will be dropped',
    )

    # add args
    parser.add_argument(
        '--Glim',
        type=float,
        required=False,
        help='Limit of greeness above which points will be dropped',
    )

    # add args
    parser.add_argument(
        '--Blim',
        type=float,
        required=False,
        help='Limit of blueness above which points will be dropped',
    )

    parser.add_argument(
        '--modify',
        help='Normalize the the R, G, B dimensions and return a lasfile',
        action='store_true'
    )

    # parse the args
    args = parser.parse_args()

    return(args)


def norm_rgb(arr):
    '''returns normed RGB on 256 scale'''
    total = arr['Red'] + arr['Green'] + arr['Blue']
    normR = arr['Red'] / total
    normG = arr['Green'] / total
    normB = arr['Blue'] / total

    return(normR, normG, normB)


def norm_rgb_256(arr):
    '''returns normed RGB on 256 scale'''
    total = arr['Red'] + arr['Green'] + arr['Blue']
    normR = 255 * arr['Red'] // total
    normG = 255 * arr['Green'] // total
    normB = 255 * arr['Blue'] // total

    return(normR, normG, normB)


def get_srs(f):
    '''returns srs of file as wkt using pdal info'''
    cmd = f'pdal info {f} --metadata'
    out = subprocess.run(cmd, shell=True, capture_output=True)
    info = json.loads(out.stdout.decode('utf8'))
    srs = info['metadata']['srs']['wkt']

    return srs


if __name__ == '__main__':

    # bag the args
    args = parse_arguments()

    # find the srs
    srs = get_srs(args.infile)

    # read the points
    pipeline = pdal.Reader.las(filename=args.infile).pipeline()
    n = pipeline.execute()
    print(f'{n} points read.')
    arr = pipeline.arrays[0]

# modify the arr and return if that is the aim
if args.modify:
    arr['Red'], arr['Green'], arr['Blue'] = norm_rgb_256(arr)
    msg = f'{args.infile} modified and written to {args.outfile}'

# filter the arr if that is the aim
else:
    normR, normG, normB = norm_rgb(arr)

    if args.Rlim:
        arr = arr[normR <= args.Rlim]

    if args.Glim:
        arr = arr[normG <= args.Glim]

    if args.Blim:
        arr = arr[normB <= args.Blim]

    msg = f'points dropped from {args.infile} based on criteria and results written to {args.outfile}'

pipeline = pdal.Writer.las(filename=args.outfile, a_srs=srs).pipeline(arr)
pipeline.execute()
print(msg)

