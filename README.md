# localstack-extension-tailscale

Connect LocalStack to your tailnet.

This extension starts a Tailscale sidecar container alongside the main LocalStack container. This allows seamless network connectivity over your tailnet to the LocalStack container.


## Configuration

To configure the Tailscale sidecar container, we forward any Tailscale configuration environment variables to the sidecar container on creation. This means you can refer to the [Tailscale docs for their Docker container](https://tailscale.com/kb/1282/docker) for documentation.

If not specified, we mount the Tailscale state directory (`TS_STATE_DIR`) into a sub-path of the LocalStack volume directory, so to persist this state between sessions, ensure `/var/lib/localstack` is mapped to a Docker volume.

## Development

### Install local development version

To install the extension into localstack in developer mode, you will need Python 3.10, and create a virtual environment in the extensions project.

In the newly generated project, simply run

```bash
make install
```

Then, to enable the extension for LocalStack, run

```bash
localstack extensions dev enable .
```

You can then start LocalStack with `EXTENSION_DEV_MODE=1` to load all enabled extensions:

```bash
EXTENSION_DEV_MODE=1 localstack start -e TS_AUTHKEY=$TS_AUTHKEY
```

### Install from GitHub repository

To distribute your extension, simply upload it to your github account. Your extension can then be installed via:

```bash
localstack extensions install "git+https://github.com/simonrw/localtailstackscale/#egg=localtailstackscale"
```
