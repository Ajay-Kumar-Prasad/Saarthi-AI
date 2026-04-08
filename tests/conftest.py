import os
import sys
import asyncio
import inspect


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: run test in asyncio loop")


def pytest_pyfunc_call(pyfuncitem):
    testfunction = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunction):
        asyncio.run(testfunction(**pyfuncitem.funcargs))
        return True
    return None
