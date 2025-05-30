import logging
import pytest

from testcontainers.localstack import LocalStackContainer

from localstack_extension_tailscale.container import TailscaleContainer


@pytest.fixture(scope="module")
def localstack_container_id():
    with LocalStackContainer("localstack/localstack") as localstack:
        yield localstack.get_wrapped_container().id


def test_start_container(caplog, localstack_container_id):
    tsc = TailscaleContainer()
    tsc.start(localstack_container_id)
    tsc.wait(timeout=30)
    tsc.stop()

    # check at least one log line was emitted
    found = False
    for log in caplog.records:
        if "[tailscale]" in log.message:
            found = True
            break

    assert found
