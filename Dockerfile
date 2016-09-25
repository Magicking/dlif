FROM rafaelsoares/archlinux

RUN pacman -Syu --noconfirm python python-cherrypy python-jinja

WORKDIR /srv/http/files
WORKDIR /srv/http/dlif

ADD . /srv/http/dlif/

EXPOSE 6543

ENTRYPOINT ["python", "dlif.py"]
