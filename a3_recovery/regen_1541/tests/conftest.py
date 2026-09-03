"""Markers the ordered chain relies on."""


def pytest_configure(config):
    # A test that READS THE CHAIN'S OWN OUTPUTS (reports/, the manifest, the log) can
    # only be judged after those outputs exist. The focused step runs every test file
    # but skips these by marker - the test declares its dependency, no runner hand-list
    # decides it - and the full suite after the freeze runs them all.
    config.addinivalue_line("markers", "reads_chain_outputs: reads reports/, the manifest or the ordered log")
