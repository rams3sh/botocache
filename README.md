# Botocache

Caching layer for Boto / Botocore libraries.


## Background

---

This project was started to solve the issue raised [here](https://github.com/boto/boto3/issues/2723).

My day job requires me to write and use multiple tools and standalone scripts to audit AWS environments. 
Most of these tools are hacky and written in python which uses boto3 / botocore in the backend to interact with AWS API.

Sometimes, I would have to write a wrapper to combine these scripts to get a custom consolidated report. 
Since these scripts are standalone, they repeat the same API calls that a previous script would have already 
called before, leading to redundant API calls, throttling and unnecessary IO wait. 

These wrapped tools are sometimes even used as Lambda for automation of certain things. 
The IO wait times becomes a bottleneck when used in environment such as Lambda where execution is a 
time-bound activity. 

Hence I was looking for a caching layer over boto that can solve reducing these direct redundant calls and 
the wait times. Thus the birth of botocache.


## About

---

Botocache caches the response of API calls initiated through boto3 / botocore.
Any subsequent redundant call will end up getting the previously cached response from Botocache as long as the call is
within the expiry timeout of the cached response. 

Botocache can work with any cache library that is based on [cachetools](https://github.com/tkem/cachetools/)

It uses the unittest module's patch as the magic component to achieve this. :wink:

This project is little hacky given the nature how it achieves caching, but it gets the job done. 


## Installation

---
Stable release installation (PyPI) :-
```bash
pip3 install botocache
```

Test release installation (Test PyPI)
```bash
pip install -i https://test.pypi.org/pypi/ --extra-index-url https://pypi.org/simple botocache
```

Installation directly from this Repository:-
```bash
pip3 install git+https://github.com/rams3sh/botocache.git
```


## Usage

---

Below snippet demonstrates usage of botocache.

```python
from boto3.session import Session
from cachetools_ext.fs import FSLRUCache

from botocache.botocache import botocache_context

cache = FSLRUCache(ttl=900, path=".cache", maxsize=1000)

# action_regex_to_cache parameter consists list of regex to be matched against a given action for considering the call to be cached
with botocache_context(cache=cache,
                       action_regex_to_cache=["List.*", "Get.*", "Describe.*"],  
                       call_log=True, # This helps in logging all calls made to AWS. Useful while debugging. Default value is False.
                       supress_warning_message=False # This supresses warning messages encountered while caching. Default value is False. 
                       ):
  cached_session = Session()
  cached_client = cached_session.client('iam')
  paginator = cached_client.get_paginator('list_users')
  for page in paginator.paginate():
    print(page)

"""
Don't do this, if you want to have a new session without caching. 
The below paginator object was initialised under the botocache context which means it's subsequent 
attributes was initialised with patched Botocache class leading it to still use the backend cache. 
"""
for page in paginator.paginate():
  print(page)

"""
Always use a fresh initialised session client and subsequent new objects outside the context of botocache to use 
boto3 without caching layer. Below is an example. 
"""

non_cached_session = Session()
non_cached_client = non_cached_session.client('iam')
paginator = non_cached_client.get_paginator('list_users')
for page in paginator.paginate():
  print(page)

```
**Note:** 

Botocache has been tested with cachetools_ext's FSLRU cache, but it should logically work with any cache that is 
compatible with cachetools.


## Disclaimer(s)

---

* This project was created mainly to support my specific internal use cases. 
Hence, there is a good scope of it having bugs and functional issues. Feel free to raise a PR / Issue in those cases.


* Botocache does not understand [HTTP related caching specification](https://tools.ietf.org/html/rfc7234).
It works based on function caching.Its a very simple dumb caching layer that checks for specific attributes in an API call, converts into a key 
and stores the response against the key. 
Any subsequent call having matching attributes will be returned with the value stored against the same key.