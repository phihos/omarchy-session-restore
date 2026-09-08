"""Load the plugin's engine as an importable module.

`hypr-session` deliberately has no .py extension: it is the user-facing CLI as
well as the engine, and `hypr-session save` reads better than `hypr_session.py
save`. Python's import machinery keys on the extension, so point a loader at
the file directly.
"""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parent.parent / "hypr-session"


def _load():
    loader = importlib.machinery.SourceFileLoader("hypr_session", str(ENGINE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def session():
    return _load()
