# Contributing

## Local Development

### Install

#### Project code

```sh
cd && git clone # path-to-this-repository.git
cd # path-to-downloaded-repository
```

#### uv

Install [uv](https://docs.astral.sh/uv/).

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Mosquitto

```sh
sudo apt install -y mosquitto mosquitto-clients
```

#### Pre-commit

```sh
uv tool install pre-commit --force
uv run pre-commit autoupdate
uv run pre-commit run --all-files
```

### Develop

#### Mosquitto

Start server

```sh
sudo mosquitto -v
```

Listen to messages

```sh
mosquitto_sub -v -t '#' -h 127.0.0.1
```

Publish a message

```sh
mosquitto_pub -t 'led/strip/set' -h 127.0.0.1 -m 0
```

Stop Mosquitto server:

```sh
sudo systemctl stop mosquitto
```

#### Tox

See [tox](pyproject.toml) for all test environments.

Tox all:

```sh
uvx tox
```

Tox a specific environment:

```sh
uvx tox -e py314
```

To generate documentation:

```sh
tox -e docs
```

The HTML pages are in docs/build/html.
