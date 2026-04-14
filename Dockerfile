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
##   --name tornado-geo-widget tornado-geo-widget:v1 --verbose
FROM docker.io/library/python:slim

# Set the working directory to /app
WORKDIR /app

# Install uv using the official installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Add the Python files for the application
COPY pyproject.toml uv.lock README.md *.py ./

# Set uv to use the .cache directory
ENV UV_CACHE_DIR=/app/.cache/uv

# Install Python dependencies
RUN uv sync --frozen --no-cache

# Add a user account
# No need to run as root in the container
RUN adduser --disabled-password --disabled-login --no-create-home appuser

# No need to run as root in the container
USER appuser

# Set the command to run on start up
ENTRYPOINT ["uv", "run",  "/app/cli.py"]
#CMD ["--help"]
