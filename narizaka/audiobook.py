import magic
import os
import ffmpeg
import pathlib
import auditok
import json
import hashlib
from dataclasses import asdict
from narizaka import utils

from stable_whisper.result import WordTiming


class AudioBook():
    def __init__(self, filename: pathlib.Path, model) -> None:
        self.model = model
        self.audio_files = []
        if not filename.exists():
            raise Exception('Audio path doesn\'t exists')
        
        self.cache_path = pathlib.Path(os.getenv('HOME', '.')) / '.cache/narizaka'
        if not self.cache_path.exists():
            os.makedirs(self.cache_path, exist_ok=True)

        if filename.is_dir():
            files = list(filename.rglob("*"))
            files.sort()
            for f in files:
                if not f.is_dir() and self._is_media(f):
                    self.audio_files.append(f)
            if not self.audio_files:
                raise Exception('Directory doesn\'t contain any audio files')
        else:
            if not self._is_media(filename):
                raise Exception('Audio book is not audio file')    
            self.audio_files.append(filename)
        self.duration = 0.0
        for fl in self.audio_files:
            probe = ffmpeg.probe(fl)
            try:
                self.duration += float(probe["format"]["duration"])
            except:
                print(f'Bad file: {fl}')

    
    def _is_media(self, filename: pathlib.Path)-> bool:
        m = magic.detect_from_filename(filename=filename)
        return  True if m.mime_type.split('/')[0] == 'audio' else True if 'audio' in m.name.lower() else False


    def calc_current_hash(self, current_file):
        with open(current_file, 'rb') as f:
            data = f.read()
            return hashlib.sha256(data).hexdigest()
    
    def transcribe(self):
        transcribed = []
        for current_file in self.audio_files:
            sr = 16000
            filename_16, _ = utils.convert_media(current_file, format='wav', sr=sr)

            cash_file = self.cache_path / pathlib.Path(self.calc_current_hash(current_file)+'.json')
            transcribed.append((current_file, filename_16, cash_file))
            if not cash_file.exists():
                print(f'Transcribing {current_file}')
                result = self.model.transcribe_stable(filename_16, input_sr=sr, language='uk', regroup=True,
                                                      prepend_punctuations= "\"'“¿([{-«",
                                                      append_punctuations = "\"'.。,，!！?？:：”)]}、»")

                with open(cash_file, 'w') as w:
                    data = []
                    for r in result.all_words():
                        data.append(asdict(r))
                    w.write(json.dumps(data, ensure_ascii=False, indent=4))

        return transcribed

    
    
