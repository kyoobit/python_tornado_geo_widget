# Python Tornado Geo Widget

An API widget which provides geographic and network information for a given IP address.

This application uses the GeoLite2-ASN and GeoLite2-City editions of Maxmind's GeoIP as the source information for the IP address details. The MaxMind databases can be downloaded using the `get_maxmind_database.sh` script. This script accepts an API key for your own Maxmind account and will unpack the database files once downloaded.

See Also:

* https://www.maxmind.com/en/geoip-databases
* https://dev.maxmind.com/geoip/geolite2-free-geolocation-data




# Building and Running 

## Building and running using a container
These instructions are written for Podman. Replace `podman` with `docker` as needed:

Building an image:

    podman build --tag tornado-geo-widget:${TAG:=v1} .

View available application options:

    podman run --rm --name tornado-geo-widget-help tornado-geo-widget:${TAG:=v1} --help
    
Download and unpack the MaxMind databases in a directory named `db`:

    mkdir db && cd db
    get_maxmind_database.sh -u -e GeoLite2-ASN,GeoLite2-City -k "${MAXMIND_API_KEY}"

Run a container instance:

    podman run --rm --detach --tty --publish 8889:8888/tcp \
    --name tornado-geo-widget --volume ./db:/var/db:ro \
    tornado-geo-widget:v1 --mmdb /var/db --port 8893

Python Actix Geo Widget Endpoints:

* `/address/<IP Address>` look up of a specific address
* `/address` look up of the requesting client's address ("what is my ip")