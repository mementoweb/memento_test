#! /usr/bin/env python
# -*- coding: utf-8 -*-

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.utils import cached_property
from werkzeug.exceptions import HTTPException

from datetime import datetime, date

import logging

logging.getLogger(__name__)
#logging.basicConfig(level=logging.DEBUG)

ARCHIVE_DATE_FORMAT = "%Y%m%d%H%M%S"

TG_PREFERENCES = {"all_headers", "required_headers", "no_headers",
                  "no_link_header", "no_vary_header",
                  "no_original_link_header",
                  "invalid_vary_header", "invalid_link_header", "invalid_datetime_in_link_header",
                  "no_accept_dt_error", "tg_no_redirect", "tg_302", "tg_303", "tg_200",
                  "tg_302_no_location_header", "tg_303_no_location_header",
                  "tg_200_no_memento_dt_header",
                  "tg_no_accept_dt_no_redirect_to_last_memento",
                  "tg_no_accept_dt_redirect_to_last_memento",
                  "tg_302_memento_dt_header"
                  }

MEMENTO_PREFERENCES = {"all_headers", "required_headers", "no_headers",
                       "no_link_header", "no_original_link_header",
                       "no_memento_dt_header", "invalid_memento_dt_header",
                       "invalid_link_header", "invalid_datetime_in_link_header",
                       "valid_archived_redirect", "valid_internal_redirect",
                       "invalid_archived_redirect", "invalid_internal_redirect",
                       }

HOST_NAME = "http://www.example.com"
LINK_TMPL = '<%s>; rel="%s"'
LINK_ADD_PARAM = '; %s="%s"'
HTTP_DT_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


def convert_to_http_datetime(dt):
    """
    Converts a datetime object to a date string in HTTP format.
    eg: datetime() -> "Sun, 01 Apr 2010 12:00:00 GMT"
    :param dt: (datetime) A datetime object.
    :return: (str) The date in HTTP format.
    """
    if not dt:
        return
    return dt.strftime(HTTP_DT_FORMAT)


def convert_to_datetime(dt):
    """
    Converts a date string in the HTTP date format to a datetime obj.
    eg: "Sun, 01 Apr 2010 12:00:00 GMT" -> datetime()
    :param dt: (str) The date string in HTTP date format.
    :return: (datetime) The datetime object of the string.
    """
    if not dt:
        return
    return datetime.strptime(dt, HTTP_DT_FORMAT)


def get_uri_dt_for_rel(links, rel_types):
    """
    Returns the uri and the datetime (if available) for a rel type from the
    parsed link header object.
    :param links: (dict) the output of parse_link_header.
    :param rel_types: (list) a list of rel types for which the uris
                        should be found.
    :return: (dict) {rel: {"uri": "", "datetime": }}
    """
    if not links or not rel_types:
        return

    uris = {}
    for uri in links:
        for rel in rel_types:
            if rel in links.get(uri).get("rel"):
                uris[rel] = {"uri": uri,
                             "datetime": links.get(uri).get("datetime")}
    return uris


def parse_link_header(link):
    """
    Parses the link header character by character.
    More robust than the parser provided by the requests module.

    :param link: (str) The HTTP link header as a string.
    :return: (dict) {"uri": {"rel": ["", ""], "datetime": [""]}...}
    """

    if not link:
        return
    state = 'start'
    data = list(link.strip())
    links = {}

    while data:
        if state == 'start':
            dat = data.pop(0)
            while dat.isspace():
                dat = data.pop(0)

            if dat != "<":
                raise ValueError("Parsing Link Header: Expected < in "
                                 "start, got %s" % dat)

            state = "uri"
        elif state == "uri":
            uri = []
            dat = data.pop(0)

            while dat != ";":
                uri.append(dat)
                try:
                    dat = data.pop(0)
                except:
                    raise ValueError("Error Parsing Link Header.")

            uri = ''.join(uri)
            uri = uri[:-1]
            data.insert(0, ';')

            # Not an error to have the same URI multiple times (I think!)
            if uri not in links:
                links[uri] = {}
            state = "paramstart"
        elif state == 'paramstart':
            dat = data.pop(0)

            while data and dat.isspace():
                dat = data.pop(0)
            if dat == ";":
                state = 'linkparam'
            elif dat == ',':
                state = 'start'
            else:
                raise ValueError("Parsing Link Header: Expected ;"
                                 " in paramstart, got %s" % dat)
        elif state == 'linkparam':
            dat = data.pop(0)
            while dat.isspace():
                dat = data.pop(0)
            param_type = []
            while not dat.isspace() and dat != "=":
                param_type.append(dat)
                dat = data.pop(0)
            while dat.isspace():
                dat = data.pop(0)
            if dat != "=":
                raise ValueError("Parsing Link Header: Expected = in"
                                 " linkparam, got %s" % dat)
            state = 'linkvalue'
            pt = ''.join(param_type)

            if pt not in links[uri]:
                links[uri][pt] = []
        elif state == 'linkvalue':
            dat = data.pop(0)
            while dat.isspace():
                dat = data.pop(0)
            param_value = []
            if dat == '"':
                pd = dat
                dat = data.pop(0)
                while dat != '"' and pd != '\\':
                    param_value.append(dat)
                    pd = dat
                    dat = data.pop(0)
            else:
                while not dat.isspace() and dat not in (',', ';'):
                    param_value.append(dat)
                    if data:
                        dat = data.pop(0)
                    else:
                        break
                if data:
                    data.insert(0, dat)
            state = 'paramstart'
            pv = ''.join(param_value)
            if pt == 'rel':
                # rel types are case insensitive and space separated
                links[uri][pt].extend([y.lower() for y in pv.split(' ')])
            else:
                if pv not in links[uri][pt]:
                    links[uri][pt].append(pv)

    return links


class MementoServer(object):
    """
    Memento Test Server that can be used by Memento clients for testing various scenarios
     from the Memento Protocol. TimeGate and Memento endpoints are provided in this server.

    This server recognizes the "Prefer" HTTP header and clients should use this header to
    express the kind of response that they expect from a Memento endpoint.

    For example, for the TimeGate to respond with only the minimum required Memento headers,
    add the value "required_headers" to the Prefer header of the request.
     ```bash
     $ curl -H "Prefer: required_headers" -I http://localhost:4000/tg/http://www.test.com
       HTTP/1.0 302 FOUND
       Link: <http://www.test.com>; rel="original"
       Vary: accept-datetime
       Location: http://www.example.com/20170713121257/http://www.test.com
       Preference-Applied: required_headers
       Content-Type: text/plain; charset=utf-8

    ```

    A list of all the Preferences that the server recognizes are provided in the
    [docs](../README.md).

    ## Starting the Server
    ```bash
    $ ./memento-test/server.py
    ```

    """

    def __init__(self):
        self.now = datetime.now()
        self.accept_datetime = self.now
        self.uri_r = None
        self.first_datetime = date(2001, 1, 1)
        self.last_datetime = self.now

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    @cached_property
    def url_map(self):
        rules = [
            Rule("/", endpoint="index"),
            Rule("/tg/<path:uri_r>", endpoint="timegate", methods=["GET", "HEAD"]),
            Rule("/<int:mem_dt>/<path:uri_r>", endpoint="memento", methods=["GET", "HEAD"])
        ]
        return Map(rules)

    def dispatch_request(self, request):
        """
        Werkzeug calls this method when a request arrives and the Request object is ready.
        This method checks against the :func: MementoServer.url_map and invokes the
          :func: MementoServer.on_request method to prepare the response.
        :param request:
        :return:
        """
        request.adapter = adapter = self.url_map.bind_to_environ(
            request.environ
        )
        try:
            endpoint, values = adapter.match()

            logging.debug("endpoint: %s" % endpoint)
            logging.debug("values: %s" % values)

            return getattr(self, "on_request")(request, **values)
        except HTTPException as e:
            return e

    def on_request(self, request, uri_r, mem_dt=None):
        """
        Processes the request and prepares the response. Mainly checks the `Prefer` header
        and invokes the appropriate method.
        :param request: the Werkzeug Request object.
        :param uri_r: the uri_r in the request URL
        :param mem_dt: the memento datetime in the request URL
        :return: the werkzeug Response object.
        """

        self.uri_r = uri_r
        if request.headers.get("accept_datetime"):
            self.accept_datetime = convert_to_datetime(request.headers.get("accept_datetime"))
        prefer = request.headers.get("prefer")

        headers = {}
        status = 302

        logging.debug("prefer: %s" % prefer)
        logging.debug("mem_dt: %s" % mem_dt)

        if not prefer:
            headers, status = self.on_all_headers(request, headers=headers, endpoint="timegate")
            return Response(status=status, headers=headers)

        prefs = prefer.split(",")

        pref_applied = []
        for p in prefs:
            p = p.strip()

            logging.debug(mem_dt)
            logging.debug(p)
            logging.debug(p.strip() in MEMENTO_PREFERENCES)

            if mem_dt and p in MEMENTO_PREFERENCES:
                headers, status = getattr(self, "on_" + p) \
                    (request, headers=headers, endpoint="memento", mem_dt=mem_dt)
                pref_applied.append(p)
            elif p in TG_PREFERENCES:
                headers, status = getattr(self, "on_" + p) \
                    (request, headers=headers, endpoint="timegate")
                pref_applied.append(p)

        logging.debug("Preference applied: %s" % pref_applied)
        if len(pref_applied) > 0:
            headers["Preference-Applied"] = ", ".join(pref_applied)
        else:
            if mem_dt is None:
                headers, status = self.on_all_headers(request, headers=headers, endpoint="timegate")
            else:
                headers, status = self.on_all_headers(request, headers=headers,
                                                      endpoint="memento", mem_dt=mem_dt)

        return Response(status=status, headers=headers)

    def on_all_headers(self, request, headers=None, endpoint=None,
                       mem_dt=None):
        """
        Returns All required and recommended Memento headers.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """

        headers["Link"] = self._create_link_header()
        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        if endpoint == "memento":
            headers["Memento-Datetime"] = mem_http_dt
            return headers, 200
        elif endpoint == "timegate":
            headers["Vary"] = "accept-datetime"
            mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                      "/" + self.uri_r
            headers["Location"] = mem_uri
            return headers, 302

    def on_required_headers(self, request, headers=None, endpoint=None,
                           mem_dt=None):
        """
        Returns Only the required Memento headers.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """

        headers["Link"] = self._create_link_header(original=True, memento=False, first=False, last=False)
        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        if endpoint == "memento":
            headers["Memento-Datetime"] = mem_http_dt
            return headers, 200
        elif endpoint == "timegate":
            headers["Vary"] = "accept-datetime"
            mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                      "/" + self.uri_r
            headers["Location"] = mem_uri
            return headers, 302

    def on_no_headers(self, request, headers=None, endpoint=None,
                      mem_dt=None):
        """
        Returns No Memento headers.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """

        if endpoint == "memento":
            return headers, 200
        elif endpoint == "timegate":
            headers["Location"] = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                  "/" + self.uri_r
            return headers, 302

    def on_no_link_header(self, request, headers=None, endpoint=None,
                          mem_dt=None):
        """
        Returns No `Link` header, but other relevant Memento headers will be returned.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """

        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        if endpoint == "memento":
            headers["Memento-Datetime"] = mem_http_dt
            return headers, 200
        elif endpoint == "timegate":
            headers["Vary"] = "accept-datetime"
            mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                      "/" + self.uri_r
            headers["Location"] = mem_uri
            return headers, 302

    def on_no_vary_header(self, request, headers=None, endpoint=None,
                          mem_dt=None):
        """
        Returns No `Vary` header, but other relevant Memento headers will be returned.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                  "/" + self.uri_r
        headers["Location"] = mem_uri
        return headers, 302

    def on_no_original_link_header(self, request, headers=None, endpoint=None,
                                   mem_dt=None):
        """
        Returns No `rel="original"` URL will be provided in the `Link` header.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header(original=False)
        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        if endpoint == "memento":
            headers["Memento-Datetime"] = mem_http_dt
            return headers, 200
        elif endpoint == "timegate":
            headers["Vary"] = "accept-datetime"
            mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                      "/" + self.uri_r
            headers["Location"] = mem_uri
            return headers, 302

    def on_invalid_vary_header(self, request, headers=None, endpoint=None,
                               mem_dt=None):
        """
        Returns An invalid value in the `Vary` header instead of `accept-datetime`.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        headers["Vary"] = "accept-dt"
        mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                  "/" + self.uri_r
        headers["Location"] = mem_uri
        return headers, 302

    def on_invalid_link_header(self, request, headers=None, endpoint=None,
                               mem_dt=None):
        """
        Returns An invalid, un-parseable `Link` header value.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        #link_header = self._create_link_header()
        headers["Link"] = "<sfafafasfasfafafafafaf, rel='ssss'"
        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        if endpoint == "memento":
            headers["Memento-Datetime"] = mem_http_dt
            return headers, 200
        elif endpoint == "timegate":
            headers["Vary"] = "accept-datetime"
            mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                      "/" + self.uri_r
            headers["Location"] = mem_uri
            return headers, 302

    def on_invalid_datetime_in_link_header(self, request, headers=None,
                                           endpoint=None, mem_dt=None):
        """
        Returns Invalid datetime values in the `Link` header.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """

        mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                  "/" + self.uri_r

        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        link_header = LINK_TMPL % (mem_uri, "memento") + \
            LINK_ADD_PARAM % ("datetime", mem_http_dt[:-2])
        headers["Link"] = link_header
        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        if endpoint == "memento":
            headers["Memento-Datetime"] = mem_http_dt
            return headers, 200
        elif endpoint == "timegate":
            headers["Vary"] = "accept-datetime"
            mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                      "/" + self.uri_r
            headers["Location"] = mem_uri
            return headers, 302

    def on_no_accept_dt_error(self, request, headers=None, endpoint=None,
                              mem_dt=None):
        """
        HTTP 400 error is returned as the TG cannot handle requests without
`Accept-Datetime`.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """

        if not request.headers.get("accept-datetime"):
            return headers, 400
        else:
            return self.on_all_headers(request, headers, endpoint)

    def on_tg_no_redirect(self, request, headers=None, endpoint=None,
                          mem_dt=None):
        """
        TG not redirecting by providing no `Location` header and a non `30*` HTTP response code.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        return headers, 200

    def on_tg_302(self, request, headers=None, endpoint=None,
                  mem_dt=None):
        """
        A valid TG response with a `302` response. Identical to `all_headers`.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        headers["Vary"] = "accept-datetime"
        mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                  "/" + self.uri_r
        headers["Location"] = mem_uri
        return headers, 302

    def on_tg_303(self, request, headers=None, endpoint=None,
                  mem_dt=None):
        """
        A valid TG response with a `303` response.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        headers["Vary"] = "accept-datetime"
        mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                  "/" + self.uri_r
        headers["Location"] = mem_uri
        return headers, 303

    def on_tg_200(self, request, headers=None, endpoint=None,
                  mem_dt=None):
        """
         A valid `200` style response from TG with `Content-Location` header.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        headers["Vary"] = "accept-datetime"
        mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                  "/" + self.uri_r
        headers["Content-Location"] = mem_uri
        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        headers["Memento-Datetime"] = mem_http_dt
        return headers, 200

    def on_tg_302_no_location_header(self, request, headers=None, endpoint=None,
                                     mem_dt=None):
        """
        A `tg_302` response without the `Location` header.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        headers["Vary"] = "accept-datetime"
        return headers, 302

    def on_tg_303_no_location_header(self, request, headers=None, endpoint=None,
                                     mem_dt=None):
        """
        A `tg_303` response without the `Location header.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        headers["Vary"] = "accept-datetime"
        return headers, 303

    def on_tg_200_no_memento_dt_header(self, request, headers=None, endpoint=None,
                                       mem_dt=None):
        """
        A `tg_200` response withtout the required `Memento-Datetime` header.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        headers["Vary"] = "accept-datetime"
        return headers, 200

    def on_tg_no_accept_dt_no_redirect_to_last_memento(self, request, headers=None,
                                                       endpoint=None, mem_dt=None):
        """
        No redirect to the `last memento` URL when no `Accept-Datetime`
is provided in the request.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        if not headers.get("accept-datetime"):
            lh = parse_link_header(headers.get("Link"))
            location = get_uri_dt_for_rel(lh, ["first"])\
                .get("first").get("uri")
            headers["Vary"] = "accept-datetime"
            headers["Location"] = location
            return headers, 302
        return self.on_all_headers(request, headers, endpoint)

    def on_tg_no_accept_dt_redirect_to_last_memento(self, request, headers=None,
                                                    endpoint=None, mem_dt=None):
        """
        Redirect correctly to the `last memento` URL when no `Accept-Datetime`
is provided in the request.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        if not headers.get("accept-datetime"):
            lh = parse_link_header(headers.get("Link"))
            location = get_uri_dt_for_rel(lh, ["last"]) \
                .get("last").get("uri")
            headers["Location"] = location
            headers["Vary"] = "accept-datetime"
            return headers, 302
        return self.on_all_headers(request, headers, endpoint)

    def on_tg_302_memento_dt_header(self, request, headers=None, endpoint=None,
                                    mem_dt=None):
        """
        A `Memento-Datetime` header is returned for a `302` TG response.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        headers["Vary"] = "accept-datetime"
        mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                  "/" + self.uri_r
        headers["Location"] = mem_uri
        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        headers["Vary"] = "accept-datetime"
        headers["Memento-Datetime"] = mem_http_dt
        return headers, 302

    def on_no_memento_dt_header(self, request, headers=None,
                                endpoint=None, mem_dt=None):
        """
        Returns No `Memento-Datetime` header.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        logging.debug("no_memenot_dt_hd")
        headers["Link"] = self._create_link_header()
        return headers, 200

    def on_invalid_memento_dt_header(self, request, headers=None,
                                     endpoint=None, mem_dt=None):
        """
        Returns Invalid value for the `Memento-Datetime` header.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header(original=False)
        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        headers["Memento-Datetime"] = mem_http_dt[:-2]
        return headers, 200

    def on_valid_archived_redirect(self, request, headers=None,
                                   endpoint=None, mem_dt=None):
        """
        Returns All the required and recommended headers for an archived redirect.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header()
        mem_http_dt = convert_to_http_datetime(self.accept_datetime)
        headers["Memento-Datetime"] = mem_http_dt
        headers["Location"] = HOST_NAME + "/" + \
            self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT)[:-6] + \
            "/" + self.uri_r
        return headers, 302

    def on_valid_internal_redirect(self, request, headers=None,
                                   endpoint=None, mem_dt=None):
        """
        Returns All the required and recommended headers for an internal redirect.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Location"] = HOST_NAME + "/" + \
                              self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT)[:-6] + \
                              "/" + self.uri_r
        return headers, 302

    def on_invalid_archived_redirect(self, request, headers=None,
                                     endpoint=None, mem_dt=None):
        """
        Returns Invalid headers for an archived redirect.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        headers["Link"] = self._create_link_header(original=False)
        return headers, 302

    def on_invalid_internal_redirect(self, request, headers=None,
                                     endpoint=None, mem_dt=None):
        """
        Returns Invalid headers for an internal redirect.
        :param request: The request object
        :param headers: dict: the appropriate memento headers to be returned
        :param endpoint: str: the memento endpoint the request was for. `memento`|`timegate`|`timemap`
        :param mem_dt: str: The datetime string provided in the request url similar to
        what IA provides. eg: 20150101243059
        :return: (dict: int) (headers, HTTP status)
        """
        return headers, 302

    def _create_link_header(self, original=True, memento=True, first=True, last=True):

        lh = []
        if original:
            lh.append(LINK_TMPL % (self.uri_r, "original"))
        if first:
            first_uri = HOST_NAME + "/" + self.first_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                    "/" + self.uri_r
            lh.append(LINK_TMPL % (first_uri, "first memento") +
                  LINK_ADD_PARAM % ("datetime", convert_to_http_datetime(self.first_datetime)))

        if last:
            last_uri = HOST_NAME + "/" + self.last_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                   "/" + self.uri_r
            lh.append(LINK_TMPL % (last_uri, "last memento") +
                  LINK_ADD_PARAM % ("datetime", convert_to_http_datetime(self.last_datetime)))
        if memento:
            mem_uri = HOST_NAME + "/" + self.accept_datetime.strftime(ARCHIVE_DATE_FORMAT) + \
                  "/" + self.uri_r

            mem_http_dt = convert_to_http_datetime(self.accept_datetime)
            lh.append(LINK_TMPL % (mem_uri, "memento") +
                  LINK_ADD_PARAM % ("datetime", mem_http_dt))

        return ", ".join(lh)


def application(environ, start_response):
    app = MementoServer()
    return app(environ, start_response)

if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple("localhost", 4000, application)
