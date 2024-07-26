import os
import magic
import ffmpeg
import pathlib
import hashlib
import json
from collections import OrderedDict
from glob import glob



class AudioBook():
    def __init__(self, filename: pathlib.Path, speaker_id=None) -> None:
        self.cache_path = pathlib.Path(os.getenv('HOME', '.')) / '.cache/narizaka'
        self.speaker_id = speaker_id
        self.files = OrderedDict()
        self.duration = 0.0
        if not filename.exists():
            raise Exception('Audio path doesn\'t exists')

        if filename.is_dir():
            files = list(glob(f'{filename.resolve()}/**', recursive=True))
            files.sort()
            for f in files:
                f = pathlib.Path(f)
                if not f.is_dir() and self._is_media(f):
                    self._add_file(f)
            if not self.files:
                raise Exception('Directory doesn\'t contain any audio files')
        else:
            if not self._is_media(filename):
                raise Exception('Audio book is not audio file')    
            self._add_file(filename)


    def _add_file(self, filename):
        if self._is_media(filename):
            hash, cache_file = self._calc_hash(filename)
            probe = ffmpeg.probe(filename)
            self.duration += float(probe["format"]["duration"])
            file_dict = {'filename': filename, 'transcribed': False}
            if cache_file.exists():
                file_dict['transcribed'] = True
            self.files[hash] = file_dict
    
    def _calc_hash(self, filename):
        with open(filename, 'rb') as f:
            data = f.read()
            hash = hashlib.sha256(data).hexdigest()
            return hash, self.cache_path / pathlib.Path(hash+'.json')
    
    def is_transcribed(self):
        return not list(self.non_transcribed_files())
    
    def non_transcribed_files(self):
        return filter(lambda x: x['transcribed'] == False, self.files.values())

    def save_transcription(self, filename, transcription):
        hash, cache_file = self._calc_hash(filename)
        if not hash in self.files:
            raise Exception('Can\'t find file in untranscribed list')
        with open(cache_file, 'w') as w:
            data = []
            for r in transcription.all_words():
                data.append(r.to_dict())
            w.write(json.dumps(data, ensure_ascii=False, indent=4))
        self.files[hash]['transcribed'] = True

    def _is_media(self, filename: pathlib.Path)-> bool:
        m = magic.detect_from_filename(filename=filename)
        return  True if (m.mime_type.split('/')[0] == 'audio' or m.mime_type.split('/')[0] == 'video') else True if 'audio' in m.name.lower() else False

    def transcription(self):
        for hash, val in self.files.items():
            cache_file = self.cache_path / pathlib.Path(hash+'.json')
            if not val['transcribed']:
                raise Exception(f'{val["filename"]} is not transcribed')
            yield val['filename'], json.load(open(cache_file, 'r'))

    def get_cache_files(self):
        for hash in self.files.keys():
            yield self.cache_path / pathlib.Path(hash+'.json')