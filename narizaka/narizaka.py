
import argparse
import sys
import os
import magic
import zipfile
from pathlib import Path
from narizaka.aligner import Aligner
from narizaka.audiobook import AudioBook
from narizaka.transcriber import Transcriber
from faster_whisper.utils import format_timestamp


def print_result(recognized, total):
    print(f'Extracted {recognized/3600:.3f} hours from audio duration of {total/3600:.3f}')
    print(f'It is {(recognized/total)*100:.1f}% of total audio')

def find_books(args):
    supported_mimes =[
        'application/epub+zip',
        'text/xml',
        'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    found_book = None
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
        return [(args.data, item)]
    
    print('Root directory doesn\'t contain any text files, checking subdirectories...\n' )
    found_books = []
    for book_dir in args.data.iterdir():
        if book_dir.is_dir():
            for book_item in book_dir.iterdir():
                if not book_item.is_dir():
                    mimetype = magic.from_file(filename=book_item, mime=True)
                    if mimetype in supported_mimes:
                        found_books.append((book_dir, book_item))
    return found_books

def run():
    parser = argparse.ArgumentParser(description = 'Utility to make audio dataset from  audio and text book')

    
    parser.add_argument('data', type=Path, help='This is path to data directory where each subdirectory\n'
                        'contains only one text file(book format or just text) and audio file/files for this text. '
                        'Audio files could have free folder structure.')
    parser.add_argument('-t',  required=False, type=Path, help='Path to text file(book format or just text)', default=None)
    parser.add_argument('-o',  type=Path, help='Output directory', default=Path('./output/'))
    parser.add_argument('-device',  type=str, help='Device to run on', default='auto')
    parser.add_argument('-c', action='store_true',  help='Cache only mode', default=False)
    parser.add_argument('-sr',  type=int, help='Resample to', default=0)
    parser.add_argument('-columns',  type=str, help='Columns to include, default values is "audio,ipa,sentence,duration", this is all possible columns', default='audio,ipa,sentence,duration')



    args = parser.parse_args()
    if not args.data.is_dir():
        print("-data argument should point to directory")
        sys.exit(-1)

        
    found_books = find_books(args)
    if found_books:
        aligner = Aligner(args.o, args.sr, args.columns)
        print(f"The following books have been found:")
        total_result = [0,0]
        for book in found_books:
            print(book[1])

        transcriber = Transcriber(device=args.device)
        for book in found_books:
            transcriber.add(book[1],  AudioBook(book[0]))

        cache_files = []
        for transcribed in transcriber.transcribe():
                
            #try:
                if args.c:
                    for _, transcribed in transcribed[1]['files'].items():
                        cache_files.append(transcribed['cache'])
                else:
                    result = aligner.run(*transcribed)
                    print(f'Result for book {transcribed[0]}:')
                    print_result(result, transcribed[1]['duration'])
                    total_result[0] += result
                    total_result[1] += transcribed[1]['duration']
            # except Exception as ex:
            #     print(f'Exception with book {book[1]}:\n {str(ex)}')

        if args.c:
            if not args.o.exists():
                os.makedirs(args.o, exist_ok=True)
            archive_path = args.o/(args.data.name +'.zip')
            with zipfile.ZipFile(archive_path , mode="w") as archive:
                for t in cache_files:
                    archive.write(t, arcname='narizaka/' + t.name)
            print(f'\nCache archive have been saved to {archive_path}')

        if len(found_books) > 1 and not args.c:
            print('\nTotal statistic:')
            print_result(total_result[0], total_result[1])
    else:
        print('Have not found any data to process.')



if __name__ == '__main__':
    run()

