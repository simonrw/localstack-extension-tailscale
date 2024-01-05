import os
import logging
from localstack import config

from localstack.extensions.api import Extension, http, aws
from localstack.utils.container_networking import get_endpoint_for_network
from localstack.utils.container_utils.container_client import (
    ContainerConfiguration,
)
from localstack.utils.bootstrap import DOCKER_CLIENT, Container, RunningContainer

LOG = logging.getLogger(__name__)


class MyExtension(Extension):
    name = "localtailstackscale"

    def __init__(self):
        self.running_container: RunningContainer | None = None

    def on_extension_load(self):
        if config.DEBUG:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logging.getLogger("localtailstackscale").setLevel(level)

    def on_platform_ready(self):
        print("MyExtension: localstack is running")

        # start up tailscale container
        container_config = ContainerConfiguration(
            image_name="srwalker101/tsproxy",
            env_vars={
                "TSPROXY_UPSTREAM_URL": f"http://{get_endpoint_for_network()}:4566",
                "TS_PROXY_PORT": "1992",
                "TS_AUTHKEY": os.environ["TS_AUTHKEY"],
            },
        )
        # TODO: error handling
        container_id = DOCKER_CLIENT.create_container_from_config(container_config)
        DOCKER_CLIENT.start_container(container_id)
        self.running_container = RunningContainer(container_id, container_config)
        self.running_container.wait_until_ready()

    def on_platform_shutdown(self):
        if self.running_container:
            self.running_container.shutdown()
