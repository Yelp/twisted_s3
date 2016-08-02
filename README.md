# twisted_s3

`twisted_s3` provides an asynchronous HTTP client for interacting with AWS S3.
It is built on the very simple [Fido](https://github.com/Yelp/fido) HTTP client,
which is in turn based on [Twisted](https://github.com/itamarst/crochet) and
[Crochet](https://github.com/itamarst/crochet). It is meant to be as
simple and easy to use as possible and as such closely mimics Fido's interface.

## Example Usage

Here's how to get a file from S3 using `twisted_s3`:

```python
client = S3Client(access_key, secret_key, region="us-west-2", bucket="my-bucket")
future = client.get("logs/2016/0001.gz")
# Work happens in a background thread...
response = future.result(timeout=2)
print(response.body)
```

And an example of setting an object's value:

```python
client = S3Client(access_key, secret_key, region="us-west-2", bucket="my-bucket")
future = client.put("path/to/file", b"new\nkey\content")
# Work happens in a background thread...
response = future.result(timeout=2)
print(response.code)  # If successful, prints "200"
```

And an example of listing keys in a bucket:

```python
client = S3Client(access_key, secret_key, region="us-west-2", bucket="my-bucket")
future = client.list("path/to/", limit=10)
# Work happens in a background thread...
response = future.result(timeout=2)
print(response.keys)  # Prints 10 keys starting with "path/to/"
```

## Installation

twisted_s3 can be installed like any other python package, using `pip`. Like so:

```bash
$ pip install twisted_s3
```

## License

Copyright (c) 2016, Yelp, Inc. All rights reserved.
Apache v2
