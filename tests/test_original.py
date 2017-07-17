# -*- coding: utf-8 -*-
from memento_test.server import application, \
    parse_link_header, get_uri_dt_for_rel
import unittest
import logging
from werkzeug.test import Client, EnvironBuilder

#logging.getLogger(__name__)
#logging.basicConfig(level=logging.DEBUG)


class OriginalTest(unittest.TestCase):

    def test_on_native_tg_url(self):

        client = Client(application)
        builder = EnvironBuilder(path="/",
                                 headers=[("Prefer", "native_tg_url")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link") is not None

        lh = parse_link_header(headers.get("Link"))
        assert get_uri_dt_for_rel(lh, ["timegate"]).get("timegate") is not None

    def test_on_no_native_tg_url(self):

        client = Client(application)
        builder = EnvironBuilder(path="/",
                                 headers=[("Prefer", "no_native_tg_url")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status

        lh = parse_link_header(headers.get("Link"))
        assert get_uri_dt_for_rel(lh, ["timegate"]) is None

    def test_on_redirect(self):

        client = Client(application)
        builder = EnvironBuilder(path="/",
                                 headers=[("Prefer", "redirect")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status

        lh = parse_link_header(headers.get("Link"))
        assert get_uri_dt_for_rel(lh, ["timegate"]) is None
        assert headers.get("Location") is not None
