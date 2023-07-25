# Use a base image with Python and Locust installed
FROM locustio/locust

COPY requirments.txt .
RUN pip3 install -r requirments.txt

COPY main.py .
