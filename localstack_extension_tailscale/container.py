import logging
import os
from pathlib import Path
from typing import Iterable
from localstack import config
from localstack.utils.sync import wait_until
from localstack.utils.container_utils.container_client import (
    ContainerConfiguration,
    NoSuchContainer,
    VolumeMappings,
)
from localstack.utils.docker_utils import (
    DOCKER_CLIENT,
    get_host_path_for_path_in_docker,
)
from localstack.utils.threads import FuncThread

CONTAINER_NAME = "tailscale/tailscale"
TAILSCALE_STATE_DIR = "/var/lib/tailscale"
LOG = logging.getLogger("localstack.extension.tailscale")
READY_SENTINEL = "Startup complete"


class TailscaleContainer:
    container_id: str | None
    log_printer: FuncThread | None
    log_lines: list[str]
    seen_log_lines: set[str]

    def __init__(self):
        self.container_id = None
        self.log_printer = None
        self.log_lines = []
        self.seen_log_lines = set()

    def start(self, localstack_container_id: str, mount_volume_dir: bool = False):
        # get environment variables to forward
        env: dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith("TS_"):
                LOG.debug("including environment variable '%s'", key)
                env[key] = value

        # ensure the state directory is set if not given
        env.setdefault("TS_STATE_DIR", TAILSCALE_STATE_DIR)

        # start up tailscale container
        volume_mappings = VolumeMappings()
        if mount_volume_dir:
            extension_container_path = (
                Path(config.dirs.cache) / "localstack-tailscale" / "state"
            )
            extension_container_path.mkdir(parents=True, exist_ok=True)
            volume = get_host_path_for_path_in_docker(str(extension_container_path))
            volume_mappings.add((volume, TAILSCALE_STATE_DIR))

        container_config = ContainerConfiguration(
            image_name="tailscale/tailscale",
            env_vars=env,
            network=f"container:{localstack_container_id}",
            volumes=volume_mappings,
        )
        # TODO: error handling
        self.container_id = DOCKER_CLIENT.create_container_from_config(container_config)
        _ = DOCKER_CLIENT.start_container(self.container_id)
        log_stream = DOCKER_CLIENT.stream_container_logs(self.container_id)

        self.log_printer = FuncThread(
            lambda params: self._print_logs(params[0]), params=(log_stream,)
        )
        self.log_printer.start()

    def _container_ready(self) -> bool:
        for line in self.log_lines:
            if READY_SENTINEL in line:
                return True

        return False

    def _check_is_up(self) -> bool:
        if self._container_exited():
            LOG.error(f"Tailscale container '%s' exited unexpectedly. Logs: %s", self.container_id, "; ".join(self.log_lines))
            raise RuntimeError("Tailscale container exited")

        return self._container_ready()

    def _container_exited(self) -> bool:
        try:
           DOCKER_CLIENT.inspect_container(self.container_id)
           return False
        except NoSuchContainer:
           return True

    def wait(self, timeout: int = 30):
        if not wait_until(self._check_is_up, wait=1, max_retries=timeout, strategy="static"):
            raise TimeoutError("Container not ready")

    def stop(self):
        if self.log_printer:
            self.log_printer.stop()

        LOG.info("shutting down Tailscale sidecar")
        self.remove()

        self.container_id = None

    def remove(self) -> None:
        if self.container_id:
            DOCKER_CLIENT.remove_container(self.container_id, force=True)

    def _print_logs(self, stream: Iterable[bytes]):
        for line in stream:
            text = line.decode().strip()
            if text in self.seen_log_lines:
                continue

            LOG.debug("[tailscale] %s", text)
            self.log_lines.append(text)
            self.seen_log_lines.add(text)
