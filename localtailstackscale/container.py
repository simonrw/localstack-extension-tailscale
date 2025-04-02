import logging
import os
from pathlib import Path
from typing import Iterable
from localstack import config
from localstack.utils.container_utils.container_client import ContainerConfiguration, VolumeMappings
from localstack.utils.docker_utils import (
    DOCKER_CLIENT,
    get_host_path_for_path_in_docker,
)
from localstack.utils.threads import FuncThread

CONTAINER_NAME = "tailscale/tailscale"
TAILSCALE_STATE_DIR = "/var/lib/tailscale"
LOG = logging.getLogger("localstack.extension.tailscale")

def print_logs(stream: Iterable[bytes]):
    for line in stream:
        LOG.debug("[tailscale] %s", line.decode().strip())



class TailscaleContainer:
    container_id: str | None
    log_printer: FuncThread | None

    def start(self, localstack_container_id: str):
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
        extension_container_path = (
            Path(config.dirs.cache) / "localstack-tailscale" / "state"
        )
        extension_container_path.mkdir(parents=True, exist_ok=True)
        volume = get_host_path_for_path_in_docker(str(extension_container_path))
        container_config = ContainerConfiguration(
            image_name="tailscale/tailscale",
            env_vars=env,
            network=f"container:{localstack_container_id}",
            volumes=VolumeMappings([(volume, TAILSCALE_STATE_DIR)]),
        )
        # TODO: error handling
        self.container_id = DOCKER_CLIENT.create_container_from_config(container_config)
        _ = DOCKER_CLIENT.start_container(self.container_id)
        log_stream = DOCKER_CLIENT.stream_container_logs(self.container_id)

        self.log_printer = FuncThread(
            lambda params: print_logs(params[0]), params=(log_stream,)
        )
        self.log_printer.start()

    def stop(self):
        if self.log_printer:
            self.log_printer.stop()

        LOG.info("shutting down Tailscale sidecar")
        if self.container_id:
            DOCKER_CLIENT.remove_container(self.container_id, force=True)
