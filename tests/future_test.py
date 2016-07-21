# -*- coding: utf-8 -*-
import mock

import pytest
from crochet import EventualResult
from fido import Response

from twisted_s3.future import Future
from twisted_s3.future import S3ResponseError
from twisted_s3.response import S3Response


def get_mock_eventual(code=200):
    mock_eventual = mock.Mock(spec=EventualResult)
    mock_eventual.wait.return_value = mock.Mock(
        spec=Response,
        code=code,
        body=b"body",
    )
    return mock_eventual


def test_result():
    mock_eventual = get_mock_eventual()
    f = Future(mock_eventual, S3Response)
    response = f.result(timeout=1.0)
    assert isinstance(response, S3Response)
    mock_eventual.wait.assert_called_once_with(1.0)


def test_result_error():
    mock_eventual = get_mock_eventual(403)
    f = Future(mock_eventual, S3Response)
    with pytest.raises(S3ResponseError):
        f.result(timeout=1.0)
