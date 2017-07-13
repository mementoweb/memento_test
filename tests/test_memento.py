# -*- coding: utf-8 -*-

from memento_test.server import application, \
    convert_to_datetime, \
    parse_link_header, get_uri_dt_for_rel
import unittest
import logging
from werkzeug.test import Client, EnvironBuilder

#logging.getLogger(__name__)
#logging.basicConfig(level=logging.DEBUG)


class MementoTest(unittest.TestCase):

    def test_on_all_headers(self):

        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "all_headers")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link")
        assert headers.get("Memento-Datetime") is not None

        lh = parse_link_header(headers.get("Link"))

        assert get_uri_dt_for_rel(lh, ["original"]) is not None
        assert get_uri_dt_for_rel(lh, ["first"]) is not None
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
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "required_headers")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link")
        assert headers.get("Memento-Datetime") is not None

        lh = parse_link_header(headers.get("Link"))

        assert get_uri_dt_for_rel(lh, ["original"]) is not None

    def test_on_no_headers(self):

        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "no_headers")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert not headers.get("Link")
        assert headers.get("Memento-Datetime") is None

    def test_on_no_link_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "no_link_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert not headers.get("Link")
        assert headers.get("Memento-Datetime") is not None

    def test_on_invalid_link_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "invalid_link_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link")
        assert headers.get("Memento-Datetime") is not None

        with self.assertRaises(Exception):
            parse_link_header(headers.get("Link"))

    def test_on_no_original_link_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "no_original_link_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link") is not None
        assert headers.get("Memento-Datetime") is not None

        lh = parse_link_header(headers.get("link"))
        assert not get_uri_dt_for_rel(lh, ["original"])

    def test_on_invalid_datetime_in_link_header(self):

        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "invalid_datetime_in_link_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link")
        assert headers.get("Memento-Datetime") is not None

        lh = parse_link_header(headers.get("Link"))
        memento = get_uri_dt_for_rel(lh, ["memento"]).get("memento")

        with self.assertRaises(ValueError):
            convert_to_datetime(memento.get("datetime")[0])

    def test_on_no_memento_dt_header(self):
        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "no_memento_dt_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link")
        assert headers.get("Memento-Datetime") is None
        lh = parse_link_header(headers.get("Link"))

        assert get_uri_dt_for_rel(lh, ["original"]) is not None

    def test_on_invalid_memento_dt_header(self):
        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "invalid_memento_dt_header")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "200" in status
        assert headers.get("Link")
        assert headers.get("Memento-Datetime") is not None
        with self.assertRaises(ValueError):
            convert_to_datetime(headers.get("Memento-Datetime"))

        lh = parse_link_header(headers.get("Link"))

        assert get_uri_dt_for_rel(lh, ["original"]) is not None

    def test_on_valid_archived_redirect(self):
        client = Client(application)
        builder = EnvironBuilder(path="/20160101010101/http://www.espn.com",
                                 headers=[("Prefer", "valid_archived_redirect")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Link") is not None
        assert headers.get("Memento-Datetime") is not None
        lh = parse_link_header(headers.get("Link"))

        assert get_uri_dt_for_rel(lh, ["original"]) is not None
        assert headers.get("Location") is not None

    def test_on_valid_internal_redirect(self):
        client = Client(application)
        builder = EnvironBuilder(path="/20160101010101/http://www.espn.com",
                                 headers=[("Prefer", "valid_internal_redirect")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Location") is not None

    def test_on_invalid_archived_redirect(self):
        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "invalid_archived_redirect")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Location") is None \
               or headers.get("Link") is None \
               or headers.get("Memento-Datetime") is None

    def test_on_invalid_internal_redirect(self):
        client = Client(application)
        builder = EnvironBuilder(path="/2016/http://www.espn.com",
                                 headers=[("Prefer", "invalid_internal_redirect")])
        env = builder.get_environ()
        app_iter, status, headers = client.run_wsgi_app(env)

        assert "302" in status
        assert headers.get("Location") is None \
               or headers.get("Link") is None \
               or headers.get("Memento-Datetime") is None
