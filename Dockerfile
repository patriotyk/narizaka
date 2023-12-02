FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

RUN apt-get update
RUN apt-get install -y pandoc ffmpeg
RUN pip install git+https://github.com/patriotyk/narizaka.git

ENTRYPOINT [ "narizaka" ]