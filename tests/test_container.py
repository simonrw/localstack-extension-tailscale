import os
import logging
import pytest

from testcontainers.localstack import LocalStackContainer

from localstack_extension_tailscale.container import TailscaleContainer
from localstack.logging.setup import setup_logging


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    setup_logging(log_level=logging.DEBUG)


@pytest.fixture(scope="module")
def localstack_container_id():
    container = LocalStackContainer("localstack/localstack")
    env = {"DEBUG": "1", "LS_LOG": "trace"}
    for key, value in env.items():
        container.with_env(key, value)

    if os.path.exists("/var/run/docker.sock"):
        container.with_volume_mapping("/var/run/docker.sock", "/var/run/docker.sock")

    with container as localstack:
        yield localstack.get_wrapped_container().id

        if localstack._container:
            logs = localstack._container.logs().decode()

            print("# LocalStack logs")
            print(logs)


def test_start_container(caplog, localstack_container_id):
    tsc = TailscaleContainer()
    tsc.start(localstack_container_id)
    try:
        tsc.wait(timeout=60)
        tsc.stop()

        # check at least one log line was emitted
        found = False
        for log in caplog.records:
            if "[tailscale]" in log.message:
                found = True
                break

        assert found
    finally:
        tsc.remove()
