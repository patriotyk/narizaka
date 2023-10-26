import magic
from datetime import timedelta
import os
import ffmpeg
import pathlib
import tempfile
import auditok
import json
from dataclasses import asdict
# from faster_whisper import WhisperModel
import torchaudio
from faster_whisper.utils import format_timestamp
import stable_whisper
from stable_whisper.result import WordTiming


class AudioBook():
    def __init__(self, filename: pathlib.Path) -> None:
        #self.model = WhisperModel('large-v2', compute_type='default')
        self.model = stable_whisper.load_faster_whisper('large-v2')
        self.audio_files = []      
        if not filename.exists():
            raise Exception('Audio path doesn\'t exists')
        
        if filename.is_dir():
            files = os.listdir(filename)
            files.sort()
            for f in files:
                if self._is_media(filename.joinpath(f)):
                    self.audio_files.append(pathlib.Path(filename.joinpath(f)))
            if not self.audio_files:
                raise Exception('Directory doesn\'t contain any audio files')
        else:
            if not self._is_media(filename):
                raise Exception('Audio book is not audio file')    
            self.audio_files.append(filename)
        self.duration = 0.0
        for fl in self.audio_files:
            probe = ffmpeg.probe(fl)
            self.duration += float(probe["format"]["duration"])

        print(f'Complete audio duration is {format_timestamp(self.duration)}')

    
    def _is_media(self, filename: pathlib.Path)-> bool:
        mimetype = magic.from_file(filename=filename, mime=True)
        return mimetype.split('/')[0] == 'audio'
    
    def _convert_media_to_wav(self, filename, sr=None):
        probe = ffmpeg.probe(filename)
        if probe.get('format').get('format_name') != 'wav' or probe['streams'][0]['sample_rate'] != str(sr):
            fl, audio_file = tempfile.mkstemp(suffix='.wav')
            os.close(fl)
            stream = ffmpeg.input(filename)
            if sr:
                stream = ffmpeg.output(stream, audio_file, ar=sr, loglevel='panic')
            else:
                stream = ffmpeg.output(stream, audio_file, loglevel='panic')
            ffmpeg.run(stream, overwrite_output=True)
            return audio_file
        else:
            return filename

    def split_to_segments(self, audio_file, all_words):
        def _split(region, threshold=46, deep=4):
            audio_regions = []
            for r in region.split(
                min_dur=0.2,     # minimum duration of a valid audio event in seconds
                max_dur=80,       # maximum duration of an event
                max_silence=0.09, # maximum duration of tolerated continuous silence within an event
                energy_threshold=threshold # threshold of detection
            ):
                if r.duration > 10.0 and deep:
                    regions = _split(r, threshold+2, deep-1)
                    if len(regions)> 1:
                        offset = r.meta.start
                        for rr in regions:
                            rr.meta = {'end': rr.meta.end+offset, 'start': rr.meta.start+offset}
                    splitted = []
                    for rr in regions:
                        splitted.append(str(rr.meta))                    
                    audio_regions = audio_regions + regions
                else:
                    audio_regions.append(r)
            return audio_regions

        
        region = auditok.load(str(audio_file))
        audio_regions = sorted(_split(region), key=lambda x: x.meta.start)
        
        pugaps = []
        text = ''
        for i, word in enumerate(all_words[:-1]):
            text += word.word
            if word.word[-1] in [',','.','?','-',':','!']:
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
                
            elif gap_dur > 0.5: #FIXME Should find split here
                temp_reg = None


        ready_segment = {}
        for segment in regions_by_punct:
            if not ready_segment:
                ready_segment = segment
                continue

            if ready_segment['text'].endswith(',') and (segment['end'] - ready_segment['start']) < 12:
                ready_segment['end'] = segment['end']
                ready_segment['text'] += segment['text']
            else:
                yield ready_segment
                ready_segment = segment
        if ready_segment:
            yield ready_segment
                
    
    def transcribe(self):
        for file_index, self.current_file in enumerate(self.audio_files):
            sr = 16000
            self.current_waveform_orig, self.current_sr_orig = torchaudio.load(self._convert_media_to_wav(self.current_file))
            waveform_16, _ =  torchaudio.load(self._convert_media_to_wav(self.current_file, sr=sr))


            print(f'Transcribing {self.current_file}')
            result = self.model.transcribe_stable(waveform_16[0].numpy(), input_sr=sr, language='uk', regroup=True,
                                                  prepend_punctuations= "\"'“¿([{-«",
                                                  append_punctuations = "\"'.。,，!！?？:：”)]}、»")
            words = result.all_words()

            with open('output/tmp/'+self.current_file.name+'.json', 'w') as w:
                data = []
                for r in result.all_words():
                    data.append(asdict(r))
                w.write(json.dumps(data))

            # data = json.load(open('output/tmp/'+self.current_file.name+'.json', 'r'))
            # words = []
            # for w in data:
            #     words.append(WordTiming(**w))


            segments = self.split_to_segments(self.current_file, words)
            for segment in segments:
                #self.save_segment(segment, pathlib.Path('output/tmp_audio/'))
                #print(f'\n{format_timestamp(segment["start"])} -> {format_timestamp(segment["end"])}: {segment["text"]}')
                segment['audio']= self.current_file
                yield segment
        
    
    
    def save_segment(self, segment, audio_output):
        filename =  str(audio_output.joinpath(self.current_file.name+f"_{segment['start']:.3f}-{segment['end']:.3f}.flac"))
        start = int(segment['start'] * self.current_sr_orig)
        end = int(segment['end'] * self.current_sr_orig)
        torchaudio.save(filename, self.current_waveform_orig[:, start:end], self.current_sr_orig)
        return filename
