# -*- coding: utf-8 -*-


class S3ResponseError(Exception):
    """Class for all HTTP errors received from S3. See
    http://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html for all
    potential errors.
    """
    pass


class Future(object):
    """Wraps a crochet.EventualResult object to provide a simple interface to
    HTTP results.

    Usage:
    future = S3Client.get(...)
    response = future.result(2)
    """
    def __init__(self, eventual, response_class):
        self.eventual = eventual
        self.response_class = response_class

    def result(self, timeout=None):
        """Block for `timeout` seconds on the results of the S3 HTTP call.

        :param timeout: time to block waiting for results of the HTTP call.
        :type timeout: float or int
        :raises crochet.TimeoutError: if the result is not ready before
        `timeout` is hit.
        :raises S3ResponseError: if the HTTP call is not successful, e.g. a
        403 response is received.
        """
        result = self.eventual.wait(timeout)
        if result.code >= 300:
            raise S3ResponseError(
                "S3 returned status code: {code} with body: {body}".format(
                    code=result.code,
                    body=result.body,
                ),
            )
        else:
            return self.response_class(result)
