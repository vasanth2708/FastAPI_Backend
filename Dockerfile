FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt /code/
RUN python -m venv venv
RUN . venv/bin/activate && pip install --upgrade pip && pip3 install -r requirements.txt

COPY . /code/


CMD . venv/bin/activate && exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
