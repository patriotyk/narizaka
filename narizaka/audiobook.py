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
from dataclasses import asdict
import torchaudio
from faster_whisper.utils import format_timestamp

from stable_whisper.result import WordTiming


class AudioBook():
    def __init__(self, filename: pathlib.Path, model) -> None:
        self.model = model
        self.audio_files = []
        self.samples_buffer_length = 8000 * 44100
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

        print(f'Complete audio duration is {format_timestamp(self.duration)}')

    
    def _is_media(self, filename: pathlib.Path)-> bool:
        mimetype = magic.from_file(filename=filename, mime=True)
        return mimetype.split('/')[0] == 'audio'
    
    def _convert_media(self, filename, format='flac', sr=None):
        probe = ffmpeg.probe(filename)
        if probe.get('format').get('format_name') != format or probe['streams'][0]['sample_rate'] != str(sr):
            fl, audio_file = tempfile.mkstemp(suffix=f'.{format}')
            os.close(fl)
            stream = ffmpeg.input(filename)
            if sr:
                stream = ffmpeg.output(stream, audio_file, ar=sr, loglevel='error')
            else:
                stream = ffmpeg.output(stream, audio_file, loglevel='error')
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
                yield ready_segment
                ready_segment = segment
        if ready_segment:
            yield ready_segment
                
    def calc_current_hash(self):
        with open(self.current_file, 'rb') as f:
            data = f.read()
            return hashlib.sha256(data).hexdigest()
    
    def transcribe(self):
        for file_index, self.current_file in enumerate(self.audio_files):
            self.last_sample = 0
            sr = 16000
            self.current_waveform_orig = None
            self.orig_flac, self.current_sr_orig  = self._convert_media(self.current_file)
            filename_16, _ = self._convert_media(self.current_file, format='wav', sr=sr)
            waveform_16, _ =  torchaudio.load(filename_16)


            cash_file = self.cache_path / pathlib.Path(self.calc_current_hash()+'.json')
            if not cash_file.exists():
                print(f'Transcribing {self.current_file}')
                result = self.model.transcribe_stable(waveform_16[0].numpy(), input_sr=sr, language='uk', regroup=True,
                                                      prepend_punctuations= "\"'“¿([{-«",
                                                      append_punctuations = "\"'.。,，!！?？:：”)]}、»")
                words = result.all_words()

                with open(cash_file, 'w') as w:
                    data = []
                    for r in result.all_words():
                        data.append(asdict(r))
                    w.write(json.dumps(data, ensure_ascii=False, indent=4))
            else:
                print(f'Using transcribed file from cache: {cash_file}')
                data = json.load(open(cash_file, 'r'))
                words = []
                for w in data:
                    words.append(WordTiming(**w))


            segments = self.split_to_segments(filename_16, words)
            for segment in segments:
                print(f'\n{format_timestamp(segment["start"])} -> {format_timestamp(segment["end"])}: {segment["text"]}')
                if (segment["end"] - segment["start"]) <= 20: #FIXME it is temporary fix
                    yield segment
                else:
                    print('Dropping segment because length is more than 20 seconds.')


    
    
    def save_segment(self, segment, audio_output):
        filename = self.current_file.name+f"_{segment['start']:.3f}-{segment['end']:.3f}.flac"
        end = int(segment['end'] * self.current_sr_orig)
        if end > self.last_sample:
            chunk, _ = torchaudio.load(self.orig_flac, frame_offset=self.last_sample, num_frames=self.samples_buffer_length)
            if self.current_waveform_orig != None:
                self.current_waveform_orig = torch.cat((self.current_waveform_orig, chunk), -1)
            else:
                self.current_waveform_orig = chunk
            self.last_sample =  self.last_sample+ self.samples_buffer_length
        start = int(segment['start'] * self.current_sr_orig)
        torchaudio.save(str(audio_output.joinpath(filename)), self.current_waveform_orig[:, start:end], self.current_sr_orig)
        return filename
