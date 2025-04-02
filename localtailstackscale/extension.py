from collections.abc import Iterable
import logging
import socket
from typing import final

from localstack import config
from localstack.extensions.api import Extension
from localstack.utils.run import FuncThread
from localtailstackscale.container import TailscaleContainer

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger("localstack.extension.tailscale")



@final
class LocalStackTailscale(Extension):
    name: str = "localtailstackscale"
    requirements = []
    log_printer: FuncThread | None

    def __init__(self):
        self.tailscale_container = TailscaleContainer()
        self.container_id: str | None = None
        self.log_printer = None

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

        self.start_sidecar_container()

    def on_platform_shutdown(self):
        self.stop_sidecar_container()

    def start_sidecar_container(self):
        # get the container name
        localstack_container_id = socket.gethostname()
        self.tailscale_container.start(localstack_container_id)

    def stop_sidecar_container(self):
        self.tailscale_container.stop()
