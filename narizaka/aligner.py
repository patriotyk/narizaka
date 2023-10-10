import regex
import unicodedata
import ffmpeg
import os
import tempfile
import torchaudio
import auditok
import pathlib

from datetime import timedelta
from narizaka.textbook import TextBook
from narizaka.audiobook import AudioBook
from fuzzysearch import find_near_matches
from num2words import num2words
from csv import DictWriter, QUOTE_NONE

from faster_whisper import WhisperModel
from faster_whisper.utils import format_timestamp


REPLACE={
    '§': 'параграф ',
    '№': 'номер ',
}

class Aligner():
    def __init__(self, book: pathlib.Path, audio: pathlib.Path) -> None:
        self.normpos = []
        self.denorm = []
        self.norm_text = ''
        self.current_pos = 0
        self.book = TextBook(book)
        self.audiobook = AudioBook(audio)
        self.total_words = 0
        self.recognised_words = 0
        self.recognised_duration = 0.0
        self.model = WhisperModel('large-v2', compute_type='default')
   
    
    def _base_norm(self, text):
        text = regex.sub(r'[\t\n]', ' ', text)
        text = regex.sub(r'\s+', ' ', text)
        text = unicodedata.normalize('NFC', text)
        text = text.lower()
        text = regex.sub(rf"[{''.join(REPLACE.keys())}]", lambda x: REPLACE[x.group()], text)
        text = regex.sub(r"(\d+)\s+рік", lambda x: num2words(x.group(1), lang='uk', to='ordinal'), text)
        text = regex.sub(r"\d+", lambda x: num2words(x.group(), lang='uk'), text)
        return text.split(' ')
    
    def _norm_word(self, text):
        text = regex.sub(r'[^\p{L}\p{N}]', '', text)
        return text
    
    def normalize(self, text):
        words = self._base_norm(text)
        normalized = ''
        for word in words:
            nword = self._norm_word(word)
            if nword:
                normalized += ' ' + nword
        return normalized

    def _feed(self, text) -> None:
        words = self._base_norm(text)
        for word in words:
            nword = self._norm_word(word)
            if nword:
                self.denorm.append(word)
                word_pos = len(self.norm_text.split(' '))-1
                chars_in_word = len(nword)
                for _ in range(chars_in_word+1):
                    self.normpos.append(word_pos)
                self.norm_text += ' ' + nword
            elif self.denorm:
                self.denorm[-1] += ' '+word

    def get_denorm(self, pos, norm_text):
        nwords = len(norm_text.split(' '))-1
        start_pos = self.current_pos+pos
        denorm_words_list = self.denorm[self.normpos[start_pos]:self.normpos[start_pos]+nwords]
        return ' '.join(denorm_words_list)
            
    def current_norm_text(self):
        if len(self.norm_text) < self.current_pos + 1000:
            text = self.book.more_text()
            self._feed(text)
        return self.norm_text[self.current_pos:]
        
    def find_match(self, text):
        norm_text = self.normalize(text)
        num_words = len(norm_text.split(' '))
        self.total_words += num_words
    
        match = {
            'asr': norm_text,
            'matched': False,
        }
        matches = find_near_matches(norm_text, self.current_norm_text(), max_l_dist=int(num_words*0.4))
        if matches and matches[0].matched:
            matched = min(matches, key=lambda m: m.start)
        
            self.recognised_words += num_words
            
            match['sentence'] = self.get_denorm(matched.start, matched.matched)
            match['sentence_norm'] = matched.matched
            match['start'] = matched.start
            match['end'] = matched.end
            match['distance'] = matched.dist
            match['matched'] = True
            self.current_pos += matched.end
        else:
            book_text = self.current_norm_text()[:200 ] + "..."
            match['book_text'] = book_text
        return match

    def getStat(self):
        return (self.recognised_words/self.total_words)*100
    

    
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
    
    
    
    def split_to_segments(self, audio_file):
        def _split(region, threshold=48, deep=3):
            audio_regions = []
            for r in region.split(
                min_dur=0.3,     # minimum duration of a valid audio event in seconds
                max_dur=80,       # maximum duration of an event
                max_silence=0.08, # maximum duration of tolerated continuous silence within an event
                energy_threshold=threshold # threshold of detection
            ):
                if r.duration > 12.0 and deep:
                    regions = _split(r, threshold+2, deep-1)
                    audio_regions = audio_regions + regions
                else:
                    audio_regions.append(r)
            return audio_regions

        
        region = auditok.load(str(audio_file))
        audio_regions = _split(region)
        #return audio_regions
        
        new_list = []
        prev_segment = None
        min_length = 9.0
        for r in audio_regions:
            if not prev_segment:
                 prev_segment = r
            elif  ((r.meta.start - prev_segment.meta.end) > 0.6) or (prev_segment.duration >= min_length):
                new_list.append(prev_segment)
                prev_segment = r
            elif prev_segment.duration + r.duration  >= min_length:
                if prev_segment.duration > 4.0 and r.duration > 4.0:
                    new_list.append(prev_segment)
                    new_list.append(r)
                    prev_segment = None
                else:
                    start = prev_segment.meta.start
                    prev_segment += r
                    prev_segment.meta = {'end': r.meta.end, 'start': start}
                    new_list.append(prev_segment)
                    prev_segment = None
            else:
                start = prev_segment.meta.start
                prev_segment += r
                prev_segment.meta = {'end': r.meta.end, 'start': start}
                
        return new_list

    def sync(self, output):
        self.prev_segment = None
        self.nsegment_in_file = 0
        audio_output = output / self.book.name
        if not audio_output.exists():
            os.makedirs(audio_output, exist_ok=True)
    
            
        dataset_file = output.joinpath(self.book.name+'.txt')
        dfp = dataset_file.open("w")
        ds = DictWriter(
            dfp,
            fieldnames=[
                "audio",
                "sentence",
                "duration"
            ],
            extrasaction='ignore',
            quoting=QUOTE_NONE,
            delimiter='|'
        )
        ds.writeheader()
        
        
        for file_index, audio_file in enumerate(self.audiobook.audio_files):
            sr = 16000
            waveform_orig, sr_orig = torchaudio.load(self._convert_media_to_wav(audio_file))
            waveform_16, _ =  torchaudio.load(self._convert_media_to_wav(audio_file, sr=sr))

            audio_regions = self.split_to_segments(audio_file)

            prev_text = ''
            for i, r in enumerate(audio_regions):
                # saved_file = r.save(str(audio_output.joinpath(audio_file.name+f"_{r.meta.start:.3f}-{r.meta.end:.3f}.wav").resolve()))
                # continue
                segments, _ = self.model.transcribe(waveform_16[:, int(r.meta.start*sr):int(r.meta.end*sr)][0].numpy(), 
                                            language='uk', 
                                            task='transcribe', word_timestamps=False, 
                                            vad_filter=False,
                                            condition_on_previous_text=True,
                                            without_timestamps=True,
                                            initial_prompt=prev_text)

                for segment in segments:
                    print(f'{format_timestamp(r.meta.start+segment.start)} -> {format_timestamp(r.meta.start+segment.end)}: {segment.text}')
                    match = self.find_match(segment.text)
                    if match.get('matched'):
                        prev_text = match["sentence"]
                        print(f'MATCHED: {match["sentence"]}')
                        saved_file = r.save(str(audio_output.joinpath(audio_file.name+f"_{r.meta.start:.3f}-{r.meta.end:.3f}.wav").resolve()))
                        match['audio'] = os.path.relpath(saved_file, output)
                        match['duration'] = r.duration
                        ds.writerow(match)
                        self.recognised_duration += match['duration']
                    else:
                        prev_text = segment.text
                        print(f'NOT MATCHED: {match["book_text"]}')
        dfp.close()
        print(f'Extracted {timedelta(seconds=self.recognised_duration)} of audio duration from {timedelta(seconds=self.audiobook.duration)}')
        print(f'It is {(self.recognised_duration/self.audiobook.duration)*100}% of total audio')



                
                

    
    