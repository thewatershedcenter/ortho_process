#%%
import argparse
import pdal
import os
import json

#%%
def parse_arguments():
    '''parses the arguments, returns args'''

    # init parser
    parser = argparse.ArgumentParser()

    # add args
    parser.add_argument(
        '--indir',
        type=str,
        required=True,
        help='directory of las/z files to merge.'
    )

    parser.add_argument(
        '--outfile',
        type=str,
        required=True,
        help='Path to output laz.'
    )

    parser.add_argument(
        '--extra_dims',
        type=str,
        required=False,
        help='''Extra dimensions in source files to be
        carried through to desttination.  e.g.
        'VARI=double,HeightAboveGround=double'
        '''
    )

    # parse the args
    args = parser.parse_args()

    return(args)


if __name__ == '__main__':


    # parse args
    args = parse_arguments()

    # define reader
    if args.extra_dims:
        reader = pdal.Reader.las(filename=os.path.join(args.indir, '*'),
                        extra_dims=args.extra_dims)
    else:
        reader = pdal.Reader.las(filename=os.path.join(args.indir, '*'))

    # define merge and writer stages        
    merge = pdal.Filter.merge()
    writer = pdal.Writer.las(args.outfile,
                         extra_dims='all')

    pipeline = reader | merge | writer


    pipeline.execute_streaming(chunk_size=10_000)
