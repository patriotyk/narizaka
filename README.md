# Narizaka
Tool to make high quality text to speech (tts) corpus from audio + text books.

## How it works
First it splits audio files in to small segments 5-15 seconds, then it iterates over each segment
and transcribes with whisper ASR and alligns this transcription with original text, if distance is very small we consider it as match and add it to the dataset.


## Installation
```
pip install narizaka
```

Or if you plan to modify sources:

```
git clone https://github.com/patriotyk/narizaka.git
pip install -e narizaka/
```
Flag `-e` means that you can edit source files in the directory where you have cloned this project and they will be reflected when you run command `narizaka`

## How to use

Application accepts two inputs. First one, it is audio data, that can be folder of audio files, or just one audio file.
And text, that can be any document that accepts `pandoc` application.
Example:
```
narizaka -a test_data/farshrutka -t test_data/Farshrutka.fb2
```
This repository contains `test_data` that includes audio and text books that you can use for testing.
