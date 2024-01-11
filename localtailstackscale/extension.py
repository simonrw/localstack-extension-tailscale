import os
import logging
from localstack import config

from localstack.extensions.api import Extension, http, aws
from localstack.utils.container_networking import get_endpoint_for_network
from localstack.utils.container_utils.container_client import (
    ContainerConfiguration,
)
from localstack.utils.bootstrap import DOCKER_CLIENT, Container, RunningContainer

LOG = logging.getLogger("localstacktailscale.tsproxy")

AUTHKEY_NAME = "TS_AUTHKEY"


class LocalStackTailscale(Extension):
    name = "localtailstackscale"

    def __init__(self):
        self.running_container: RunningContainer | None = None

    def on_extension_load(self):
        if config.DEBUG:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logging.getLogger("localtailstackscale").setLevel(level)

        # validation
        if AUTHKEY_NAME not in os.environ:
            LOG.warning(
                "%s not found in environment. Check sidecar container logs for authorization instructions",
                AUTHKEY_NAME,
            )

    def on_platform_ready(self):
        LOG.info("%s: localstack is running", self.name)

        # start up tailscale container
        container_config = ContainerConfiguration(
            # TODO: public image
            image_name="srwalker101/tsproxy",
            env_vars={
                "TSPROXY_UPSTREAM_URL": f"http://{get_endpoint_for_network()}:4566",
                "TSPROXY_PORT": os.getenv("TSPROXY_PORT", "4566"),
                "TSPROXY_HOSTNAME": os.getenv("TSPROXY_HOSTNAME", ""),
                "TS_AUTHKEY": os.getenv("TS_AUTHKEY", ""),
            },
        )
        # TODO: error handling
        container_id = DOCKER_CLIENT.create_container_from_config(container_config)
        DOCKER_CLIENT.start_container(container_id)
        self.running_container = RunningContainer(container_id, container_config)
        self.running_container.wait_until_ready()

    def on_platform_shutdown(self):
        LOG.info("%s shutting down", self.name)
        if self.running_container:
            self.running_container.shutdown()
