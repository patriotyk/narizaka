import regex
import unicodedata
import os
import pathlib
import json


from narizaka.textbook import TextBook
from narizaka.splitter import Splitter
from narizaka import utils
from narizaka.languages.uk.textnormalizer import norm
from fuzzysearch import find_near_matches
from csv import DictWriter, QUOTE_MINIMAL
from faster_whisper.utils import format_timestamp
from narizaka.segmenter import Segmenter
import torchaudio
from torchaudio.functional import resample
from stable_whisper.result import WordTiming


bad_text = regex.compile('[0-9\p{L}--[а-яіїєґ]]', regex.VERSION1|regex.IGNORECASE)

class Aligner():
    def __init__(self, args) -> None:
        self.output = args.o
        self.sr = args.sr
        self.splitter = Splitter()
        self.columns = args.columns.split(',')

    def pases_filter(self, segment):
        if segment['end']-segment['start'] < 1.0 or segment['end']-segment['start'] > 35:
            #print('Skipped because of length')
            return False
        if bad_text.search(segment['sentence']):
            #print('Skipped because contains inapropirate characters')
            return False
        return True

    
    def _base_norm(self, text):
        return norm(text).split(' ')
    
    def _norm_word(self, text):
        text = regex.sub(r'[^\p{L}\p{N}]', '', text)
        return text.lower()
    
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
        if len(self.norm_text) < self.current_pos + 20000:
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
        matches = find_near_matches(norm_text, self.current_norm_text(), max_l_dist=int(num_words*0.2))
        if matches and matches[0].matched:
            matched = min(matches, key=lambda m: m.start)
            
            match['sentence'] = self._norm_for_corpus(self.get_denorm(matched.start, matched.matched))
            match['sentence_norm'] = matched.matched
            match['start'] = matched.start
            match['end'] = matched.end
            match['distance'] = matched.dist
            match['matched'] = True
            if num_words > 4 or matched.start < 20:
                self.current_pos += matched.end
        else:
            book_text = self.current_norm_text()[:200 ] + "..."
            match['book_text'] = book_text
        return match


    def run(self, pair):
        self.normpos = []
        self.denorm = []
        self.norm_text = ''
        self.current_pos = 0
        self.book = TextBook(pair.text_book_path)

        self.recognised_duration = 0.0

        audio_output = self.output / self.book.name
        if not audio_output.exists():
            os.makedirs(audio_output, exist_ok=True)
    
            
        dataset_file = self.output.joinpath(self.book.name+'.txt')
        log_file = open(self.output.joinpath(self.book.name+'.log'), 'w')
        log_file.write(f'\nStarting book {self.book.name}\n')
        dfp = dataset_file.open("w")
        ds = DictWriter(
            dfp,
            fieldnames=self.columns,
            extrasaction='ignore',
            quoting=QUOTE_MINIMAL,
            delimiter='|'
        )

        segmenter = Segmenter(sr=self.sr)
        for audio_file, words in pair.audio_book.transcription():
            log_file.write(f'Starting audiofile: {audio_file}\n')
            file_16, _ = utils.convert_media(audio_file, format='wav', sr=16000)
            segments = self.splitter.split_to_segments(file_16, words)
            for segment in segments:
                if not segment:
                    continue
                log_file.write(f'\n{format_timestamp(segment["start"])} -> {format_timestamp(segment["end"])}: {segment["text"]}\n')

                match = self.find_match(segment["text"])
                if match.get('matched'):
                    segment['sentence'] = match["sentence"]
                    log_file.write(f'MATCHED: {match["sentence"]}\n')
                    if not self.pases_filter(segment):
                        continue

                    start = float(segment['start'])
                    end = float(segment['end'])
                    filename = segmenter.save(start_time=start, end_time=end)
                    
                    segment['duration'] = segment['end'] - segment['start']
                    segment['audio'] = os.path.join(self.book.name, filename)
                    segment['speaker_id'] = pair.audio_book.speaker_id or '0'

                    ds.writerow(segment)
                    self.recognised_duration += segment['duration']

                else:
                    log_file.write(f'NOT MATCHED: {match["book_text"]}\n')
            os.remove(file_16)
            segmenter.run(str(audio_file), output_folder=audio_output)
        dfp.close()
        log_file.close()
        return self.recognised_duration, pair.audio_book.duration, self.book.name
