# Thin layer over gnzsnz/ib-gateway that adds xdotool for dialog dismissal.
# gnzsnz base image includes Xvfb, x11vnc, socat, but NOT xdotool.
# Pin to the same digest running in production.
FROM ghcr.io/gnzsnz/ib-gateway:stable

USER root
RUN apt-get update \
 && apt-get install --no-install-recommends -y xdotool \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
USER 1000:1000
