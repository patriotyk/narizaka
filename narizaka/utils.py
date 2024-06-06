import os
import ffmpeg
import tempfile
from retry import retry
from narizaka.audiobook import AudioBook


class AudioTextPair():
    def __init__(self, audio_book:AudioBook, text_book_path:str):
        self.audio_book = audio_book
        self.text_book_path = text_book_path
    

@retry(tries=3, delay=1)
def convert_media(filename, format='flac', sr=None):
    probe = ffmpeg.probe(filename)
    if probe.get('format').get('format_name') != format or probe['streams'][0]['sample_rate'] != str(sr):
        fl, audio_file = tempfile.mkstemp(suffix=f'.{format}')
        os.close(fl)
        stream = ffmpeg.input(filename)
        if sr:
            stream = ffmpeg.output(stream, audio_file, acodec='pcm_s16le' if format == 'wav' else 'flac' , ar=sr, ac=1, loglevel='panic')
        else:
            stream = ffmpeg.output(stream, audio_file,  acodec='pcm_s16le' if format == 'wav' else 'flac' , ac=1, loglevel='panic')
        ffmpeg.run(stream, overwrite_output=True)
        return audio_file, sr or int(probe['streams'][0]['sample_rate'])
    else:
        return filename, int(probe['streams'][0]['sample_rate'])