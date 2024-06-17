import os
import stable_whisper
from faster_whisper.tokenizer import Tokenizer
from narizaka.utils import convert_media


class FasterWhisperTranscriber():
    def __init__(self, device, device_index) -> None:

        self.model = stable_whisper.load_faster_whisper(
            'large-v2', device=device, device_index=device_index, cpu_threads=2)
        tokenizer = Tokenizer(
                    self.model.hf_tokenizer,
                    True,
                    task='transcribe',
                    language='uk',
                )
        self.number_tokens = [-1]
        self.number_tokens = self.number_tokens + [
            i 
            for i in range(tokenizer.eot)
            if all(c in "0123456789%№§IVXC$£₴€" for c in tokenizer.decode([i]).removeprefix(" "))
        ]

    def transcribe(self, audio_file):
        filename_16, _ = convert_media(audio_file, format='wav', sr=16000)
        result = self.model.transcribe_stable(filename_16, language='uk', regroup=True, verbose=None,
                                                        prepend_punctuations= "\"'“¿([{-«",
                                                        append_punctuations = "\"'.。,，!！?？:：”)]}、»", suppress_tokens=self.number_tokens)
        os.remove(filename_16)
        return result
