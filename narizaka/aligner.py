import regex
import unicodedata
import os
import pathlib
import json


from narizaka.textbook import TextBook
from narizaka.splitter import Splitter
from narizaka import utils
from fuzzysearch import find_near_matches
from num2words import num2words
from csv import DictWriter, QUOTE_MINIMAL
from faster_whisper.utils import format_timestamp
import torch
import torchaudio
import numpy as np
from torchaudio.functional import resample

from stable_whisper.result import WordTiming


REPLACE={
    '§': 'параграф ',
    '№': 'номер ',
}
bad_text = regex.compile('[\p{L}--[а-яіїєґ]]', regex.VERSION1|regex.IGNORECASE)

class Aligner():
    def __init__(self, output: pathlib.Path, sr: int) -> None:
        self.output = output
        self.sr = sr
        self.splitter = Splitter()

    def pases_filter(self, segment):
        if segment['end']-segment['start'] < 1.0 or segment['end']-segment['start'] > 35:
            print('Skipped because of length')
            return False
        if bad_text.search(segment['text']):
            print('Skipped because contains inapropirate characters')
            return False
        return True

    
    def _base_norm(self, text):
        text = regex.sub(r'[\t\n]', ' ', text)
        text = regex.sub(r'\s+', ' ', text)
        text = unicodedata.normalize('NFC', text)
        text = text.lower()
        text = regex.sub(rf"[{''.join(REPLACE.keys())}]", lambda x: REPLACE[x.group()], text)
        text = regex.sub(r"(\d+)\s+рік", lambda x: num2words(x.group(1), lang='uk', to='ordinal'), text)
        #text = regex.sub(r"\d+", lambda x: num2words(x.group(), lang='uk'), text)
        return text.split(' ')
    
    def _norm_word(self, text):
        text = regex.sub(r'[^\p{L}\p{N}]', '', text)
        return text
    
    def _norm_for_corpus(self, text):
        text = regex.sub(r'[^\p{L}\p{N}\?\!\,\.\-\: ]', '', text)
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
    
        match = {
            'asr': norm_text,
            'matched': False,
        }
        if not norm_text:
            match['book_text'] = self.current_norm_text()[:20 ] + "..."
            return match
        matches = find_near_matches(norm_text, self.current_norm_text(), max_l_dist=int(num_words*0.4))
        if matches and matches[0].matched:
            matched = min(matches, key=lambda m: m.start)
            
            match['sentence'] = self._norm_for_corpus(self.get_denorm(matched.start, matched.matched))
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

    def segments(self, transcribed):
        for orig_file, audio_file_16, transcribed_file in transcribed:
            print(f'Using transcribed file from file: {transcribed_file}')
            self.orig_flac, self.current_sr_orig  = utils.convert_media(orig_file)
            data = json.load(open(transcribed_file, 'r'))
            words = []
            for w in data:
                words.append(WordTiming(**w))

            segments = self.splitter.split_to_segments(audio_file_16, words)
            yield {
                'segments': segments,
                'orig_name': orig_file.name,
                'flac_path': self.orig_flac,
                'flac_sr': self.current_sr_orig
            }

    def run(self, book: pathlib.Path, transcribed):
        self.normpos = []
        self.denorm = []
        self.norm_text = ''
        self.current_pos = 0
        self.book = TextBook(book)
        #print(f'\nStarting book {self.book.name}, with audio duration {format_timestamp(self.audiobook.duration)}')

        self.recognised_duration = 0.0

        audio_output = self.output / self.book.name
        if not audio_output.exists():
            os.makedirs(audio_output, exist_ok=True)
    
            
        dataset_file = self.output.joinpath(self.book.name+'.txt')
        dfp = dataset_file.open("w")
        ds = DictWriter(
            dfp,
            fieldnames=[
                "audio",
                "sentence",
                "duration"
            ],
            extrasaction='ignore',
            quoting=QUOTE_MINIMAL,
            delimiter='|'
        )
        
        samples_buffer_length = 8000 * 44100
        for segments in self.segments(transcribed):
            last_sample = 0
            current_waveform_orig = None
            orig_flac = segments['flac_path']
            current_sr  = segments['flac_sr'] if not self.sr else self.sr
            orig_name = segments['orig_name']

            for segment in segments['segments']:
                print(f'\n{format_timestamp(segment["start"])} -> {format_timestamp(segment["end"])}: {segment["text"]}')

                match = self.find_match(segment["text"])
                if match.get('matched'):
                    print(f'MATCHED: {match["sentence"]}')
                    if not self.pases_filter(segment):
                        continue

                    filename = orig_name+f"_{segment['start']:.3f}-{segment['end']:.3f}.flac"
                    end = int(segment['end'] * current_sr)
                    if end > last_sample:
                        chunk, orig_sr = torchaudio.load(orig_flac, frame_offset=last_sample, num_frames=samples_buffer_length)
                        if self.sr:
                            chunk = resample(chunk, orig_sr, self.sr, lowpass_filter_width=128, resampling_method="sinc_interp_kaiser")
                        if current_waveform_orig != None:
                            current_waveform_orig = torch.cat((current_waveform_orig, chunk), -1)
                        else:
                            current_waveform_orig = chunk
                        last_sample =  last_sample + samples_buffer_length
                    start = int(segment['start'] * current_sr)
                    
                    segment_wave = current_waveform_orig[:, start:end]
                    torchaudio.save(str(audio_output.joinpath(filename)), segment_wave, current_sr)

                    segment['sentence'] = match["sentence"]
                    segment['duration'] = segment['end'] - segment['start']
                    segment['audio'] = self.book.name+ '/' + filename
                    ds.writerow(segment)
                    self.recognised_duration += segment['duration']

                else:
                    print(f'NOT MATCHED: {match["book_text"]}')
                pass
        dfp.close()
        return self.recognised_duration

    