import magic
from datetime import timedelta
import os
import ffmpeg
import pathlib
import tempfile
import auditok
import torch
import json
import hashlib
from retry import retry
from dataclasses import asdict

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

    @retry(tries=3, delay=1)
    def _convert_media(self, filename, format='flac', sr=None):
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

    def split_to_segments(self, audio_file, all_words):
        def _split(region, threshold=46, deep=4):
            if not region.meta:
                region.meta = {'start': 0}
            audio_regions = []
            for r in region.split(
                min_dur=0.2,     # minimum duration of a valid audio event in seconds
                max_dur=80,       # maximum duration of an event
                max_silence=0.11, # maximum duration of tolerated continuous silence within an event
                energy_threshold=threshold # threshold of detection
            ):
                r.meta = {'start': r.meta.start+region.meta.start, 'end': r.meta.end+region.meta.start}
                if r.duration > 10.0 and deep:
                    regions = _split(r, threshold+2, deep-1)
                    if len(regions)> 1:
                        audio_regions = audio_regions + regions
                else:
                    audio_regions.append(r)
            return audio_regions

        
        region = auditok.load(str(audio_file), large_file=True)
        audio_regions = sorted(_split(region), key=lambda x: x.meta.start)
        
        pugaps = []
        text = ''
        for i, word in enumerate(all_words[:-1]):
            text += word.word
            if word.word[-1] in [',','.','?','-',':','!', '»', ';'] or \
              ((all_words[i+1].start - word.end) > 0.2 and (all_words[i+1].end - all_words[i+1].start) > 0.4 and
              (word.end - word.start) > 0.4):
                pugaps.append([word.end, all_words[i+1].start, i])
                text = ''
        
        
        temp_reg = None
        start_word = 0
        regions_by_punct = []
        for i, r in enumerate(audio_regions[:-1]):

            if not temp_reg:
                temp_reg = r
            else:
                start = temp_reg.meta.start
                temp_reg += r
                temp_reg.meta = {'end': r.meta.end, 'start': start}

            gap_dur = audio_regions[i+1].meta.start - r.meta.end
            gap_point = r.meta.end + (gap_dur/2)
            found = next((item for item in pugaps if (item[0]-0.1) <= gap_point <= item[1]+0.1), None)
            
            if found:
                if start_word != found[2]+1:
                    text = ''.join([word.word for word in all_words[start_word:found[2]+1]])
                    if text.strip():
                        regions_by_punct.append({'start': temp_reg.meta.start,
                                                'end': r.meta.end,
                                                'text': text})
                        temp_reg = None
                        start_word = found[2]+1
                
            # elif gap_dur > 3.5: #FIXME Should find split here
            #     print('GAPPP')
            #     temp_reg = None


        ready_segment = {}
        for segment in regions_by_punct:
            if not ready_segment:
                ready_segment = segment
                continue

            if ready_segment['text'].endswith(',') and (segment['end'] - ready_segment['start']) < 10:
                ready_segment['end'] = segment['end']
                ready_segment['text'] += segment['text']
            else:
                if (ready_segment["end"] - ready_segment["start"]) <= 20:
                    yield ready_segment
                ready_segment = segment
        if ready_segment and (ready_segment["end"] - ready_segment["start"]) <= 20:
            yield ready_segment
                
    def calc_current_hash(self, current_file):
        with open(current_file, 'rb') as f:
            data = f.read()
            return hashlib.sha256(data).hexdigest()
    
    def transcribe(self):
        transcribed = []
        for current_file in self.audio_files:
            sr = 16000
            filename_16, _ = self._convert_media(current_file, format='wav', sr=sr)

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


    def segments(self, transcribed):
        for orig_file, audio_file_16, transcribed_file in transcribed:
            print(f'Using transcribed file from file: {transcribed_file}')
            self.orig_flac, self.current_sr_orig  = self._convert_media(orig_file)
            data = json.load(open(transcribed_file, 'r'))
            words = []
            for w in data:
                words.append(WordTiming(**w))

            segments = self.split_to_segments(audio_file_16, words)
            yield {
                'segments': segments,
                'orig_name': orig_file.name,
                'flac_path': self.orig_flac,
                'flac_sr': self.current_sr_orig

            }
    
    
