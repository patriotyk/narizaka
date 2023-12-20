FROM nvidia/cuda:12.3.1-base-ubuntu22.04

RUN apt-get update
RUN apt-get install -y pandoc ffmpeg git python3-pip
RUN pip install git+https://github.com/patriotyk/narizaka.git

ENTRYPOINT [ "narizaka" ]