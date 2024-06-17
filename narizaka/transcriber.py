import os
import pathlib
import torch
import multiprocessing
from collections import OrderedDict
from dataclasses import asdict
from multiprocessing import Queue, Process
from queue import Empty
from narizaka.utils import convert_media
from narizaka.asr_backends.faster_whisper import FasterWhisperTranscriber

multiprocessing.set_start_method('spawn', force=True)

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
            while book_files := self.book_files_queue.get(timeout=10):
                result = self.backend.transcribe(book_files[1])
                self.transcribed.put_nowait({'text_book_filename': book_files[0], 
                                            'audio_file': book_files[1], 
                                            'transcription': result})
        except Empty:
            print('Done worker thread')




class Transcriber():
    def __init__(self, device) -> None:
        self.cache_path = pathlib.Path(os.getenv('HOME', '.')) / '.cache/narizaka'
        if not self.cache_path.exists():
            os.makedirs(self.cache_path, exist_ok=True)

        self.device = 'cuda' if torch.cuda.device_count() > 0 and device != 'cpu' else 'cpu'
        self.audio_files_q = Queue()
        self.transcribed = Queue()
        self.devices = torch.cuda.device_count() if torch.cuda.device_count() > 0 and device != 'cpu' else 2
        self.books = {}

    
    def add(self, pair):
        self.books[pair.text_book_path] = pair
        for audio_file in pair.audio_book.non_transcribed_files():
            self.audio_files_q.put_nowait((pair.text_book_path, audio_file['filename']))
    
    def transcribe(self):
        self.workers = []
        for index in range(self.devices):
            worker = BackendWorker(self.device, index if self.device == 'cuda' else 0, self.audio_files_q, self.transcribed)
            worker.start()
            self.workers.append(worker)

        while any([w.is_alive() for w in self.workers]):
            try:
                transcribed = self.transcribed.get(timeout=20)
                pair = self.books[transcribed['text_book_filename']]
                pair.audio_book.save_transcription(transcribed['audio_file'], transcribed['transcription'] )
                if pair.audio_book.is_transcribed():
                    yield pair
            except Empty:
                pass
