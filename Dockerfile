#FROM python:3.8-slim
FROM nvidia/cuda:11.5.2-devel-ubuntu20.04
# Project setup

ENV VIRTUAL_ENV=/opt/venv

RUN apt-get update && apt-get clean
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-dev \
        python3-pip \
        wget \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
#RUN apt install apt install nvidia-cuda-toolkit

#RUN apt-get install cuda-cudart-11-8
RUN apt-get update &&  apt-get install -y --no-install-recommends\
    python3.8-venv

RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install  --quiet --upgrade pip && \
    pip install  --quiet pip-tools
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt \
    && rm -rf /root/.cache/pip

#Custom translator requirements
#COPY ./app/customtranslators/<customtranslatorname>/requirements.txt /app/customrequirements.txt
#RUN pip install -r /app/customrequirements.txt \
#    && rm -rf /root/.cache/pip

COPY . /app
WORKDIR /app

COPY ./app/nltk_pkg.py /app/nltk_pkg.py
RUN python3 /app/nltk_pkg.py