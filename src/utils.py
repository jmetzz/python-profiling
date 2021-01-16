import logging
import re
from functools import wraps
from time import perf_counter

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

logger = logging.getLogger(__name__)


def audited(wrapped_func):
    """Decorate a function to time it and log it out (also captures args/kwargs)
    """

    @wraps(wrapped_func)
    def wrap(*args, **kw):
        logger.debug(f"[START] func: %s", wrapped_func.__name__, extra={"func_args": args, "func_kwargs": kw})

        start = perf_counter()
        result = f(*args, **kw)
        end = perf_counter()

        logger.debug(
            "END: func: %s",
            wrapped_func.__name__,
            extra={"func_args": args, "func_kwargs": kw, "time": f"{end - start:2.4f}"},
        )
        return result

    return wrap


def timed(wrapped_func):
    """Decorate a function to time it and log it out
    """

    @wraps(wrapped_func)
    def wrap(*args, **kw):
        start = perf_counter()
        result = f(*args, **kw)
        end = perf_counter()
        logger.debug("func: %s took: %2.4f sec", wrapped_func.__name__, end - start)
        return result

    return wrap


def underscore_to_camel(name: str) -> str:
    """
    Convert a name from underscore lower case convention to camel case convention.
    Args:
        name (str): name in underscore lowercase convention.
    Returns:
        Name in camel case convention.
    """
    under_pat = re.compile(r"_([a-z])")
    return under_pat.sub(lambda x: x.group(1).upper(), name)
