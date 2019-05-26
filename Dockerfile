FROM python:3

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    less \
    vim-tiny \
    wget \
    ca-certificates \
    locales \
    time \
    gnupg \
    build-essential \
    coinor-cbc \
&& apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./dev-requirements.txt /tmp

RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt && \
    pip install -r /tmp/dev-requirements.txt

COPY . /app

WORKDIR /app

CMD python schedule.py
