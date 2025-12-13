FROM alpine:latest AS parsley

RUN apk add --no-cache unzip \
    && wget -q https://github.com/wez/atomicparsley/releases/download/20240608.083822.1ed9031/AtomicParsleyAlpine.zip -O /tmp/ap.zip \
    && unzip -q /tmp/ap.zip -d /tmp \
    && install -m 755 /tmp/AtomicParsley /usr/local/bin/AtomicParsley

FROM python:3-alpine

RUN mkdir -p /opt/twitch-recorder/ \
    && apk add --no-cache ffmpeg libstdc++ \
    && pip install streamlink

COPY --from=parsley /usr/local/bin/AtomicParsley /usr/local/bin/AtomicParsley

COPY twitch-recorder.py postprocess.py /opt/twitch-recorder/

WORKDIR /opt/twitch-recorder

CMD ["python", "./twitch-recorder.py"]

