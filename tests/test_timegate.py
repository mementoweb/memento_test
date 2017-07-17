# -*- coding: utf-8 -*-

from memento_test.server import application, \
    convert_to_datetime, convert_to_http_datetime,\
    parse_link_header, get_uri_dt_for_rel
import unittest
import logging
from werkzeug.test import Client, EnvironBuilder

#logging.getLogger(__name__)
#logging.basicConfig(level=logging.DEBUG)


class TimeGateTest(unittest.TestCase):

    def test_on_all_headers(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "all_headers")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")

        lh = parse_link_header(headers.get("Link"))

        assert get_uri_dt_for_rel(lh, ["original"]).get("original")
        assert get_uri_dt_for_rel(lh, ["first"])
        f_dt = get_uri_dt_for_rel(lh, ["first"]).get("first")
        assert convert_to_datetime(f_dt["datetime"][0]) is not None
        assert get_uri_dt_for_rel(lh, ["last"])
        l_dt = get_uri_dt_for_rel(lh, ["last"]).get("last")
        assert convert_to_datetime(l_dt["datetime"][0]) is not None
        assert get_uri_dt_for_rel(lh, ["memento"])
        m_dt = get_uri_dt_for_rel(lh, ["memento"]).get("memento")
        assert convert_to_datetime(m_dt["datetime"][0]) is not None

    def test_on_required_headers(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "required_headers")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")

        lh = parse_link_header(headers.get("Link"))

        assert get_uri_dt_for_rel(lh, ["original"])
        assert not get_uri_dt_for_rel(lh, ["first"])
        assert not get_uri_dt_for_rel(lh, ["last"])
        assert not get_uri_dt_for_rel(lh, ["memento"])

    def test_on_no_headers(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "no_headers")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert not headers.get("Link")
        assert "accept-datetime" not in headers.get("Vary", "")

    def test_on_no_link_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "no_link_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert not headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")

    def test_on_no_vary_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "no_vary_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert headers.get("Vary") is None

    def test_on_no_original_link_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "no_original_link_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link") is not None
        assert headers.get("Vary") is not None

        lh = parse_link_header(headers.get("link"))
        assert not get_uri_dt_for_rel(lh, ["original"])
        assert get_uri_dt_for_rel(lh, ["memento"])

    def test_on_invalid_vary_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "invalid_vary_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert headers.get("Vary")
        assert "accept-datetime" not in headers.get("vary", "")

    def test_on_invalid_link_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "invalid_link_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert headers.get("Vary")

        with self.assertRaises(Exception):
            parse_link_header(headers.get("Link"))

    def test_on_invalid_datetime_in_link_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "invalid_datetime_in_link_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert headers.get("Vary")

        lh = parse_link_header(headers.get("Link"))
        memento = get_uri_dt_for_rel(lh, ["memento"]).get("memento")

        with self.assertRaises(ValueError):
            convert_to_datetime(memento.get("datetime")[0])

    def test_on_no_accept_dt_error(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "no_accept_dt_error")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "400" in status

    def test_tg_no_redirect(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_no_redirect")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert not headers.get("Link")
        assert "accept-datetime" not in headers.get("Vary", "")

    def test_tg_302(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_302")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")
        assert headers.get("Location") is not None

        lh = parse_link_header(headers.get("Link"))

        assert get_uri_dt_for_rel(lh, ["original"])
        assert get_uri_dt_for_rel(lh, ["first"])
        f_dt = get_uri_dt_for_rel(lh, ["first"]).get("first")
        assert convert_to_datetime(f_dt["datetime"][0]) is not None
        assert get_uri_dt_for_rel(lh, ["last"])
        l_dt = get_uri_dt_for_rel(lh, ["last"]).get("last")
        assert convert_to_datetime(l_dt["datetime"][0]) is not None
        assert get_uri_dt_for_rel(lh, ["memento"])
        m_dt = get_uri_dt_for_rel(lh, ["memento"]).get("memento")
        assert convert_to_datetime(m_dt["datetime"][0]) is not None

    def test_tg_303(self):
        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_303")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "303" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")
        assert headers.get("Location") is not None

    def test_tg_200(self):
        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_200")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")
        assert headers.get("memento-datetime") is not None

    def test_tg_302_no_location_header(self):
        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_302_no_location_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")
        assert headers.get("Location") is None

    def test_tg_303_no_location_header(self):
        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_303_no_location_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "303" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")
        assert headers.get("Location") is None

    def test_tg_200_no_memento_datetime_header(self):
        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_200_no_memento_dt_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")
        assert headers.get("memento-datetime") is None

    def test_tg_no_accept_dt_no_redirect_to_last_memento(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_no_accept_dt_no_redirect_to_last_memento")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")
        assert headers.get("Location") is not None
        lh = parse_link_header(headers.get("Link"))
        assert get_uri_dt_for_rel(lh, ["last"])
        l_uri = get_uri_dt_for_rel(lh, ["last"]).get("last").get("uri")
        assert l_uri != headers.get("Location")

    def test_tg_no_accept_dt_redirect_to_last_memento(self):

        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_no_accept_dt_redirect_to_last_memento")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")
        assert headers.get("Location") is not None
        lh = parse_link_header(headers.get("Link"))
        assert get_uri_dt_for_rel(lh, ["last"])
        l_uri = get_uri_dt_for_rel(lh, ["last"]).get("last").get("uri")
        assert l_uri == headers.get("Location")

    def test_tg_302_memento_dt_header(self):
        client = Client(application)
        builder = EnvironBuilder(path="/tg/http://www.espn.com",
                                 headers=[("Prefer", "tg_302_memento_dt_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link")
        assert "accept-datetime" in headers.get("Vary", "")
        assert headers.get("Location") is not None
        assert headers.get("Memento-Datetime") is not None


