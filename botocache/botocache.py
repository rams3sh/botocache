from botocore.client import BaseClient
from cachetools import cached
import hashlib
from collections import OrderedDict
from unittest.mock import patch
import logging
import re

logger = logging.getLogger(__name__)


def botocache_context(cache=None, action_regex_to_cache=["List.*", "Get.*", "Describe.*"],
                      call_log=False,
                      supress_warning_message=False):

    if not (isinstance(action_regex_to_cache, list)):
        action_regex_to_cache = [action_regex_to_cache]

    class BotoCache(BaseClient):

        def return_cache_key(self, operation_name, api_params):
            cache_key = \
                "{access_key}_{service}_{action}_{region}_{api_params}".format(
                    # Access Key to identify the Principal
                    access_key=self._request_signer._credentials.access_key,
                    # Service for identifying which service is being queried
                    service=self._service_model.service_name,
                    # Action of the service
                    action=operation_name,
                    # Region where the call is being made
                    region=self.meta.region_name,
                    # Api Parameters. This takes care of pagination token, marker and other params.
                    # The API Params dictionary is sorted before hashing
                    api_params=str(OrderedDict(sorted(api_params.items()))))
            hash_gen = hashlib.sha256()
            hash_gen.update(cache_key.encode("utf-8"))
            return hash_gen.hexdigest()

        def _make_api_call(self, operation_name, api_params):
            if call_log:
                logger.info("API Call Logger: Region - {region}, "
                            "Service - {service}, "
                            "Action - {action}, "
                            "API Params - {api_params}".format(region=self.meta.region_name,
                                                               service=self._service_model.service_name,
                                                               action=operation_name, api_params=str(api_params)))
            if any([bool(re.match(regex, operation_name)) for regex in action_regex_to_cache]):
                try:
                    return self._make_cached_api_call(operation_name, api_params)
                except Exception as e:
                    # In case of any errors with caching , normal make api will be called
                    if not supress_warning_message:
                        logger.error("Error encountered : {}. Retrying the same call without cached context.".format(e))
            return super()._make_api_call(operation_name, api_params)

        @cached(cache=cache, key=return_cache_key)
        def _make_cached_api_call(self, operation_name, api_params):
            return super()._make_api_call(operation_name, api_params)

    return patch('botocore.client.BaseClient', new=BotoCache)

