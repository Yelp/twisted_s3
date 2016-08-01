"""
Using AWS Version 4 signing method to make a request to s3. There are multiple
ways to sign requests to AWS, we're using the Authorization Header method.
http://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-auth-using-authorization-header.html

The basic algorithm is:
    1. Create a "string to sign", a concatenation of select request elements
    2. Create a "signing key", a key created from hashing the secret key and
       date, region, and service (e.g. S3) elements.
    3. Use signing key to sign string to sign, include as Authorization header
       on request.

"""
import hashlib
import hmac
import six
if six.PY3:
    from urllib.parse import quote  # pragma: no cover
    from urllib.parse import quote_plus  # pragma: no cover
else:
    from urllib import quote  # pragma: no cover
    from urllib import quote_plus  # pragma: no cover


ISO8601_FMT = "%Y%m%dT%H%M%SZ"
DATE_FMT = "%Y%m%d"


def compute_hashed_payload(payload):
    return hashlib.sha256(payload).hexdigest()


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def create_canonical_query_string(query_params):
    """Canonical query params for S3 requests are all url-encoded and sorted
    by key name. E.g. {"mimeType": "application/json", "limit": 20} will yield
    a query_string of "limit=20&mimeType=application%2Fjson"

    :param query_params: dict of query params
    :type query_params: dict with str keys
    """
    string_params = []
    for key in sorted(query_params.keys()):
        if not isinstance(key, six.string_types):
            raise ValueError("Query param keys must be strings")
        string_params.append(
            quote_plus(key) + "=" + quote_plus(query_params[key])
        )
    return "&".join(string_params)


def create_canonical_headers(headers, bucket, region):
    """Canonical headers is a list of certain request headers and values,
    separated by newlines, adhering to some AWS-specific rules. Signed headers
    is just a sorted list of all included canonical headers.

    Rules:
    - header names must be lowercase
    - sorted alphabetically by name
    - trailing whitespace in values is trimmed
    - "host" header is always required. In our case, this will always be
      "s3.amazonaws.com"
    - "x-amz-content-sha256" (hash of payload) is always required. If there is
      no payload, you must provide the hash of the empty string.
    - if "Content-Type" header is present, it must be included
    - all "x-amz-" prefixed headers must be included
    - any additional headers *can* be included. We will include them, as AWS
      docs claim this adds increased security.
    """
    headers = dict(
        (name.lower(), value.strip())
        for name, value in six.iteritems(headers)
    )

    sorted_headers = sorted(six.iteritems(headers))
    signed_headers = ";".join(
        name for (name, value) in sorted_headers
    )
    canonical_headers = "\n".join(
        name + ":" + value for (name, value) in sorted_headers
    )
    canonical_headers += "\n"
    return signed_headers, canonical_headers


def canonicalize_request(
    method,
    path,
    bucket,
    region,
    headers,
    canonical_query_string,
    hashed_payload,
):
    """Creates a the "canonical request" used in signing AWS sigv4 requests.
    See http://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-header-based-auth.html#canonical-request  # noqa

    HTTPMethod + "\n" +
    CanonicalURI + "\n" +
    CanonicalQueryString + "\n" +
    CanonicalHeaders + "\n" +
    SignedHeaders + "\n" +
    HexEncode(Hash(RequestPayload))

    Note that this is simply a way of organizing and serializing the HTTP request
    for authorization purposes.
    """
    canonical_uri = quote(path)
    signed_headers, canonical_headers = create_canonical_headers(
        headers,
        bucket,
        region,
    )

    elements = [
        method,
        canonical_uri,
        canonical_query_string,
        canonical_headers,
        signed_headers,
        hashed_payload,
    ]
    return "\n".join(elements), signed_headers


def create_string_to_sign(canonical_request, region, dt):
    """The string to sign is a string in a specific format:
    "AWS4-HMAC-SHA256" + "\n" +
    ISO-8601 timestamp + "\n" +
    Scope + "\n" +
    Hex(SHA256Hash(CanonicalRequest))

    Scope is date + "/" + region + "/" + service + "/" + "aws4_request"
    """
    scope_elements = [
        dt.strftime(DATE_FMT),
        region,
        "s3",
        "aws4_request",
    ]
    scope = "/".join(scope_elements)
    string_elements = [
        "AWS4-HMAC-SHA256",
        dt.strftime(ISO8601_FMT),
        scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ]
    string_to_sign = "\n".join(string_elements)
    return string_to_sign, scope


def create_signing_key(now, secret_key, region):
    date_key = sign(("AWS4" + secret_key).encode("utf-8"), now.strftime("%Y%m%d"))
    region_key = sign(date_key, region)
    service_key = sign(region_key, "s3")
    return sign(service_key, "aws4_request")


def format_auth_header(access_key, scope, signed_headers, signature):
    return (
        "AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
        "SignedHeaders={signed_headers}, Signature={signature}"
    ).format(
        access_key=access_key,
        scope=scope,
        signed_headers=signed_headers,
        signature=signature,
    )


def compute_auth_header(
    headers,
    method,
    dt,
    region,
    bucket,
    path,
    canonical_query_string,
    hashed_payload,
    access_key,
    secret_key,
):
    # Format HTTP request for signing
    canonical_request, signed_headers = canonicalize_request(
        method,
        path,
        bucket,
        region,
        headers,
        canonical_query_string,
        hashed_payload,
    )
    string_to_sign, scope = create_string_to_sign(canonical_request, region, dt)
    # Sign request
    signing_key = create_signing_key(dt, secret_key, region)
    signature = hmac.new(
        signing_key,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    # Format Authorization header
    return format_auth_header(
        access_key,
        scope,
        signed_headers,
        signature,
    )
