"""Contract test: every client.<method>(...) call in the scripts must exist in the
published FlashArray REST spec, with only parameters that endpoint accepts.

The spec comes from https://github.com/PureStorage-OpenConnect/swagger (the source of
https://code.purestorage.com/swagger/). Set STAAS_API_VERSION to test another version
(default 2.42, the minimum in the README). Needs no array and no credentials; the test
is skipped when the spec cannot be fetched.
"""
import ast
import importlib
import inspect
import os
import pathlib
import urllib.request

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ["staas-reporting.py", "staas-tag_vols.py", "staas_common.py"]
VERSION = os.environ.get("STAAS_API_VERSION", "2.42")
SPEC_URL = (
    "https://raw.githubusercontent.com/PureStorage-OpenConnect/swagger/master/"
    f"definitions/oas2.0/FA{VERSION}.spec.yaml"
)
CACHE = ROOT / ".cache" / f"FA{VERSION}.spec.yaml"
VERBS = ("get", "post", "put", "patch", "delete")
# Python-only keywords the SDK adds to every call; they are not REST parameters.
SDK_KWARGS = {"async_req", "_preload_content", "_request_timeout", "x_request_id", "authorization"}


# Calls the SDK accepts but the raw REST spec does not define for that endpoint. Each is
# a convenience the SDK handles; verify against a real array (pytest -m live) before
# relying on it, and remove the entry when the call is fixed.
KNOWN_SPEC_DEVIATIONS = {
    # /volumes/space filters by `ids` in the spec; `names` is an SDK convenience.
    ("get_volumes_space", "names"),
    # /realms/space is array-local in the spec and takes no context_names.
    ("get_realms_space", "context_names"),
}


# Calls the installed SDK rejects (TypeError at runtime): real bugs in the scripts, tracked
# here as expected failures until fixed. Remove the entry in the same change as the fix.
KNOWN_SDK_BUGS = {
    # py-pure-client FA_2_42..FA_2_58 get_realms_space() takes ids/names only, no context_names.
    ("get_realms_space", "context_names"),
}


@pytest.fixture(scope="session")
def operations():
    """Map SDK method name -> set of accepted parameter names, built from the spec."""
    if not CACHE.exists():
        try:
            with urllib.request.urlopen(SPEC_URL, timeout=30) as resp:
                data = resp.read()
        except OSError as e:
            pytest.skip(f"cannot fetch {SPEC_URL}: {e}")
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_bytes(data)
    spec = yaml.safe_load(CACHE.read_text())
    shared = spec.get("parameters", {})
    prefix = f"/api/{VERSION}/"

    def param_names(params):
        names = set()
        for p in params:
            if "$ref" in p:
                p = shared[p["$ref"].rsplit("/", 1)[-1]]
            names.add(p["name"])
        return names

    ops = {}
    for path, item in spec["paths"].items():
        if not path.startswith(prefix):
            continue
        stem = path[len(prefix):].replace("/", "_").replace("-", "_")
        for verb in VERBS:
            if verb in item:
                ops[f"{verb}_{stem}"] = param_names(item[verb].get("parameters", []))
    return ops


def client_calls():
    """Yield (file, line, method, kwargs) for each `client.<verb>_*(...)` call."""
    for name in SCRIPTS:
        tree = ast.parse((ROOT / name).read_text(), filename=name)
        for node in ast.walk(tree):
            f = getattr(node, "func", None)
            if (
                isinstance(node, ast.Call)
                and isinstance(f, ast.Attribute)
                and isinstance(f.value, ast.Name)
                and f.value.id == "client"
                and f.attr.startswith(tuple(f"{v}_" for v in VERBS))
            ):
                yield name, node.lineno, f.attr, [k.arg for k in node.keywords if k.arg]


CALLS = sorted(set((n, line, m, tuple(k)) for n, line, m, k in client_calls()))


def test_calls_were_found():
    assert CALLS, "AST scan found no client calls; the scan itself is broken"


@pytest.mark.parametrize("file,line,method,kwargs", CALLS, ids=[f"{c[0]}:{c[1]}:{c[2]}" for c in CALLS])
def test_call_matches_spec(operations, file, line, method, kwargs):
    # get_rest_version is an SDK helper (GET /api/api_version), not a versioned endpoint.
    if method == "get_rest_version":
        pytest.skip("SDK helper")
    assert method in operations, f"{method} is not an endpoint in FA {VERSION}"
    unknown = {k for k in set(kwargs) - operations[method] - SDK_KWARGS if (method, k) not in KNOWN_SPEC_DEVIATIONS}
    assert not unknown, f"{file}:{line} {method} passes parameters FA {VERSION} does not define: {sorted(unknown)}"


@pytest.mark.parametrize("file,line,method,kwargs", CALLS, ids=[f"{c[0]}:{c[1]}:{c[2]}" for c in CALLS])
def test_call_matches_sdk_signature(file, line, method, kwargs):
    """The installed py-pure-client must accept exactly these keyword arguments."""
    if method == "get_rest_version":
        pytest.skip("SDK helper")
    module = importlib.import_module(f"pypureclient.flasharray.FA_{VERSION.replace('.', '_')}.client")
    fn = getattr(module.Client, method, None)
    assert fn is not None, f"py-pure-client FA {VERSION} has no {method}"
    params = inspect.signature(fn).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return
    unknown = set(kwargs) - set(params)
    if unknown and all((method, k) in KNOWN_SDK_BUGS for k in unknown):
        pytest.xfail(f"known bug: {method} does not accept {sorted(unknown)} (see KNOWN_SDK_BUGS)")
    assert not unknown, f"{file}:{line} {method} would raise TypeError for {sorted(unknown)}"
