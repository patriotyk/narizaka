import os
import ffmpeg
import tempfile
from retry import retry

@retry(tries=3, delay=1)
def convert_media(filename, format='flac', sr=None):
    probe = ffmpeg.probe(filename)
    if probe.get('format').get('format_name') != format or probe['streams'][0]['sample_rate'] != str(sr):
        fl, audio_file = tempfile.mkstemp(suffix=f'.{format}')
        os.close(fl)
        stream = ffmpeg.input(filename)
        if sr:
            stream = ffmpeg.output(stream, audio_file, acodec='pcm_s16le' if format == 'wav' else 'flac' , ar=sr, loglevel='error')
        else:
            stream = ffmpeg.output(stream, audio_file,  acodec='pcm_s16le' if format == 'wav' else 'flac' , loglevel='error')
        ffmpeg.run(stream, overwrite_output=True)
        return audio_file, sr or int(probe['streams'][0]['sample_rate'])
    else:
        return filename, int(probe['streams'][0]['sample_rate'])