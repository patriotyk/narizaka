import regex
import unicodedata
import os
import pathlib
import json


from narizaka.textbook import TextBook
from narizaka.splitter import Splitter
from narizaka import utils
from narizaka.textnormalizer import norm
from fuzzysearch import find_near_matches
from csv import DictWriter, QUOTE_MINIMAL
from faster_whisper.utils import format_timestamp
from narizaka.segmenter import Segmenter
import torchaudio
from torchaudio.functional import resample
from stable_whisper.result import WordTiming
from ukrainian_word_stress import Stressifier
from ipa_uk import ipa
stressify = Stressifier()


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
        if len(self.norm_text) < self.current_pos + 3000:
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
            if num_words > 2 or matched.start < 10:
                self.current_pos += matched.end
        else:
            book_text = self.current_norm_text()[:200 ] + "..."
            match['book_text'] = book_text
        return match

    def segments(self, transcribed):
        for orig_file, transcribed_files in transcribed.items():
            print(f"Using transcribed file from file: {transcribed_files['cache']}")
            data = json.load(open(transcribed_files['cache'], 'r'))
            words = []
            for w in data:
                words.append(WordTiming(**w))

            if transcribed_files['audio_16']:
                file_16 = transcribed_files['audio_16']
            else:
                file_16, _ = utils.convert_media(orig_file, format='wav', sr=16000)
            segments = self.splitter.split_to_segments(file_16, words)
            yield {
                'segments': segments,
                'orig_name': orig_file,
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
            fieldnames=self.columns,
            extrasaction='ignore',
            quoting=QUOTE_MINIMAL,
            delimiter='|'
        )

        segmenter = Segmenter(sr=self.sr)
        for segments in self.segments(transcribed['files']):

            orig_name = segments['orig_name']
            for segment in segments['segments']:
                if not segment:
                    continue
                #print(f'\n{format_timestamp(segment["start"])} -> {format_timestamp(segment["end"])}: {segment["text"]}')

                match = self.find_match(segment["text"])
                if match.get('matched'):
                    segment['sentence'] = match["sentence"]
                    #print(f'MATCHED: {match["sentence"]}')
                    if not self.pases_filter(segment):
                        continue

                    start = float(segment['start'])
                    end = float(segment['end'])
                    filename = segmenter.save(start_time=start, end_time=end)
                    
                    segment['duration'] = segment['end'] - segment['start']
                    segment['audio'] = os.path.join(elf.book.name, filename)
                    segment['ipa'] = ipa(stressify(match["sentence"]), False)
                    segment['speaker_id'] = transcribed['speaker_id']

                    ds.writerow(segment)
                    self.recognised_duration += segment['duration']

                else:
                    pass
                    #print(f'NOT MATCHED: {match["book_text"]}')
            segmenter.run(str(orig_name), output_folder=audio_output)
        dfp.close()
        return self.recognised_duration
