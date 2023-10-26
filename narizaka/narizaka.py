
import argparse

from pathlib import Path
from narizaka.aligner import Aligner



def run():
    parser = argparse.ArgumentParser(description = 'Utility to make audio dataset from  audio and text book')
    parser.add_argument('-t',  type=Path, required=True, help='Path to text version of book can be any book format or just text file')
    parser.add_argument('-a',  type=Path, required=True, help='Path to audio version of book, should be folder that\
                                                               contains all audio files or just single audio file')
    parser.add_argument('-o',  type=Path, help='Output directory', default=Path('./output/'))
    #parser.add_argument('-d',  help='Additionaly generate html report with not recognized items for debugging puposes', action='store_true')

    args = parser.parse_args()



    aligner = Aligner(args.t, args.a)
    aligner.run(args.o)


if __name__ == '__main__':
    run()

