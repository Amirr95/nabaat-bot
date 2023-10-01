FROM python:3.10.6-slim

WORKDIR /bot

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

# RUN python3 -u main.py