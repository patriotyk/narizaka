# Narizaka
Tool to make high quality text to speech (tts) corpus from audio + text books.

## How it works
First it splits audio files in to small segments 5-15 seconds, then it iterates over each segment
and transcribes with whisper ASR and alligns this transcription with original text, if distance is very small we consider it as match and add it to the dataset.


## Installation

First, you should install several system dependancies:

On deb linux:
```
sudo apt install ffmpeg pandoc
```
on MacOSX:

```
brew install ffmpeg pandoc libmagic
```

Then you can install `narizaka`:

> **⚠ WARNING**
> Because we have direct dependancies to github temporary we are not able to push `narizaka` to pypi. There is very old version.

```
pip install narizaka
```
or if you want last develop version:

```
pip install git+https://github.com/patriotyk/narizaka.git
```
Also if you plan to modify sources:

```
git clone https://github.com/patriotyk/narizaka.git
pip install -e narizaka/
```
Flag `-e` means that you can edit source files in the directory where you have cloned this project and they will be reflected when you run command `narizaka`

Every tagged commit on `main` brnach automatically pushes ro the docker hub. So you can also pull this images:

```
docker pull patriotyk/narizaka:latest
```

## How to use

Application as input accepts directory that contains audio data, it can be folder or subfolder of audio files, or just one audio file and there also should be one text file tat represents this audio.
This text file, can be any document that accepts `pandoc` application.
Example:
```
narizaka test_data/farshrutka 
```
Or
```
narizaka test_data
```
to process all books.

This repository contains `test_data` that includes two audio and text books that you can use for testing.
