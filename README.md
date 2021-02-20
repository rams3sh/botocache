# Botocache

Caching layer for Boto / Botocore libraries.


## Little Background

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
  
It uses the unittest module's patch as the magic component to achieve this. :wink:

This project is little hacky given the nature how it achieves caching, but it gets the job done. 

## Credits 

---

[cachetools_ext](https://github.com/olirice/cachetools_ext) - I shamelessly copied the base code for sqlite based 
cache from [here](https://github.com/olirice/cachetools_ext/blob/develop/cachetools_ext/sqlite.py) and modified it a 
little to suit the needs of botocache. This  was really a life saver. Thanks to [Oliver Rice](https://github.com/olirice).

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
from botocache.botocache import botocache_context

with botocache_context(cache_max_size=100, cache_ttl=900, cache_path=".cache",
                       call_verbs_to_cache=["List", "Get", "Describe"]):
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

# New botocache context with a new cache
new_botocache_context = botocache_context(cache_max_size=100, cache_ttl=900, cache_path=".new_cache",
                       call_verbs_to_cache=["List", "Get", "Describe"])

with new_botocache_context:
    cached_session = Session()
    cached_client = cached_session.client('iam')
    paginator = cached_client.get_paginator('list_users')
    for page in paginator.paginate():
        print(page)

```

Note: The same cache can be used across multiple parallel running python scripts with each script contibuting 
a new response to the cache. 
## Disclaimer(s)

---

* This project was created mainly to support my internal use cases. 
Hence, there is a good scope of it having bugs and functional issues. Feel free to raise a PR / Issue in those cases.


* Botocache does not understand [HTTP related caching specification](https://tools.ietf.org/html/rfc7234).
It works based on function caching.Its a very simple dumb caching layer that checks for specific attributes in an API call, converts into a key 
and stores the response against the key. 
Any subsequent call having matching attributes will be returned with the value stored against the same key.
  

* Botocache is completely dependent on underlying [SQLITE's mechanism](https://www.sqlite.org/lockingv3.html) 
for handling race conditions of concurrent DB read / write across multiple processes. 

## Known Issues

---
* Botocache currently supports caching of only pickleable objects. Hence API calls 
  such as file downloads from S3 may not be cached as it uses `io.BufferedReader` which is non-pickleable.

