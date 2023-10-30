FROM python:3.11

RUN apt-get update
RUN apt-get install -y pandoc ffmpeg
RUN pip install git+https://github.com/patriotyk/narizaka.git

ENTRYPOINT [ "narizaka" ]