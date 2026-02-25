# mozzo

A lightweight command-line assistant for acknowledging and managing Nagios Core alerts via its native CGI scripts.

[![Flake8 Lint](https://github.com/sadsfae/mozzo/actions/workflows/flake8.yml/badge.svg)](https://github.com/sadsfae/mozzo/actions/workflows/flake8.yml)
[![PyPI version](https://img.shields.io/pypi/v/mozzo.svg)](https://pypi.org/project/mozzo/)


## Table of Contents

- [About](#about)
- [Installation](#installation)
  - [Option 1: Run from source (Standalone)](#option-1-run-from-source-standalone)
  - [Option 2: Install via pip](#option-2-install-via-pip)
  - [Option 3: Install via Pypi](#install-via-pypi)
- [Configuration](#configuration)
- [Usage](#usage)
  - [View Nagios process status](#view-nagios-process-status)
  - [List unhandled/alerting services](#list-unhandledalerting-services)
  - [Acknowledge a specific service](#acknowledge-a-specific-service)
  - [Acknowledge a host and all its services](#acknowledge-a-host-and-all-its-services)
  - [Set downtime for a specific host](#set-downtime-for-a-specific-host)
  - [Set downtime for a host and all its services](#set-downtime-for-a-host-and-all-its-services)
  - [Set downtime for a specific service](#set-downtime-for-a-specific-service)
  - [Toggle global alerts](#toggle-global-alerts)
  - [Setting Ack or Downtime with a Custom Message](#setting-ack-or-downtime-with-a-custom-message)
- [License](#license)

## About

Mozzo interacts with Nagios Core (4.x) via `cmd.cgi` and `statusjson.cgi` using standard HTTPS requests. It allows you to acknowledge alerts, schedule downtime, and view statuses without needing to install specialized Nagios libraries or scrape HTML.

a _Mozzo_ is Neapolitan for a young helper who does menial tasks on a ship and is quick to acknowledge things.

## Installation

### Option 1: Run from source (Standalone)

You can clone the repository and run the script directly:

```bash
git clone https://github.com/sadsfae/mozzo.git
cd mozzo
chmod +x mozzo.py
./mozzo.py --help
```

### Option 2: Install via pip

Install globally or in a virtual environment to make the `mozzo` command available anywhere:

```bash
git clone https://github.com/sadsfae/mozzo.git
cd mozzo
pip install .
mozzo --help
```

### Option 3: Install via Pypi

```bash
python -m venv mozzo
. !$/bin/activate
pip install mozzo
```

## Configuration

Mozzo requires a configuration file named `config.yml`. It will search for this file in the following order:

1. `~/.config/mozzo/config.yml`
2. `./config.yml` (Current directory)
3. `/etc/mozzo/config.yml`

> [!TIP]
> Copy the example `config.yml` and edit it first.

```bash
mkdir -p ~/.config/mozzo
curl -s -o ~/.config/mozzo/config.yml https://raw.githubusercontent.com/sadsfae/mozzo/refs/heads/main/config.yml
vim ~/.config/mozzo/config.yml
```

Your `config.yml` should have the following structure:

```yaml
nagios_server: https://nagios.example.com
nagios_cgi_path: /nagios/cgi-bin
nagios_username: nagiosadmin
nagios_password: mysecurepassword
default_downtime: 120 # in minutes
verify_ssl: false
date_format: "%m-%d-%Y %H:%M:%S"
```

## Usage

> [!IMPORTANT]
> You can run `mozzo` (if installed) or `./mozzo.py` or `python mozzo.py` (if running from source).

### View Nagios process status

```bash
mozzo --status

```

### List unhandled/alerting services

```bash
mozzo --unhandled

```

### Acknowledge a specific service

```bash
mozzo --ack --host host01.example.com --service "HTTP"

```

### Acknowledge a host and all its services

```bash
mozzo --ack --host host01.example.com --all-services

```

### Set downtime for a specific host

```bash
mozzo --set-downtime --host host01.example.com

```

### Set downtime for a host and all its services

```bash
mozzo --set-downtime --host host01.example.com --all-services

```

### Set downtime for a specific service

```bash
mozzo --set-downtime --host host01.example.com --service "HTTP"

```

### Toggle global alerts

```bash
mozzo --disable-alerts
mozzo --enable-alerts

```

### Setting Ack or Downtime with a Custom Message

```bash
mozzo --ack --host host01.example.com --message "Acknowledged per ticket INC-12345"
mozzo --set-downtime --host host01.example.com --all-services -m "Patching window"
```

## License

This project is licensed under the **GPLv3** License - see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details. Author: Will Foster (wfoster@pm.me).
