import regex
import unicodedata
import os
import pathlib

from datetime import timedelta
from narizaka.textbook import TextBook
from narizaka.audiobook import AudioBook
from fuzzysearch import find_near_matches
from num2words import num2words
from csv import DictWriter, QUOTE_NONE



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
        self.recognised_duration = 0.0
   
    
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
    
        match = {
            'asr': norm_text,
            'matched': False,
        }
        matches = find_near_matches(norm_text, self.current_norm_text(), max_l_dist=int(num_words*0.4))
        if matches and matches[0].matched:
            matched = min(matches, key=lambda m: m.start)
            
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


    def run(self, output):
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
        

        for segment in self.audiobook.transcribe():
            match = self.find_match(segment["text"])
            #self.audiobook.save_segment(segment, audio_output)
            if match.get('matched'):
                #print(f'MATCHED: {match["sentence"]}')
                segment['sentence'] = match["sentence"]
                segment['duration'] = segment['end'] - segment['start']
                ds.writerow(segment)
                self.recognised_duration += segment['duration']
                self.audiobook.save_segment(segment, audio_output)
            else:
                pass
                #print(f'NOT MATCHED: {match["book_text"]}')
        dfp.close()
        print(f'Extracted {timedelta(seconds=self.recognised_duration)} of audio duration from {timedelta(seconds=self.audiobook.duration)}')
        print(f'It is {(self.recognised_duration/self.audiobook.duration)*100}% of total audio')



                
                

    
    