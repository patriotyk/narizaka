FROM nvidia/cuda:11.8.0-base-ubuntu22.04

RUN apt-get update
RUN apt-get install -y pandoc ffmpeg git python3-pip libmagic-dev
RUN git clone https://github.com/patriotyk/narizaka.git
RUN pip install -U pip
RUN pip install narizaka/

ENTRYPOINT [ "narizaka" ]