FROM python:3.7-slim
RUN apt-get -y update && apt-get -y install build-essential
WORKDIR /usr/local/src
COPY requirments.txt .
RUN pip3 install -r requirments.txt
COPY main.py run.sh /usr/local/src/