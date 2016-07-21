# -*- coding: utf-8 -*-
import datetime
import mock

import pytest

from twisted_s3 import auth
from twisted_s3.client import S3Client


@pytest.yield_fixture
def mocked_client():
    client = S3Client("fake_key", "fake_secret")
    with mock.patch.object(client, "_make_request", autospec=True):
        yield client


@pytest.yield_fixture
def mock_fetch():
    with mock.patch("fido.fetch", autospec=True) as mock_fetch:
        yield mock_fetch


@pytest.yield_fixture
def mock_datetime():
    # Hack to get around mock not being able to patch built-ins
    time_now = datetime.datetime.fromtimestamp(100000)
    with mock.patch(
        "twisted_s3.client.datetime.datetime",
        new=mock.Mock(wraps=datetime.datetime),
    ) as mock_datetime:
        mock_datetime.utcnow.return_value = time_now
        yield mock_datetime


@pytest.yield_fixture
def client():
    yield S3Client("fake_key", "fake_secret")


def test_get(mocked_client):
    mocked_client.get(
        "/path/001.gz",
        headers="headers",
        query_params="params",
        region="region",
        bucket="bucket",
    )
    mocked_client._make_request.assert_called_once_with(
        method="GET",
        path="/path/001.gz",
        headers="headers",
        query_params="params",
        payload=b"",
        region="region",
        bucket="bucket",
    )


def test_list_no_args(mocked_client):
    mocked_client.list()
    mocked_client._make_request.assert_called_once_with(
        method="GET",
        path="/",
        headers=None,
        query_params={"list-type": "2"},
        payload=b"",
        region=None,
        bucket=None,
    )


def test_list(mocked_client):
    mocked_client.list(
        prefix="test/",
        limit=10,
        delimiter="/",
        continuation_token="token",
        headers="headers",
        query_params={"start-after": "abc"},
        region="region",
        bucket="bucket",
    )
    mocked_client._make_request.assert_called_once_with(
        method="GET",
        path="/",
        headers="headers",
        query_params={
            "list-type": "2",
            "start-after": "abc",
            "continuation-token": "token",
            "max-keys": "10",
            "prefix": "test/",
            "delimiter": "/",
        },
        payload=b"",
        region="region",
        bucket="bucket",
    )


def test_put(mocked_client):
    mocked_client.put(
        "/path/001.gz",
        b"some bytes",
        headers="headers",
        region="region",
        bucket="bucket",
    )
    mocked_client._make_request.assert_called_once_with(
        method="PUT",
        path="/path/001.gz",
        headers="headers",
        query_params=None,
        payload=b"some bytes",
        region="region",
        bucket="bucket",
    )


def test_make_request_missing_bucket(client):
    with pytest.raises(ValueError):
        client._make_request("GET", "/path/001.gz", None, None, b"")


def test_make_request(client, mock_fetch, mock_datetime):
        client._make_request(
            method="GET",
            path="path/001.gz",
            headers={"header": "blah"},
            query_params={"start-at": "abc"},
            payload=b"",
            region="us-west-2",
            bucket="my-bucket",
        )

        args, kwargs = mock_fetch.call_args

        # Check that the URL is correct
        host = "my-bucket.s3-us-west-2.amazonaws.com"
        assert args[0] == "http://" + host + "/path/001.gz?start-at=abc"
        assert len(args) == 1

        # Check that the headers are correct
        headers = kwargs.pop("headers")
        # We don't care about the actual values of these headers, as they're
        # set by auth code that's tested separately
        for header in ("x-amz-content-sha256", "Authorization"):
            headers.pop(header)

        assert headers == {
            "host": host,
            "x-amz-date": mock_datetime.utcnow().strftime(auth.ISO8601_FMT),
            "header": "blah",
        }

        # Check the rest of the kwargs are correct
        assert kwargs == {"method": "GET", "body": b""}
