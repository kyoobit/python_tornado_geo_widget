FROM docker.io/library/alpine:latest

## Add os build dependencies
## podman run --rm --tty --interactive rust:alpine /bin/sh
## apk update; apk info <package>
RUN apk add python3 py3-tornado py3-geoip2

## Copy the source files for the project
COPY app.py /app.py
COPY cli.py /cli.py

## Add a user account
## No need to run as root in the container
RUN addgroup -S appgroup \
    && adduser -S appuser -G appgroup

## Run all future commands as appuser
USER appuser

## Setup the entrypoint
ENTRYPOINT ["python3", "/cli.py"]
## Example usage:
##   podman build --tag tornado-geo-widget:v1 .
##
## View the available program options:
##   podman run --rm --name tornado-geo-widget-help tornado-geo-widget:v1 --help
##
## Download the latest databases (you'll need an API key):
##   bash ./get_maxmind_database.sh -u -e GeoLite2-ASN,GeoLite2-City -k "${MAXMIND_API_KEY}"
## 
## Run a container instance:
##   podman run --rm --detach --publish 8888:8888/tcp \
##   --volume ./GeoLite2-ASN.mmdb:/GeoLite2-ASN.mmdb:ro \
##   --volume ./GeoLite2-City.mmdb:/GeoLite2-City.mmdb:ro \
##   --name tornado-geo-widget tornado-geo-widget:v1