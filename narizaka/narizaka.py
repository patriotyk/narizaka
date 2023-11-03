
import argparse
import sys
import magic

from pathlib import Path
from narizaka.aligner import Aligner



def run():
    parser = argparse.ArgumentParser(description = 'Utility to make audio dataset from  audio and text book')

    
    parser.add_argument('-o',  type=Path, help='Output directory', default=Path('./output/'))
    parser.add_argument('-device',  type=str, help='Device to run on', default='auto')
    parser.add_argument('-data',  required=True, type=Path, help='This is path to data directory where each subdirectory\n'
                        'contains only one text file(book format or just text) and audio file/files for this text. '
                        'Audio files could have free folder structure.')


    args = parser.parse_args()
    if not args.data.is_dir():
        print("-data argument should point to directory")
        sys.exit(-1)

    
    supported_mimes =[
        'application/epub+zip',
        'text/xml',
        'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    for item in args.data.iterdir():
        if not item.is_dir():
            mimetype = magic.from_file(filename=item, mime=True)
            if mimetype in supported_mimes:
                aligner = Aligner(args.o, args.device)
                aligner.run(item, args.data)
                break



if __name__ == '__main__':
    run()

