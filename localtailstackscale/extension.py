from collections.abc import Iterable
import logging
import os
import socket
from pathlib import Path
from typing import final

from localstack import config
from localstack.extensions.api import Extension
from localstack.utils.docker_utils import (
    DOCKER_CLIENT,
    get_host_path_for_path_in_docker,
)
from localstack.utils.container_utils.container_client import (
    ContainerConfiguration,
    VolumeMappings,
)
from localstack.utils.run import FuncThread

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger("localstack.extension.tailscale")

TAILSCALE_STATE_DIR = "/var/lib/tailscale"


def print_logs(stream: Iterable[bytes]):
    for line in stream:
        LOG.debug("[tailscale] %s", line.decode().strip())


@final
class LocalStackTailscale(Extension):
    name: str = "localtailstackscale"
    requirements = []
    volume: str
    log_printer: FuncThread | None

    def __init__(self):
        self.container_id: str | None = None
        extension_container_path = (
            Path(config.dirs.cache) / "localstack-tailscale" / "state"
        )
        extension_container_path.mkdir(parents=True, exist_ok=True)
        self.volume = get_host_path_for_path_in_docker(str(extension_container_path))
        self.log_printer = None

    def on_extension_load(self):
        if config.DEBUG:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logging.getLogger("localtailstackscale").setLevel(level)

        LOG.debug("storing tailscale state at '%s'", self.volume)

    def on_platform_ready(self):
        LOG.info("%s: localstack is running", self.name)

        # if we are not running in docker then exit
        if not config.is_in_docker:
            LOG.warning("not running as a docker container")
            return

        self.start_sidecar_container()

    def on_platform_shutdown(self):
        self.stop_sidecar_container()

    def start_sidecar_container(self):
        # get the container name
        localstack_container_id = socket.gethostname()

        # get environment variables to forward
        # TODO: lock this down
        env: dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith("TS_"):
                LOG.debug("including environment variable '%s'", key)
                env[key] = value

        # ensure the state directory is set if given
        env["TS_STATE_DIR"] = TAILSCALE_STATE_DIR

        # start up tailscale container
        container_config = ContainerConfiguration(
            image_name="tailscale/tailscale",
            env_vars=env,
            network=f"container:{localstack_container_id}",
            volumes=VolumeMappings([(self.volume, TAILSCALE_STATE_DIR)]),
        )
        # TODO: error handling
        self.container_id = DOCKER_CLIENT.create_container_from_config(container_config)
        _ = DOCKER_CLIENT.start_container(self.container_id)
        log_stream = DOCKER_CLIENT.stream_container_logs(self.container_id)

        self.log_printer = FuncThread(
            lambda params: print_logs(params[0]), params=(log_stream,)
        )
        self.log_printer.start()

    def stop_sidecar_container(self):
        if self.log_printer:
            self.log_printer.stop()

        LOG.info("%s shutting down", self.name)
        if self.container_id:
            DOCKER_CLIENT.remove_container(self.container_id, force=True)
