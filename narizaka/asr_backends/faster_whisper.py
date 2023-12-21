import stable_whisper
from faster_whisper.tokenizer import Tokenizer

class FasterWhisperTranscriber():
    def __init__(self, device, device_index) -> None:
        self.model = stable_whisper.load_faster_whisper('large-v3', device=device, device_index=device_index if device =='cuda' else 0, cpu_threads=2)    
        tokenizer = Tokenizer(
                    self.model.hf_tokenizer,
                    True,
                    task='transcribe',
                    language='uk',
                )
        self.number_tokens = [-1]
        self.number_tokens  = self.number_tokens + [
            i 
            for i in range(tokenizer.eot)
            if all(c in "0123456789%№§IVXC$£₴€" for c in tokenizer.decode([i]).removeprefix(" "))
        ]


    def transcribe(self, audio):
        result = self.model.transcribe_stable(audio, language='uk', regroup=True,
                                                      prepend_punctuations= "\"'“¿([{-«",
                                                      append_punctuations = "\"'.。,，!！?？:：”)]}、»", suppress_tokens=self.number_tokens)
        return result
