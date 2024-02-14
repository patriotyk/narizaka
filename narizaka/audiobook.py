import magic
from glob import glob
import ffmpeg
import pathlib



class AudioBook():
    def __init__(self, filename: pathlib.Path, speaker_id=None) -> None:
        self.speaker_id = speaker_id
        self.audio_files = []
        if not filename.exists():
            raise Exception('Audio path doesn\'t exists')

        if filename.is_dir():
            files = list(glob(f'{filename.resolve()}/**', recursive=True))
            files.sort()
            for f in files:
                f = pathlib.Path(f)
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

