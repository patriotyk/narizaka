
import argparse
import sys
import magic
from datetime import timedelta
from pathlib import Path
from narizaka.aligner import Aligner


def print_result(result):
    recognized, total = result
    print(f'Extracted {timedelta(seconds=recognized)} from audio duration of {timedelta(seconds=total)}')
    print(f'It is {(recognized/total)*100:.3f}% of total audio')

def run():
    parser = argparse.ArgumentParser(description = 'Utility to make audio dataset from  audio and text book')

    
    parser.add_argument('data', type=Path, help='This is path to data directory where each subdirectory\n'
                        'contains only one text file(book format or just text) and audio file/files for this text. '
                        'Audio files could have free folder structure.')
    parser.add_argument('-t',  required=False, type=Path, help='Path to text file(book format or just text)', default=None)
    parser.add_argument('-o',  type=Path, help='Output directory', default=Path('./output/'))
    parser.add_argument('-device',  type=str, help='Device to run on', default='auto')


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
    found_book = None
    aligner = Aligner(args.o, args.device)
    if args.t:
        mimetype = magic.from_file(filename=args.t, mime=True)
        if mimetype in supported_mimes:
            found_book = args.t
        else:
            print('Text file is not suported.\n suported formats are:', supported_mimes)
            sys.exit(-1)
    else:
        for item in args.data.iterdir():
            if not item.is_dir():
                mimetype = magic.from_file(filename=item, mime=True)
                if mimetype in supported_mimes:
                    found_book = item
                    break
    if found_book:
        result = aligner.run(item, args.data)
        print_result(result)
        sys.exit(0)

    print('Root directory doesn\'t contain any text files, checking subdirectories...' )
    found_books = []
    for book_dir in args.data.iterdir():
        if book_dir.is_dir():
            for book_item in book_dir.iterdir():
                if not book_item.is_dir():
                    mimetype = magic.from_file(filename=book_item, mime=True)
                    if mimetype in supported_mimes:
                        found_books.append((book_dir, book_item))
    if found_books:
        print(f"Following books have been found:")
        total_result = [0,0]
        for book in found_books:
            print(book[1])
        for book in found_books:
            result = aligner.run(book[1], book[0])
            print(f'Result for book {book[1]}:')
            print_result(result)
            total_result[0] += result[0]
            total_result[1] += result[1]
        print('Total statistic:')
        print_result(total_result)
    else:
        print('Have not found any data to process.')



if __name__ == '__main__':
    run()

