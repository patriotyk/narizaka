import magic
import sys
from tqdm import tqdm
from multiprocessing import Pool
from narizaka.audiobook import AudioBook
from narizaka.transcriber import Transcriber
from narizaka.aligner import Aligner
from narizaka.utils import AudioTextPair


class InputData():
    supported_mimes =[
            'application/epub+zip',
            'text/xml',
            'text/plain',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]

    def __init__(self, args):
        self.args = args
        self.transcribed_books = []
        self.needs_transcribe_books = []
        self.transcriber = None
        found_book = None
        if args.t:
            mimetype = magic.from_file(filename=args.t, mime=True)
            if mimetype in self.supported_mimes:
                found_book = args.t
            else:
                print('Text file is not suported.\n suported formats are:', self.supported_mimes)
                sys.exit(-1)
        else:
            for item in args.data.iterdir():
                if not item.is_dir():
                    mimetype = magic.from_file(filename=item, mime=True)
                    if mimetype in self.supported_mimes:
                        found_book = item
                        break
        if found_book:
            self._make_and_add_book_pair(AudioBook(args.data), item)
            return

        items = list(args.data.iterdir())
        for speaker_id, book_or_group in enumerate(tqdm(items, desc='Discovering data')):
            if book_or_group.is_dir():
                if found_book:=self._find_one_book(book_or_group):
                    self._make_and_add_book_pair(AudioBook(book_or_group,  speaker_id=speaker_id), found_book)
                else:
                    for group_item in book_or_group.iterdir():
                        if group_item.is_dir():
                            if found:=self._find_one_book(group_item):
                                self._make_and_add_book_pair(AudioBook(group_item,  speaker_id=speaker_id), found)

    def _find_one_book(self, book_dir):
        for book_item in book_dir.iterdir():
                if not book_item.is_dir():
                    mimetype = magic.from_file(filename=book_item, mime=True)
                    if mimetype in self.supported_mimes:
                        return book_item
        return None 
    
    def get_all_pairs(self):
        return self.transcribed_books + self.needs_transcribe_books

    def _make_and_add_book_pair(self, audio_book, text_book_path):
        p = AudioTextPair(audio_book, text_book_path)
        if audio_book.is_transcribed():
            self.transcribed_books.append(p)
        else:
            t = self._get_transcriber()
            t.add(p)
            self.needs_transcribe_books.append(p)

    def _get_transcriber(self):
        if not self.transcriber:
            self.transcriber = Transcriber(self.args)
        return self.transcriber
    
    def is_empty(self):
        return not len(self.transcribed_books) and not len(self.needs_transcribe_books)

    def process(self):
        results = []
        with Pool(processes=self.args.n) as pool:
            for pair in self.transcribed_books:
                result = pool.apply_async(Aligner(self.args).run, (pair,))
                results.append((result, pair.audio_book.duration, pair.text_book_path))
            if self.needs_transcribe_books:
                transcriber = self._get_transcriber()
                for pair in transcriber.transcribe():
                    if not self.args.c:
                        result = pool.apply_async(Aligner(self.args).run, (pair,))
                        results.append((result, pair.audio_book.duration, pair.text_book_path))
            pool.close()
            pool.join()
            return results

        

