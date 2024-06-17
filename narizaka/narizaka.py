
import argparse
import sys
import os
import zipfile
from pathlib import Path
from narizaka.aligner import Aligner
from narizaka.audiobook import AudioBook
from narizaka.transcriber import Transcriber
from faster_whisper.utils import format_timestamp

from narizaka.data import InputData


def print_result(recognized, total):
    print(f'Extracted {recognized/3600:.3f} hours from audio duration of {total/3600:.3f}')
    print(f'It is {(recognized/total)*100:.1f}% of total audio')


columns = 'audio,speaker_id,sentence,duration'
def run():
    parser = argparse.ArgumentParser(description = 'Utility to make audio dataset from  audio and text book')

    
    parser.add_argument('data', type=Path, help='This is path to data directory where each subdirectory\n'
                        'contains only one text file(book format or just text) and audio file/files for this text. '
                        'Audio files could have free folder structure.')
    parser.add_argument('-t',  required=False, type=Path, help='Path to text file(book format or just text)', default=None)
    parser.add_argument('-o',  type=Path, help='Output directory', default=Path('./output/'))
    parser.add_argument('-device',  type=str, help='Device to run on', default='auto')
    parser.add_argument('-c', action='store_true',  help='Cache only mode', default=False)
    parser.add_argument('-n',  type=int, help='Limit number of CPU workers', default=None)
    parser.add_argument('-sr',  type=int, help='Resample to', default=24000)
    parser.add_argument('-columns',  type=str, help=f'Columns to include, default values is "{columns}", this is all possible columns', default=columns)



    args = parser.parse_args()
    if not args.data.is_dir():
        print("-data argument should point to the directory")
        sys.exit(-1)

        
    input_data = InputData(args)
    if not input_data.is_empty():
        print(f"The following books have been found:")
        total_result = [0,0]
        
        if len(input_data.transcribed_books):
            print('\nFully transcribed:')
            for book_pair in input_data.transcribed_books:
                print(book_pair.audio_book.speaker_id, book_pair.text_book_path)
        if len(input_data.needs_transcribe_books):
            print('\nPartially or not transcribed:')
            for book_pair in input_data.needs_transcribe_books:
                print(book_pair.audio_book.speaker_id, book_pair.text_book_path)

        results = input_data.process()

        if args.c:
            if not args.o.exists():
                os.makedirs(args.o, exist_ok=True)
            archive_path = args.o/(args.data.name +'.zip')
            with zipfile.ZipFile(archive_path , mode="w") as archive:
                for p in input_data.get_all_pairs():
                    for cache_file_path in p.audio_book.get_cache_files():
                        archive.write(cache_file_path, arcname=f'narizaka/'+ cache_file_path.name)
            print(f'\nCache archive have been saved to {archive_path}')
        else:
            for result in results:
                print(f'Result for book {result[2]}:')
                aligned = result[0].get()
                print_result(aligned, result[1])
                total_result[0] += aligned
                total_result[1] += result[1]

            print('\nTotal statistic:')
            print_result(total_result[0], total_result[1])
    else:
        print('Have not found any data to process.')



if __name__ == '__main__':
    run()

