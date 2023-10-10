# Narizaka
Tool to make high quality text to speech (tts) corpus from audio + text books.

## How it works
First it splits audio files in to small segments 5-15 seconds, then it iterates over each segment
and transcribes with whisper ASR and alligns this transcription with original text, if distance is very small we consider it as match and add it to the dataset.

