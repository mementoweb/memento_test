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

## Install
```bash
$ cd /path/to/memento_test
$ python setup.py install
```

## Starting the Server
```bash
$ memento_test_server
```

## Preferences

For complete information on the Memento 
headers, please refer to the [Memento RFC](http://mementoweb.org/guide/rfc/)

### TimeGate Preferences
For each of the parameters below, the TimeGate will respond by providing:  
* `all_headers`: All required and recommended Memento headers.
* `required_headers`: Only the required Memento headers.
* `no_headers`: No Memento headers. 
* `no_link_header`: No `Link` header, but other relevant Memento headers will be returned.  
* `no_vary_header`: No `Vary` header, but other relevant Memento headers will be returned.
* `no_original_link_header`: No `rel="original"` URL will be provided in the `Link` header.  
* `invalid_vary_header`: An invalid value in the `Vary` header instead of `accept-datetime`. 
* `invalid_link_header`: An invalid, un-parseable `Link` header value.
* `invalid_datetime_in_link_header`: Invalid datetime values in the `Link` header.
* `no_accept_dt_error`: HTTP 400 error is returned as the TG cannot handle requests without 
`Accept-Datetime`.
* `tg_no_redirect`: TG not redirecting by providing no `Location` header and a non `30*` HTTP response code.
* `tg_302`: A valid TG response with a `302` response. Identical to `all_headers`.
* `tg_303`: A valid TG response with a `303` response.
* `tg_200`: A valid `200` style response from TG with `Content-Location` header.
* `tg_302_no_location_header`: A `tg_302` response without the `Location` header.
* `tg_303_no_location_header`: A `tg_303` response without the `Location header.
* `tg_200_no_memento_dt_header`: A `tg_200` response withtout the required `Memento-Datetime` header.
* `tg_no_accept_dt_no_redirect_to_last_memento`: No redirect to the `last memento` URL when no `Accept-Datetime`
is provided in the request.
* `tg_no_accept_dt_redirect_to_last_memento`: Redirect correctly to the `last memento` URL when no `Accept-Datetime`
is provided in the request.
* `tg_302_memento_dt_header`: A `Memento-Datetime` header is returned for a `302` TG response. 

### Memento Preferences

* `all_headers`: All required and recommended Memento headers.
* `required_headers`: Only the required Memento headers.
* `no_headers`: No Memento headers. 
* `no_link_header`: No `Link` header, but other relevant Memento headers will be returned.  
* `no_original_link_header`: No `rel="original"` URL will be provided in the `Link` header.  
* `invalid_link_header`: An invalid, un-parseable `Link` header value.
* `invalid_datetime_in_link_header`: Invalid datetime values in the `Link` header.
* `no_memento_dt_header`: No `Memento-Datetime` header.
* `invalid_memento_dt_header`: Invalid value for the `Memento-Datetime` header.
* `valid_archived_redirect`: All the required and recommended headers for an archived redirect. 
* `valid_internal_redirect`: All the required and recommended headers for an internal redirect. 
* `invalid_archived_redirect`: Invalid headers for an archived redirect.
* `invalid_internal_redirect`: Invalid headers for an internal redirect.

TODO: 
* `invalid_accept_dt_header`
* `relative_url_in_location_header`