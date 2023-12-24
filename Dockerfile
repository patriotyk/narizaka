FROM nvidia/cuda:11.8.0-base-ubuntu22.04

RUN apt-get update
RUN apt-get install -y pandoc ffmpeg git python3-pip libmagic-dev nvidia-cuda-toolkit
RUN pip install -U pip
RUN git clone https://github.com/patriotyk/narizaka.git
RUN pip install narizaka/
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH

ENTRYPOINT [ "narizaka" ]