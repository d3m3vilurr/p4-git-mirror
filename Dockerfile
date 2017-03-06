FROM library/python:2.7-slim

WORKDIR /opt

ENV P4_VERSION 16.2
ENV GIT_USER p4mirror
ENV GIT_EMAIL noreply@p4mirror

RUN set -x \
    && cd /etc/apt \
    && sed -i 's/deb.debian.org/ftp.kaist.ac.kr/g' sources.list \
    && sed -i 's/security.debian.org/ftp.kaist.ac.kr\/debian-security/g' sources.list \
    && builds='build-essential curl libssl-dev git openssh-client' \
    && apt-get update && apt-get install -y $builds --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && curl http://cdist2.perforce.com/perforce/r$P4_VERSION/bin.linux26x86_64/p4 -o /usr/local/bin/p4 \
    && chmod 755 /usr/local/bin/p4 \
    && cd /opt \
    && curl -L https://github.com/d3m3vilurr/p4-git-mirror/raw/master/requirement.txt -o requirement.txt \
    && pip install -r requirement.txt \
    && apt-get purge -y --auto-remove build-essential \
    && git config --global user.email $GIT_EMAIL \
    && git config --global user.name $GIT_USER

COPY sync.py /opt/sync.py

ENTRYPOINT ["python", "sync.py"]
