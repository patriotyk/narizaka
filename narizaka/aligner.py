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
import torch
import torchaudio
from torchaudio.functional import resample
from stable_whisper.result import WordTiming
from ukrainian_word_stress import Stressifier
from ipa_uk import ipa
stressify = Stressifier()


bad_text = regex.compile('[0-9\p{L}--[а-яіїєґ]]', regex.VERSION1|regex.IGNORECASE)

class Aligner():
    def __init__(self, output: pathlib.Path, sr: int, columns: str, audio_format: str) -> None:
        self.output = output
        self.audio_format = audio_format
        self.sr = sr
        self.splitter = Splitter()
        self.columns = columns.split(',')

    def pases_filter(self, segment):
        if segment['end']-segment['start'] < 1.0 or segment['end']-segment['start'] > 35:
            print('Skipped because of length')
            return False
        if bad_text.search(segment['sentence']):
            print('Skipped because contains inapropirate characters')
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
            self.orig_flac, self.current_sr_orig  = utils.convert_media(orig_file)
            data = json.load(open(transcribed_files['cache'], 'r'))
            words = []
            for w in data:
                words.append(WordTiming(**w))

            if transcribed_files['audio_16']:
                file_16 = transcribed_files['audio_16']
            else:
                file_16, _ = utils.convert_media(orig_file, format='wav', sr=16000)
            print(file_16)
            segments = self.splitter.split_to_segments(file_16, words)
            yield {
                'segments': segments,
                'orig_name': orig_file.name,
                'flac_path': self.orig_flac,
                'flac_sr': self.current_sr_orig
            }

    def normalize_loudness(self, wav: torch.Tensor, sample_rate: int, loudness_headroom_db: float = 18,
                        energy_floor: float = 2e-3):
        """Normalize an input signal to a user loudness in dB LKFS.
        Audio loudness is defined according to the ITU-R BS.1770-4 recommendation.

        Args:
            wav (torch.Tensor): Input multichannel audio data.
            sample_rate (int): Sample rate.
            loudness_headroom_db (float): Target loudness of the output in dB LUFS.
            energy_floor (float): anything below that RMS level will not be rescaled.
        Returns:
            output (torch.Tensor): Loudness normalized output data.
        """
        energy = wav.pow(2).mean().sqrt().item()
        if energy < energy_floor:
            return wav
        transform = torchaudio.transforms.Loudness(sample_rate)
        input_loudness_db = transform(wav).item()
        # calculate the gain needed to scale to the desired loudness level
        delta_loudness = -loudness_headroom_db - input_loudness_db
        gain = 10.0 ** (delta_loudness / 20.0)
        output = gain * wav
        assert output.isfinite().all(), (input_loudness_db, wav.pow(2).mean().sqrt())
        return output

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
        
        for segments in self.segments(transcribed['files']):
            current_waveform_orig = None
            orig_flac = segments['flac_path']
            current_sr  = segments['flac_sr'] if not self.sr else self.sr
            orig_name = segments['orig_name']
            if self.sr:
                orig_flac, _ = utils.convert_media(orig_flac, sr=self.sr)
                #Resampling with torchaudio requires lot of memory, because we load original file to memory, for big files even 32 GB of memory is not enought
                #current_waveform_orig = resample(current_waveform_orig, orig_sr, self.sr, lowpass_filter_width=128, resampling_method="sinc_interp_kaiser")
            current_waveform_orig, sr = torchaudio.load(orig_flac, normalize=True)
            current_waveform_orig = self.normalize_loudness(current_waveform_orig, sr)

            for segment in segments['segments']:
                if not segment:
                    continue
                print(f'\n{format_timestamp(segment["start"])} -> {format_timestamp(segment["end"])}: {segment["text"]}')

                match = self.find_match(segment["text"])
                if match.get('matched'):
                    segment['sentence'] = match["sentence"]
                    print(f'MATCHED: {match["sentence"]}')
                    if not self.pases_filter(segment):
                        continue

                    filename = orig_name+f"_{segment['start']:.3f}-{segment['end']:.3f}.{self.audio_format}"
                    start = int(segment['start'] * current_sr)
                    end = int(segment['end'] * current_sr)
                    
                    segment_wave = current_waveform_orig[:, start:end]
                    torchaudio.save(str(audio_output.joinpath(filename)), segment_wave, current_sr)

                    
                    segment['duration'] = segment['end'] - segment['start']
                    segment['audio'] = self.book.name+ '/' + filename
                    segment['ipa'] = ipa(stressify(match["sentence"]), False)
                    segment['speaker_id'] = transcribed['speaker_id']

                    ds.writerow(segment)
                    self.recognised_duration += segment['duration']

                else:
                    print(f'NOT MATCHED: {match["book_text"]}')
        dfp.close()
        return self.recognised_duration
