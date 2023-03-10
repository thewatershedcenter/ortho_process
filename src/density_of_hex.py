#%%
import geopandas as gpd
import os
import argparse
import pdal
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
        help='File to which density shall be added.'
    )

    parser.add_argument(
        '--out_gpkg',
        type=str,
        required=True,
        help='Output gpkg name.'
    )

    # parse the args
    args = parser.parse_args()

    return(args)


if __name__ == '__main__':

    # parse
    args =  parse_arguments()

    # open file
    df = gpd.read_file(args.infile)

    # calculate density
    df['density'] = df.COUNT / df.geometry.area

    # write file
    df.to_file(args.out_gpkg, driver='GPKG')