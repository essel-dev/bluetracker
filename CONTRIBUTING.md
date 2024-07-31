# Contributing
## Local Development
### Install
#### Project code
```sh
cd && git clone # path-to-this-repository.git
cd # path-to-downloaded-repository
```

#### Python
Verify if Python is installed.
```sh
python --version
```

##### pyenv
To install multiple Python versions, use [pyenv](https://github.com/pyenv/pyenv).

To activate `pyenv`:
```sh
pyenv local 3.11 3.12
```

#### Mosquitto
```sh
sudo apt install -y mosquitto mosquitto-clients
```

#### Virtual environment
```sh
python -m venv .env
source .env/bin/activate
```

#### pip and setuptools
```sh
python -m pip install --upgrade pip setuptools
```

#### Dependencies
```sh
pip install -e .[dev]
```

#### Pre-commit
```sh
pre-commit install
pre-commit autoupdate
pre-commit run --all-files
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

To run all:
```sh
tox
```

To run a specific environment:
```sh
tox -e py312
```

To generate documentation:
```sh
tox -e docs
```
The HTML pages are in docs/build/html.
