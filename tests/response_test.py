# -*- coding: utf-8 -*-
import mock

import pytest
from fido import Response

from twisted_s3.response import ListResponse


@pytest.fixture(scope="module")
def list_response_xml():
    with open("tests/data/list_response.xml") as xml_file:
        return xml_file.read()


@pytest.fixture(scope="module")
def truncated_list_response_xml():
    with open("tests/data/truncated_list_response.xml") as xml_file:
        return xml_file.read()


def mock_response(response_xml):
    response = mock.Mock(
        spec=Response,
        body=response_xml,
        code=200,
    )
    return response


def test_list_response(list_response_xml):
    response = mock_response(list_response_xml)
    list_response = ListResponse(response)
    assert list_response.code == 200
    assert list_response.contents == list_response_xml
    assert list_response.keys == ["path/test/00", "path/test/01"]
    assert list_response.common_prefixes == []
    assert not list_response.is_truncated
    assert list_response.continuation_token is None


def test_list_response_truncated(truncated_list_response_xml):
    response = mock_response(truncated_list_response_xml)
    list_response = ListResponse(response)
    assert list_response.code == 200
    assert list_response.contents == truncated_list_response_xml
    assert list_response.keys == ["path/00", "path/01"]
    assert list_response.common_prefixes == ["path/test/", "path/test2/"]
    assert list_response.is_truncated
    assert list_response.continuation_token == "fake-token-omgggg"
