import logging
import os
import socket
import threading

from localstack import config
from localstack.extensions.api import Extension
from localstack.utils.docker_utils import DOCKER_CLIENT
from localstack.utils.container_utils.container_client import (
    CancellableStream,
    ContainerConfiguration,
)

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger("localstack.extension.tailscale")


def print_logs(stream: CancellableStream):
    for line in stream:
        LOG.debug("[tailscale] %s", line.decode().strip())


class LocalStackTailscale(Extension):
    name: str = "localtailstackscale"

    def __init__(self):
        self.container_id: str | None = None

    def on_extension_load(self):
        if config.DEBUG:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logging.getLogger("localtailstackscale").setLevel(level)

    def on_platform_ready(self):
        LOG.info("%s: localstack is running", self.name)

        # if we are not running in docker then exit
        if not config.is_in_docker:
            LOG.warning("not running as a docker container")
            return

        # get the container name
        localstack_container_id = socket.gethostname()

        # get environment variables to forward
        # TODO: lock this down
        env: dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith("TS_"):
                env[key] = value

        # start up tailscale container
        container_config = ContainerConfiguration(
            image_name="tailscale/tailscale",
            env_vars=env,
            network=f"container:{localstack_container_id}",
        )
        # TODO: error handling
        self.container_id = DOCKER_CLIENT.create_container_from_config(container_config)
        _ = DOCKER_CLIENT.start_container(self.container_id)
        log_stream = DOCKER_CLIENT.stream_container_logs(self.container_id)
        self.log_printer = threading.Thread(
            target=print_logs, args=(log_stream,), daemon=True
        )
        self.log_printer.start()

    def on_platform_shutdown(self):
        LOG.info("%s shutting down", self.name)
        if self.container_id:
            DOCKER_CLIENT.remove_container(self.container_id, force=True)
