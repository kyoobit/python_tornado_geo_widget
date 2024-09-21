import asyncio
import logging

from datetime import datetime
from json import dumps
from pathlib import Path
from re import search
from urllib.parse import quote_plus

# python -m pip show tornado
# python -m pip install --upgrade pip tornado
import tornado.web
from tornado.log import access_log

# python -m pip show geoip2
# python -m pip install --upgrade pip geoip2
import geoip2.database
import geoip2.errors

HELP = """
Hello World!
--------------------------------------------------------------------------------
This is a Python Tornado Web "GEO" HTTP service.

Available endpoints:

  GET .*/help

    Return this text


  GET /address
  GET /address/<IP Address>
  GET /address/<IP Address>?compact
  GET /address/<IP Address>?auth_only

    Query a database for GEO available data matching an <IP Address>.

    The `<IP Address>' is passed as part of the URI path -or- the <IP Address>
    is taken from a HTTP header in the following order:
      * The last address in the `X-Forwarded-For: <IP Address>' request header.
      * The for field in the `Forwarded: for="<IP Address>"' request header.

    Equivalent:

      GET /address/<IP Address>
      GET /address --header 'X-Forwarded-For: <IP Address>'
      GET /address --header 'Forwarded: for="<IP Address>"'

    The JSON body response uses "pretty" (expanded) formatted unless the
    request includes the `compact' query parameter.

    The JSON body response is suppressed when the request includes the
    `auth_only' query parameter -or- the X-Auth-Only request header.

    The `X-Client-Geo' response header includes a brief GEO summary.

      X-Client-Geo: <city>,<subdivision>/<country>; <asn_organization> (<asn>);
      X-Client-Geo: Gap,Hautes-Alpes/FR; Orange (3215);

Example JSON response structure:

  {
    "address": <str> IP Address used in this query
    "asn": <int> Autonomous System Number (ASN)
    "asn_network": <str> CIDR of the network
    "asn_organization": <str> Organization Name for the ASN
    "city": <str> Assumed city for the address
    "continent": [
      <str> Two letter continent code
      <str> Continent name
          * AF - Africa
          * AS - Asia
          * EU - Europe
          * NA - North America
          * SA - South America
          * OC - Oceania
          * AN - Antarctica
    ],
    "country": [
      <str> Two letter country code (ISO 3166-1 alpha-2)
      <str> Country name
          * See full list: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
    ],
    "subdivisions": [
      <str> Two letter state or province code
      <str> State or province name
    ]
  }

--------------------------------------------------------------------------------
"""


# -----------------------------------------------------------------------------
def log_function(handler, *args, **kwargs):
    """Writes a completed HTTP request to the `access_log'

    See Also:
        https://www.tornadoweb.org/en/stable/web.html#application-configuration
    """
    if handler.get_status() == 404 or handler.get_status() < 400:
        _log_method = access_log.info
    elif handler.get_status() < 500:
        _log_method = access_log.warning
    else:
        _log_method = access_log.error
    request_time = 1000.0 * handler.request.request_time()
    _log_method(
        "{status} {method} {full_url} {duration:0.2f}ms {forwarded}".format(
            status=handler.get_status(),
            method=handler.request.method,
            full_url=handler.request.full_url(),
            duration=request_time,
            forwarded=handler.request.headers.get("forwarded", "-"),
        )
    )


# -----------------------------------------------------------------------------
class HelpHandler(tornado.web.RequestHandler):

    def get(self, *args, **kwargs):
        self.write(HELP)


# -----------------------------------------------------------------------------
class MainHandler(tornado.web.RequestHandler):
    """Handle looking up details about an IP address

    See Also:
      https://github.com/maxmind/GeoIP2-python
    """

    def initialize(self, **kwargs):
        name = f"{Path(__file__).name} -"
        logging.debug(f"{name} initialize - **kwargs: {kwargs!r}")
        self.set_header("Server", "Python/Tornado/Geo")

    def get(self, *args, **kwargs):
        name = f"{Path(__file__).name} -"
        logging.debug(f"{name} get - *args: {args}")
        logging.debug(f"{name} get - **kwargs: {kwargs}")

        # Handle requests for 'ping'
        if self.request.path.endswith("/ping"):
            resp = {"ping": "pong"}
            self.write(resp)
            # Include a trailing line break
            self.write("\n")
            return

        # Client address to lookup
        address = kwargs.get("address")
        logging.debug(f"{name} get - address {type(address)}: {address!r}")

        # https://github.com/maxmind/GeoIP2-python
        database = self.settings["database"]

        # Look for a client IP in proxied request

        # X-Forwarded-For: <IP Address>, <IP Address>, <IP Address>
        x_forwarded_for = self.request.headers.get("X-Forwarded-For")
        logging.debug(
            f"{name} get - x_forwarded_for {type(x_forwarded_for)}: {x_forwarded_for!r}"
        )

        # Forwarded: for="<IP Address>";
        forwarded = self.request.headers.get("Forwarded")
        logging.debug(f"{name} get - forwarded {type(forwarded)}: {forwarded!r}")

        if address is None and x_forwarded_for is not None:
            address = x_forwarded_for.split(",")[-1].strip()
            logging.debug(
                f"{name} get - address {type(address)}: {address!r} (set by x_forwarded_for)"
            )
        elif address is None and forwarded is not None:
            forwarded_for = search(r'for="(?P<address>[^";]+)"', forwarded)
            logging.debug(
                f"{name} get - forwarded_for {type(forwarded_for)}: {forwarded_for!r}"
            )
            if forwarded_for is not None:
                address = forwarded_for.groupdict().get("address")
                logging.debug(
                    f"{name} get - address {type(address)}: {address!r} (set by forwarded)"
                )

        # Catch when there is nothing to lookup
        if address is None:
            self.set_status(204)
            return

        # Collect available data for the address
        resp = {"address": address}

        # Query ASN data
        try:
            result = database["asn"].asn(str(address))
            resp.update(asn=result.autonomous_system_number)
            resp.update(asn_organization=result.autonomous_system_organization)
            resp.update(asn_network=str(result.network))  # IPv4Network
        except geoip2.errors.AddressNotFoundError:
            pass

        # Query address data
        try:
            result = database["city"].city(str(address))
            resp.update(city=result.city.names.get("en"))
            resp.update(
                continent=[
                    result.continent.code,
                    result.continent.names.get("en"),
                ]
            )
            resp.update(
                country=[
                    result.country.iso_code,
                    result.country.names.get("en"),
                ]
            )
            # resp.update(location = result.location)
            # resp.update(postal = result.postal.code)
            resp.update(
                subdivisions=[
                    result.subdivisions.most_specific.iso_code,
                    result.subdivisions.most_specific.name,
                ]
            )
        except geoip2.errors.AddressNotFoundError:
            pass

        logging.debug(f"{name} get - resp {type(resp)}: {resp!r}")

        # Include a response header with a brief GEO summary
        # X-Client-Geo: -,-/US; LEVEL3 (3356);
        # X-Client-Geo: Gap,Hautes-Alpes/FR; Orange (3215);
        try:
            x_client_geo = "".join(
                [
                    quote_plus(str(resp.get("city"))),
                    ",",
                    quote_plus(str(resp.get("subdivisions")[-1])),
                    "/",
                    quote_plus(str(resp.get("country")[0])),
                    "; ",
                    quote_plus(str(resp.get("asn_organization"))),
                    " ",
                    f"({str(resp.get('asn'))});",
                ]
            ).replace("None", "-")
            self.set_header("X-Client-Geo", x_client_geo)
            logging.info(f"{address:<15} ---> 'X-Client-Geo: {x_client_geo}'")
        except Exception as err:
            logging.debug(f"Exception raised: {err}")

        # Pretty print is default, allow compact
        if self.request.arguments.get("compact", False):
            self.write(resp)
            # Include a trailing line break
            self.write("\n")
        # Setting `auth_only' skips returning the body content
        elif self.request.arguments.get("auth_only", False) or self.request.headers.get(
            "X-Auth-Only", False
        ):
            return
        else:
            self.write(dumps(resp, sort_keys=True, indent=4))
            # Include a trailing line break
            self.write("\n")


# -----------------------------------------------------------------------------
def make_app(*args, **kwargs):
    name = f"{Path(__file__).name} -"
    logging.debug(f"{name} make_app - *args: {args}")
    logging.debug(f"{name} make_app - **kwargs: {kwargs}")

    mmdb = kwargs.get("mmdb", Path(__file__).parent)
    logging.debug(f"{name} make_app - mmdb {type(mmdb)}: {mmdb!r}")

    database = {
        "asn": geoip2.database.Reader(f"{mmdb}/GeoLite2-ASN.mmdb"),
        "city": geoip2.database.Reader(f"{mmdb}/GeoLite2-City.mmdb"),
    }
    logging.debug(f"{name} make_app - database {type(database)}: {database!r}")

    for db in database:
        db_metadata = database[db].metadata()
        dt = datetime.fromtimestamp(db_metadata.build_epoch)
        logging.info(
            f"Using {db_metadata.description['en']} build on {dt} (epoch={db_metadata.build_epoch})"
        )

    if kwargs.get("debug", False):
        kwargs.update(autoreload=True)

    return tornado.web.Application(
        [
            (r".*/help$", HelpHandler),
            (r"/address/(?P<address>[\da-fA-F\.:]+)", MainHandler),
            (r"/address", MainHandler),
            (r"/.*", MainHandler),
        ],
        autoreload=kwargs.get("autoreload", False),
        database=database,
        debug=kwargs.get("debug", False),
        log_function=log_function,
    )


# -----------------------------------------------------------------------------
async def main(*args, **kwargs):
    name = f"{Path(__file__).name} -"
    logging.debug(f"{name} main - *args: {args}")
    logging.debug(f"{name} main - **kwargs: {kwargs}")

    app = make_app(**kwargs)
    app.listen(int(kwargs.get("port", 8888)))
    await asyncio.Event().wait()


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
