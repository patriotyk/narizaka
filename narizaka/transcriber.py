import os
import pathlib
import json
import hashlib
from dataclasses import asdict
from narizaka.utils import convert_media
from narizaka.transcribers.faster_whisper import FasterWhisperTranscriber

class Transcriber():
    def __init__(self, device) -> None:
        self.backend =  FasterWhisperTranscriber(device)
        self.cache_path = pathlib.Path(os.getenv('HOME', '.')) / '.cache/narizaka'
        if not self.cache_path.exists():
            os.makedirs(self.cache_path, exist_ok=True)

    def transcribe(self, audio_book):
        transcribed = []
        for file in audio_book.audio_files:
            transcribed.append(self._transcribe_one(file))
        return transcribed
    
    def calc_current_hash(self, current_file):
        with open(current_file, 'rb') as f:
            data = f.read()
            return hashlib.sha256(data).hexdigest()
    
    def _transcribe_one(self, audio_file):
        sr = 16000
        filename_16, _ = convert_media(audio_file, format='wav', sr=sr)

        cash_file = self.cache_path / pathlib.Path(self.calc_current_hash(audio_file)+'.json')
        if not cash_file.exists():
            print(f'Transcribing {audio_file}')
            result = self.backend.transcribe(filename_16)

            with open(cash_file, 'w') as w:
                data = []
                for r in result.all_words():
                    data.append(asdict(r))
                w.write(json.dumps(data, ensure_ascii=False, indent=4))
        return audio_file, filename_16, cash_file


