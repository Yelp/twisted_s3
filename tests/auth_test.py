# -*- coding: utf-8 -*-
"""
These examples from
http://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-header-based-auth.html#example-signature-calculations
"""
import datetime

import pytest
import pytz

from twisted_s3 import auth


@pytest.fixture
def expected_query_string():
    return (
        "response-content-encoding=utf-8&"
        "response-content-type=application%2Fjson"
    )


@pytest.fixture
def expected_canonical_request():
    content_sha = (
        "e3b0c44298fc1c149afbf4c8996fb924"
        "27ae41e4649b934ca495991b7852b855"
    )
    return "\n".join([
        "GET",
        "/test.txt",
        "",
        "host:examplebucket.s3.amazonaws.com",
        "range:bytes=0-9",
        "x-amz-content-sha256:{sha}".format(sha=content_sha),
        "x-amz-date:20130524T000000Z",
        "",
        "host;range;x-amz-content-sha256;x-amz-date",
        content_sha,
    ])


@pytest.fixture
def expected_string_to_sign():
    return "\n".join([
        "AWS4-HMAC-SHA256",
        "20130524T000000Z",
        "20130524/us-east-1/s3/aws4_request",
        "7344ae5b7ee6c3e7e6b0fe0640412a37625d1fbfff95c48bbb2dc43964946972",
    ])


@pytest.fixture
def expected_signing_key():
    # Value pre-computed based on secret_key fixture
    return (
        b"\xa0\x9b\xcb\xe9\x03\x8c\xa3\xae\x02\x07\xfa<\xab\x00"
        b"\xd9\xe8\x9b\xf6o_!\xe3\xbd\xcc\xb3\x1c\xbb\xf0|\x9c\xb1\xde"
    )


@pytest.fixture
def expected_auth_header(access_key, request_datetime):
    signature = "8d3949b63f8a03a2a88892eac8fc9dfa7e16689060d13591281019cd2cef2789"
    return (
        "AWS4-HMAC-SHA256 "
        "Credential={access_key}/{datestr}/us-east-1/s3/aws4_request, "
        "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, "
        "Signature={signature}"
    ).format(
        access_key=access_key,
        datestr=request_datetime.strftime(auth.DATE_FMT),
        signature=signature,
    )


@pytest.fixture
def request_datetime():
    return datetime.datetime(2013, 5, 24, tzinfo=pytz.utc)


@pytest.fixture
def access_key():
    return "AKIAIGEE5NOTMIIAAAAA"


@pytest.fixture
def secret_key():
    return "fakekeywg5QN60eASHGsL46obAsk2AK14ne0boea"


@pytest.fixture
def request_params(request_datetime):
    hashed_payload = auth.compute_hashed_payload(b"")
    return {
        "method": "GET",
        "path": "/test.txt",
        "bucket": "examplebucket",
        "region": "us-east-1",
        "headers": {
            "host": "examplebucket.s3.amazonaws.com",
            "x-amz-date": request_datetime.strftime(auth.ISO8601_FMT),
            "x-amz-content-sha256": hashed_payload,
            "Range": "bytes=0-9",
        },
        "query_string": "",
    }


@pytest.fixture
def canonical_request(request_params):
    canonical_request, _ = auth.canonicalize_request(
        request_params["method"],
        request_params["path"],
        request_params["bucket"],
        request_params["region"],
        request_params["headers"],
        request_params["query_string"],
        request_params["headers"]["x-amz-content-sha256"],
    )
    return canonical_request


def test_create_canonical_query_string_empty():
    query_string = auth.create_canonical_query_string({})
    assert query_string == ""


def test_create_canonical_query_string_value_error():
    with pytest.raises(ValueError):
        auth.create_canonical_query_string({1: 1})


def test_create_canonical_query_string(expected_query_string):
    query_string = auth.create_canonical_query_string({
        "response-content-type": "application/json",
        "response-content-encoding": "utf-8",
    })
    assert query_string == expected_query_string


def test_canonicalize_request(canonical_request, expected_canonical_request):
    assert canonical_request == expected_canonical_request


def test_string_to_sign(
    canonical_request,
    expected_string_to_sign,
    request_datetime,
    request_params,
):
    string_to_sign, _ = auth.create_string_to_sign(
        canonical_request,
        request_params["region"],
        request_datetime,
    )
    assert string_to_sign == expected_string_to_sign


def test_signing_key(
    secret_key,
    expected_signing_key,
    request_datetime,
    request_params,
):
    signing_key = auth.create_signing_key(
        request_datetime,
        secret_key,
        request_params["region"],
    )
    assert signing_key == expected_signing_key


def test_compute_auth_header(
    request_datetime,
    request_params,
    access_key,
    secret_key,
    expected_auth_header,
):
    auth_header = auth.compute_auth_header(
        request_params["headers"],
        request_params["method"],
        request_datetime,
        request_params["region"],
        request_params["bucket"],
        request_params["path"],
        request_params["query_string"],
        request_params["headers"]["x-amz-content-sha256"],
        access_key,
        secret_key,
    )
    assert auth_header == expected_auth_header
