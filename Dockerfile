FROM nvidia/cuda:11.8.0-base-ubuntu22.04

RUN apt-get update
RUN apt-get install -y pandoc ffmpeg git python3-pip libmagic-dev libcairo2-dev libgirepository1.0-dev python3-gst-1.0
RUN pip install -U pip
RUN pip install git+https://github.com/patriotyk/narizaka.git
RUN cp -r /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/lib* /usr/lib/

ENTRYPOINT [ "narizaka" ]