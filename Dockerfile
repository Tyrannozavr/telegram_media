FROM python:3.12

ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY ./requirements.txt .
RUN pip install --upgrade pip

COPY . .
RUN pip install -r requirements.txt
