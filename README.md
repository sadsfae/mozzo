# mozzo

A lightweight CLI for acknowledging and managing [Nagios Core](https://www.nagios.org/projects/nagios-core/) alerts and reporting via its native CGI scripts.

[![Flake8 Lint](https://github.com/sadsfae/mozzo/actions/workflows/flake8.yml/badge.svg)](https://github.com/sadsfae/mozzo/actions/workflows/flake8.yml)
[![PyPI version](https://badge.fury.io/py/mozzo.svg)](https://badge.fury.io/py/mozzo)

## About

Mozzo interacts with Nagios Core (4.x) via `cmd.cgi` and `statusjson.cgi` using standard HTTPS requests. It allows you to acknowledge alerts, schedule downtime, generate service/host uptime reporting and view statuses without needing to install specialized Nagios libraries or scrape HTML.

> [!NOTE]
> This is compatible with Nagios Core 4.4.x and not been tested with 4.5.x

## Table of Contents

- [Installation](#installation)
  - [Option 1: Run from Source (Standalone)](#option-1-run-from-source-standalone)
  - [Option 2: Install via pip](#option-2-install-via-pip)
  - [Option 3: Install via Pypi](#install-via-pypi)
- [Configuration](#configuration)
- [Usage](#usage)
  - [View Nagios Process Status](#view-nagios-process-status)
  - [List Unhandled or Alerting services](#list-unhandledalerting-services)
  - [List Service Issue](#list-service-issues)
  - [Acknowledge a Specific Service](#acknowledge-a-specific-service)
  - [Acknowledge a Host and all its Services](#acknowledge-a-host-and-all-its-services)
  - [Set Downtime for a Specific Host](#set-downtime-for-a-specific-host)
  - [Set Downtime for a Host and all its Services](#set-downtime-for-a-host-and-all-its-services)
  - [Set Downtime for a Specific Service](#set-downtime-for-a-specific-service)
  - [Disable Alerting for a Specific Service](#disable-alerting-for-a-specific-service)
  - [Disable Alerting for all Services on a Host](#disable-alerting-for-all-services-on-a-host)
  - [Enable Alerting for all Services on a Host](#enable-alerting-for-all-services-on-a-host)
  - [Enable Alerting for a Specific Service](#enable-alerting-for-a-specific-service)
  - [Toggle Global Alerts](#toggle-global-alerts)
  - [Setting Ack or Downtime with a Custom Message](#setting-ack-or-downtime-with-a-custom-message)
  - [Acknowledging all Unhandled Issues](#acknowledging-all-unhandled-issues)
- [Service Reporting and Uptime](#service-reporting-and-uptime)
  - [Listing all Services by Host](#listing-all-services-by-host)
  - [Listing Service Details by Host](#listing-service-details-by-host)
  - [Listing Service Details on All Hosts](#listing-service-details-on-all-hosts)
  - [Listing Service Details with Output](#listing-service-details-with-output)
  - [Listing Service Details with Filter](#listing-service-details-with-filter)
  - [Uptime Reporting](#uptime-reporting)
    - [Report Uptime by Service](#report-uptime-by-service)
    - [Report Uptime by Host](#report-uptime-by-host)
  - [Exporting Report Data](#exporting-report-data)
- [Contributing](#contributing)

## Installation

### Option 1: Run from Source (Standalone)

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

Your `config.yml` needs the following structure:

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

### View Nagios Process Status

```bash
mozzo --status
```

### List Unhandled or Alerting services

```bash
mozzo --unhandled
```

### List Service Issues

```bash
mozzo --service-issues [ --host host.example.com ]
```

### Acknowledge a Specific Service

```bash
mozzo --ack --host host01.example.com --service "HTTP"
```

### Acknowledge a Host and all its Services

```bash
mozzo --ack --host host01.example.com --all-services
```

### Set Downtime for a Specific Host

```bash
mozzo --set-downtime --host host01.example.com
```

### Set Downtime for a Host and all its Services

```bash
mozzo --set-downtime --host host01.example.com --all-services
```

### Set Downtime for a Specific Service

```bash
mozzo --set-downtime --host host01.example.com --service "HTTP"
```

### Disable Alerting for a Specific Service

```bash
mozzo --disable-alerts --host host01.example.com --service "HTTP"
```

### Disable Alerting for all Services on a Host

```bash
mozzo --disable-alerts --host host01.example.com --all-services
```

### Enable Alerting for all Services on a Host

```bash
mozzo --enable-alerts --host host01.example.com --all-services
```

### Enable Alerting for a Specific Service

```bash
mozzo --enable-alerts --host host01.example.com --service "HTTP"
```

### Toggle Global Alerts

```bash
mozzo --disable-alerts
mozzo --enable-alerts
```

### Setting Ack or Downtime with a Custom Message

```bash
mozzo --ack --host host01.example.com --message "Acknowledged per ticket INC-12345"
mozzo --set-downtime --host host01.example.com --all-services -m "Patching window"
```

### Acknowledging all Unhandled Issues
* This bash one-liner can ack all unhandled issues in one swoop.

```bash
mozzo --unhandled | grep -E -i "critical|warning" | while read -r level host arrow service; do mozzo --ack --host "$host" --service "$service"; done
```

## Service Reporting and Uptime
* We also support reporting for uptime per host and per service based on Nagios `archivejson.cgi`

### Listing all Services by Host

```bash
mozzo --status --host host01.example.com
```

### Listing Service Details by Host

```bash
mozzo --status --host host01.example.com --service "DNS"
```

### Listing Service Details on All Hosts

```bash
mozzo --status --service "DNS"
```

### Listing Service Details with Output

To show DNS results for all hosts that have the service:

```bash
mozzo --status --service "DNS" --show-output
```

To show DNS results for a specific host that has the service:

```bash
mozzo --status --host host01.example.com --service "DNS" --show-output
```

### Listing Service Details with Filter

1 = PENDING; 2 = OK; 4 = WARNING; 8 = UNKNOWN; 16 = CRITICAL
To show DNS results for all hosts that have the service in CRITICAL state:

```bash
mozzo --status --service "DNS" --show-output --output-filter 16
```

To show DNS results for a specific host that has the service in CRITICAL state:

```bash
mozzo --status --host host01.example.com --service "DNS" --show-output --output-filter 16
```

You can combine `--show-output` with `--output-filter`

### Uptime Reporting

> [!NOTE]
> Default uptime reporting is 365 days if `--days` is not specified.

#### Report Uptime by Service

```bash
mozzo --status --host host01.example.com --service "DNS" --uptime --days 180

```

#### Report Uptime by Host

```bash
mozzo --status --host host01.example.com --uptime
```

### Exporting Report Data
* You can export in both JSON and CSV

```bash
mozzo --status --host host01.example.com --service "DNS" --uptime --format json > /tmp/host01_dns.json

```

```bash
mozzo --status --host host01.example.com --service "HTTP" --uptime --format csv > /tmp/host01_http_json
```

## Contributing

- Please open pull requests against the [development](https://github.com/sadsfae/mozzo/tree/development) branch.
- I maintain an Ansible playbook to [install Nagios Core here](https://github.com/sadsfae/ansible-nagios) and clients.
