FROM python:3.10

WORKDIR /async_download_service

COPY requirements.txt .

RUN  apt-get update && apt-get install -q zip && pip install -r requirements.txt

COPY . .
