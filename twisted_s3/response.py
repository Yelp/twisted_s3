# -*- coding: utf-8 -*-
import re
from xml.etree import ElementTree


class S3Response(object):
    """An object representing an HTTP response from S3. This is for simple
    HTTP responses that don't need extra parsing. The only two attributes it
    exposes officially are .code (response code) and .body (response body).

    Unofficially, however, the full HTTP response can be accessed using
    ._response. This will be a `fido.Response` object. You can use this to
    access the response's headers.
    """
    def __init__(self, response):
        self._response = response

    @property
    def code(self):
        """HTTP response code"""
        return self._response.code

    @property
    def body(self):
        """HTTP response body"""
        return self._response.body


class ListResponse(S3Response):
    """An object representing parsed XML returned by List Objects v2 endpoint.
    http://docs.aws.amazon.com/AmazonS3/latest/API/v2-RESTBucketGET.html

    Example usage:
    client = S3Client(...)
    response = S3Client.list().result()
    print(response.keys)  # list of strings
    """

    # S3's XML responses are namespaced, such that the XML tags always begin
    # with, e.g. "{http://s3.amazonaws.com/doc/2006-03-01/}". Instead of
    # hardcoding these tags, we'll use a regex to extract them, future-proofing
    # against them changing the tag.
    NS_PATTERN = re.compile(r"\{http.*?\}")

    def __init__(self, response):
        super(ListResponse, self).__init__(response)

        self._root = ElementTree.fromstring(response.body)
        self._namespace = ListResponse._get_namespace(self._root)

        self._is_truncated = ListResponse._get_is_truncated(
            self._root,
            self._namespace,
        )
        self._continuation_token = None
        if self._is_truncated:
            self._continuation_token = ListResponse._get_continuation_token(
                self._root,
                self._namespace,
            )

        self._keys = None
        self._common_prefixes = None

    @property
    def is_truncated(self):
        """If there are more keys/common_prefixes than are returned as part of
        this result. If true, more HTTP calls will have to be made using
        continuation_token to get the bucket's entire contents. See the docstring
        for continuation_token for more info.
        """
        return self._is_truncated

    @property
    def continuation_token(self):
        """A special token that only AWS understands, used to paginate results.

        Example:
            r = client.list(limit=10).result()
            while r.is_truncated:
                print(r.keys)
                r = client.list(limit=10, continuation_token=r.continuation_token).result()  # noqa
        """
        return self._continuation_token

    @property
    def keys(self):
        """Object paths returned by this list operation. Note that if
        a delimiter is specified, this property will *not* include keys rolled
        up under common_prefixes. For more information see the common_prefixes
        docstring.
        """
        if self._keys is None:
            self._keys = [
                element.text for element in
                self._root.findall(
                    "{ns}Contents/{ns}Key".format(ns=self._namespace)
                )
            ]
        return self._keys

    @property
    def common_prefixes(self):
        """List of common prefixes. This attribute will only have entries if
        a delimiter is specified. In this case, keys that share a common prefix
        will be left out of .keys. See the AWS documentation for more information.

        As a concrete example, imagine your bucket contains the following objects:
        a/b/1
        a/b/2
        a/3
        a/4

        Example with delimiter::
            r = client.list(prefix="a/", delimiter="/").result()
            print(r.keys)  # prints ["a/3", "a/4"]
            print(r.common_prefixes)  # prints ["a/b/"]

        Example without delimiter::
            r = client.list(prefix="path/").result()
            print(r.keys)  # prints ["a/b/1", "a/b/2", "a/3", "a/4"]
            print(r.common_prefixes)  # prints []
        """
        if self._common_prefixes is None:
            self._common_prefixes = [
                element.text for element in
                self._root.findall(
                    "{ns}CommonPrefixes/{ns}Prefix".format(ns=self._namespace)
                )
            ]
        return self._common_prefixes

    @classmethod
    def _get_namespace(cls, element):
        match = cls.NS_PATTERN.match(element.tag)
        return match.group()

    @staticmethod
    def _get_is_truncated(root, namespace):
        # The relevant XML tag looks like <IsTruncated>false</IsTruncated>
        return root.find(
            "{ns}IsTruncated".format(ns=namespace)
        ).text == "true"

    @staticmethod
    def _get_continuation_token(root, namespace):
        return root.find(
            "{ns}NextContinuationToken".format(ns=namespace)
        ).text
