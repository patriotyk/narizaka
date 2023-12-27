FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

RUN apt-get update
RUN apt-get install -y pandoc ffmpeg git python3-pip libmagic-dev
RUN pip install -U pip
RUN pip install git+https://github.com/patriotyk/narizaka.git


ENTRYPOINT [ "narizaka" ]