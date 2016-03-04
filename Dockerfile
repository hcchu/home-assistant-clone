FROM python:3.4
MAINTAINER Paulus Schoutsen <Paulus@PaulusSchoutsen.nl>

VOLUME /config

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN pip3 install --no-cache-dir colorlog cython

# For the nmap tracker
RUN apt-get update && \
    apt-get install -y --no-install-recommends nmap net-tools cython3 libudev-dev sudo && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY script/build_python_openzwave script/build_python_openzwave
RUN script/build_python_openzwave && \
  mkdir -p /usr/local/share/python-openzwave && \
  ln -sf /usr/src/app/build/python-openzwave/openzwave/config /usr/local/share/python-openzwave/config

COPY requirements_all.txt requirements_all.txt
RUN pip3 install --no-cache-dir -r requirements_all.txt

# Copy source
COPY . .

CMD [ "python", "-m", "homeassistant", "--config", "/config" ]
