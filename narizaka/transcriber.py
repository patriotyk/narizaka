import os
import pathlib
import json
import hashlib
from collections import OrderedDict
from dataclasses import asdict
from multiprocessing import Queue, Process
from queue import Empty
from narizaka.utils import convert_media
from narizaka.asr_backends.faster_whisper import FasterWhisperTranscriber

class BackendWorker(Process):
    def __init__(self, device, device_index, book_files_queue, output_queue) -> None:
        
        self.book_files_queue = book_files_queue
        self.transcribed = output_queue
        self.device = device
        self.device_index = device_index
        super().__init__()
    

    def run(self):
        self.backend = FasterWhisperTranscriber(self.device, self.device_index)
        try:
            while book_files := self.book_files_queue.get_nowait():
                sr = 16000
                filename_16, _ = convert_media(book_files[1], format='wav', sr=sr)
                print(f'Transcribing {book_files[1]}')
                self._transcribe_one(filename_16, book_files[2])
                self.transcribed.put_nowait({'text_book_filename': book_files[0], 
                                            'audio_16': filename_16, 
                                            'audio_file': book_files[1], 
                                            'cache_file': book_files[2]})
        except Empty:
            self.transcribed.put_nowait(None)

    def _transcribe_one(self, filename_16, cache_file):
        
        result = self.backend.transcribe(filename_16)
        with open(cache_file, 'w') as w:
            data = []
            for r in result.all_words():
                data.append(asdict(r))
            w.write(json.dumps(data, ensure_ascii=False, indent=4))



class Transcriber():
    def __init__(self, device) -> None:
        self.cache_path = pathlib.Path(os.getenv('HOME', '.')) / '.cache/narizaka'
        if not self.cache_path.exists():
            os.makedirs(self.cache_path, exist_ok=True)

        self.device = device
        self.audio_files_q = Queue()
        self.transcribed = Queue()
        self.devices = 2# torch.cuda.device_count()
        self.books = {}

    def calc_current_hash(self, current_file):
        with open(current_file, 'rb') as f:
            data = f.read()
            return hashlib.sha256(data).hexdigest()
    
    def add(self, text_book_path, audio_book):
        self.books[text_book_path] = {
            'duration': audio_book.duration,
            'files': OrderedDict()
        }
        for audio_file in audio_book.audio_files:
            cash_file = self.cache_path / pathlib.Path(self.calc_current_hash(audio_file)+'.json')
            if cash_file.exists():
                self.books[text_book_path]['files'][audio_file] = {'cache': cash_file, 'audio_16': None}
            else:
                self.books[text_book_path]['files'][audio_file] = {'cache': None, 'audio_16': None}
                self.audio_files_q.put_nowait((text_book_path, audio_file, cash_file,))
        

    
    def transcribe(self):
        self.workers = []
        for index in range(self.devices):
            worker = BackendWorker(self.device, index, self.audio_files_q, self.transcribed)
            worker.start()
            self.workers.append(worker)
        try:
            while transcribed := self.transcribed.get():
                self.books[transcribed['text_book_filename']]['files'][transcribed['audio_file']] =  {'cache': transcribed['cache_file'], 'audio_16': transcribed['audio_16']}
                if all([ v.get('cache')  for v in self.books[transcribed['text_book_filename']]['files'].values()]):
                    yield transcribed['text_book_filename'], self.books[transcribed['text_book_filename']]
                    del self.books[transcribed['text_book_filename']]
        except Empty:
            pass
        for text_book, audio_files in self.books.items():
            yield text_book, audio_files
    

    



