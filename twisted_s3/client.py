# -*- coding: utf-8 -*-
import datetime

import fido

from twisted_s3 import auth
from twisted_s3 import response
from twisted_s3.future import Future


class S3Client(object):

    def __init__(
        self, access_key, secret_key,
        region=None, bucket=None,
    ):
        """An asynchronous s3 client based on the fido HTTP utility,
        which is based on twisted/crochet.

        :param access_key: AWS access key ID
        :type access_key: str
        :param secret_key: AWS secret
        :type secret_key: str
        :param region: AWS region
        :type region: str, default None
        :param bucket: AWS bucket
        :type bucket: str, default None
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.bucket = bucket

    def _make_request(
        self, method, path, headers, query_params, payload,
        region=None, bucket=None,
    ):
        """Authenticate and actually make the HTTP request to S3."""
        headers = headers or {}
        query_params = query_params or {}
        region = region or self.region
        bucket = bucket or self.bucket

        if not region or not bucket:
            raise ValueError(
                "Region and bucket must be either set at the client level "
                "or passed in at call time. "
                "Region={region}; Bucket={bucket}".format(
                    region=region,
                    bucket=bucket,
                ),
            )

        hashed_payload = auth.compute_hashed_payload(payload)

        host = "{bucket}.s3-{region}.amazonaws.com".format(
            bucket=bucket,
            region=region
        )
        query_string = auth.create_canonical_query_string(query_params)
        if not path.startswith("/"):
            path = "/" + path

        now = datetime.datetime.utcnow()

        # Add headers necessary for auth computation
        headers["host"] = host
        headers["x-amz-content-sha256"] = hashed_payload
        headers["x-amz-date"] = now.strftime(auth.ISO8601_FMT)
        headers["Authorization"] = auth.compute_auth_header(
            headers,
            method,
            now,
            region,
            bucket,
            path,
            query_string,
            hashed_payload,
            self.access_key,
            self.secret_key,
        )

        url = "http://{host}{path}".format(host=host, path=path)
        if query_string:
            url += "?" + query_string
        return fido.fetch(url, method=method, body=payload, headers=headers)

    def get(
        self,
        path,
        headers=None,
        query_params=None,
        region=None,
        bucket=None,
    ):
        """Get an object from S3. See
        http://docs.aws.amazon.com/AmazonS3/latest/API/RESTObjectGET.html

        Example usage:
        client = S3Client(...)
        future = S3Client.get("/test/key")
        key = future.result()
        print(key.body)  # prints the object's bytes

        :param path: Object path, e.g. "/logs/2016/file.gz"
        :type path: str
        :param headers: Additional headers to send in S3 HTTP request. Note
            that the headers "x-amz-date" and "Authorization" will be added as
            part of the authentication process.
        :type headers: dict, with str keys
        :param query_params: Query parameters to include in the request. This
            is rarely used, but can be useful for, say, getting a specified
            version of an object.
        :type query_params: dict
        :param region: S3 region in which the object resides. E.g. "us-west-2".
        :type region: str
        :param bucket: Name of S3 bucket
        :type bucket: str

        :rtype: Future, returning S3Response.
        """
        return Future(
            self._make_request(
                method="GET",
                path=path,
                headers=headers,
                query_params=query_params,
                payload=b"",
                region=region,
                bucket=bucket,
            ),
            response_class=response.S3Response,
        )

    @staticmethod
    def _add_query_params_for_list(
        query_params,
        prefix,
        limit,
        delimiter,
        continuation_token,
    ):
        query_params["list-type"] = "2"

        if prefix is not None:
            query_params["prefix"] = prefix
        if continuation_token is not None:
            query_params["continuation-token"] = continuation_token
        if limit is not None:
            query_params["max-keys"] = str(limit)
        if delimiter is not None:
            query_params["delimiter"] = delimiter

    def list(
        self,
        prefix=None,
        limit=None,
        delimiter=None,
        continuation_token=None,
        headers=None,
        query_params=None,
        region=None,
        bucket=None,
    ):
        """Get a list of objects in a bucket, filtered by certain criteria. See
        http://docs.aws.amazon.com/AmazonS3/latest/API/v2-RESTBucketGET.html

        Example usage:
        client = S3Client(...)
        future = S3Client.list("test/", limit=10)
        results = future.result()
        print(results.keys)  # returns a list of strings

        :param prefix: Prefix to use to filter results. This should be *without*
            the leading slash. E.g. "logs/2016/" not "/logs/2016/".
        :type prefix: str
        :param limit: Max # of keys to return. Default is 1000. When delimiter
            is specified, each instances of CommonPrefix counts as one key.
        :type limit: int
        :param delimiter: A character used to group keys. If specified, all
            keys with the same string between the prefix and the first
            occurence of delimiter will be grouped under .common_prefixes
        :type delimiter: str
        :param continuation_token: Used to paginate results when more than max
            keys (default 1000).
        :type continuation_token: str
        :param headers: Additional headers to send in S3 HTTP request. Note
            that the headers "x-amz-date" and "Authorization" will be added as
            part of the authentication process.
        :type headers: dict, with str keys
        :param query_params: Additional query params. These are used to limit
            the result set. See above link for more information.
        :param region: S3 region in which the object resides. E.g. "us-west-2".
        :type region: str
        :param bucket: Name of S3 bucket
        :type bucket: str

        :rtype: Future, returning ListResponse.
        """
        query_params = query_params or {}
        S3Client._add_query_params_for_list(
            query_params,
            prefix,
            limit,
            delimiter,
            continuation_token,
        )

        return Future(
            self._make_request(
                method="GET",
                path="/",
                headers=headers,
                query_params=query_params,
                payload=b"",
                region=region,
                bucket=bucket,
            ),
            response_class=response.ListResponse,
        )

    def put(
        self,
        path,
        payload,
        headers=None,
        region=None,
        bucket=None,
    ):
        """Set S3 object at path to payload. See
        http://docs.aws.amazon.com/AmazonS3/latest/API/RESTObjectPUT.html

        Note that S3 REST API doesn't accept query params for PUTs.

        :param path: Object path, e.g. "/logs/2016/file.gz"
        :type path: str
        :param payload: Object payload. I.e. what to put in S3
        :type payload: bytes
        :param headers: Additional headers to send in S3 HTTP request. Note
            that the headers "x-amz-date" and "Authorization" will be added as
            part of the authentication process.
        :type headers: dict, with str keys and str values
        :param region: S3 region in which the object resides. E.g. "us-west-2".
        :type region: str
        :param bucket: Name of S3 bucket
        :type bucket: str

        :rtype: Future, returning S3Response.
        """
        return Future(
            self._make_request(
                method="PUT",
                path=path,
                headers=headers,
                query_params=None,
                payload=payload,
                region=region,
                bucket=bucket,
            ),
            response_class=response.S3Response,
        )
