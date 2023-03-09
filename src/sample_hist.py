import matplotlib.pyplot as plt
import rasterio
import numpy as np
import geopandas as gpd
import argparse


def parse_arguments():
    '''parses the arguments, returns args'''

    # init parser
    parser = argparse.ArgumentParser()

    # add args
    parser.add_argument(
        '--points',
        type=str,
        required=True,
        help='OGR readable file of points to sample.'
    )

    parser.add_argument(
        '--rastA',
        type=str,
        required=True,
        help='Raster A.'
    )

    parser.add_argument(
        '--rastB',
        type=str,
        required=True,
        help='Raster B.'
    )

    parser.add_argument(
        '--outfile',
        type=str,
        required=True,
        help='Output file name.'
    )

    # parse the args
    args = parser.parse_args()

    return(args)


if __name__ == '__main__':

    # parse args
    args =  parse_arguments()

    # get points
    df = gpd.read_file(args.points)
    coord_list = [(x, y) for x, y in zip(df.geometry.x, df.geometry.y)]
    
    # sample rasters
    with rasterio.open(args.rastA) as src:
        samp1 = [val for val in src.sample(coord_list)]

    with rasterio.open(args.rastB) as src:
        samp2 = [val for val in src.sample(coord_list)]

    # calc rmse
    diff = np.subtract(samp1, samp2)
    square=np.square(diff)
    mse=square.mean()
    rmse=np.sqrt(mse)
    print(f'RMSE for samples at the {len(df)} points provided is {rmse}')

    # make hist
    plt.hist(diff, color='grey', ec='k');
    plt.xlabel('Difference (m)')
    plt.title(f'Error at {len(df)} sample points')
    plt.annotate(
    f'RMSE: {round(rmse, 2)}',
    xy=(
        diff.min() + 2 *(diff.max() - diff.min()) /30,
        4
        )
    )

    plt.savefig(args.outfile)
    plt.show()

