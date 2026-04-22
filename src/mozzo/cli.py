# -*- coding: utf-8 -*-
import argparse
import csv
import datetime
import json
import os
import sys

import requests
import urllib3
import yaml

# Force UTF-8 output to prevent emoji Mojibake (e.g. â instead of ❌)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _get_version():
    """Reads the version from __init__.py without importing the package."""
    base_path = os.path.dirname(__file__)
    init_path = os.path.join(base_path, "__init__.py")
    if os.path.exists(init_path):
        with open(init_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    return "UNKNOWN"


__version__ = _get_version()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TimeoutHTTPAdapter(requests.adapters.HTTPAdapter):
    """HTTPAdapter that sets a default timeout for all requests."""

    def __init__(self, timeout=60, *args, **kwargs):
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        # Use the instance timeout if no timeout is explicitly provided
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


class MozzoNagiosClient:
    # Status and filter maps used throughout the class
    SERVICE_STATUS_MAP = {
        1: "⏳ PENDING",
        2: "✅ OK",
        4: "⚠️  WARNING",
        8: "❓ UNKNOWN",
        16: "❌ CRITICAL",
    }

    HOST_STATUS_MAP = {
        0: "⏳ PENDING",
        2: "✅ UP",
        4: "❌ DOWN",
        8: "❓ UNREACHABLE"
    }

    FILTER_MAP = {
        "PENDING": 1,
        "OK": 2,
        "WARNING": 4,
        "UNKNOWN": 8,
        "CRITICAL": 16,
    }

    def __init__(self, config_path=None, message=None, days=None):
        config_file = self._find_config(config_path)
        if not config_file:
            print(
                "❌ Could not find config.yml.\n"
                "Please ensure config.yml exists in the current directory."
            )
            sys.exit(1)
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading {config_file}: {e}")
            sys.exit(1)

        self.server = self.config.get("nagios_server", "").rstrip("/")
        self.cgi_path = self.config.get("nagios_cgi_path", "/nagios/cgi-bin").strip("/")
        self.auth = (
            self.config.get("nagios_username"),
            self.config.get("nagios_password"),
        )
        self.downtime_mins = self.config.get("default_downtime", 120)
        self.report_days = self.config.get("default_reporting_days", 365)
        self.verify_ssl = self.config.get("verify_ssl", True)
        self.date_format = self.config.get("date_format", "%m-%d-%Y %H:%M:%S")
        self.cmd_url = f"{self.server}/{self.cgi_path}/cmd.cgi"
        self.json_url = f"{self.server}/{self.cgi_path}/statusjson.cgi"
        self.archive_url = f"{self.server}/{self.cgi_path}/archivejson.cgi"

        # Set the custom message or fallback to default
        self.message = message if message else "Action issued by Mozzo CLI"
        self.days = days

        # Configure session with timeout adapter for all HTTP/HTTPS requests
        self.session = requests.Session()
        adapter = TimeoutHTTPAdapter(timeout=60)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _find_config(self, provided_path):
        if provided_path and os.path.exists(provided_path):
            return provided_path

        search_paths = [
            os.path.expanduser("~/.config/mozzo/config.yml"),
            "/etc/mozzo/config.yml",
            "config.yml",
        ]

        for path in search_paths:
            if os.path.exists(path):
                return path
        return None

    def _normalize_timestamp(self, timestamp):
        """Convert millisecond timestamps to seconds if needed.

        Nagios CGI sometimes returns timestamps in milliseconds (>9999999999).
        This helper normalizes them to standard Unix seconds.
        """
        if timestamp > 9999999999:
            return timestamp / 1000.0
        return timestamp

    def _format_duration(self, last_change_ts):
        """Format a timestamp delta into human-readable duration.

        Args:
            last_change_ts: Unix timestamp of the last state change

        Returns:
            Formatted string like "5d 3h 42m 15s" or "N/A" if invalid
        """
        if last_change_ts <= 0:
            return "N/A"

        last_change_ts = self._normalize_timestamp(last_change_ts)
        now = datetime.datetime.now().timestamp()
        delta = datetime.timedelta(seconds=int(now - last_change_ts))
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{delta.days}d {hours}h {minutes}m {seconds}s"

    def _post_cmd(self, payload):
        payload["btnSubmit"] = "Commit"
        payload["com_author"] = self.auth[0]
        payload["com_data"] = self.message

        try:
            response = self.session.post(
                self.cmd_url, data=payload, auth=self.auth, verify=self.verify_ssl
            )
            response.raise_for_status()
            if "successfully submitted" in response.text:
                print("✅ Command successfully submitted to Nagios.")
            else:
                print(
                    "⚠️ Command sent, but success message not found. "
                    "Check permissions."
                )
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP Error submitting command: {e}")

    def _get_json(self, params):
        try:
            response = self.session.get(
                self.json_url, params=params, auth=self.auth, verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP Error fetching data: {e}")
            sys.exit(1)

    def _get_downtime_windows(self):
        now = datetime.datetime.now()
        if self.days is not None:
            end = now + datetime.timedelta(days=self.days)
        else:
            end = now + datetime.timedelta(minutes=self.downtime_mins)
        return now.strftime(self.date_format), end.strftime(self.date_format)

    def _get_status_text(self, status_code, is_host=False):
        """Get human-readable status text for a status code.

        Args:
            status_code: Numeric status code from Nagios
            is_host: If True, use HOST_STATUS_MAP, else SERVICE_STATUS_MAP

        Returns:
            Formatted status string with emoji, or fallback format
        """
        if is_host:
            return self.HOST_STATUS_MAP.get(status_code, f"CODE_{status_code}")
        return self.SERVICE_STATUS_MAP.get(status_code, f"[{status_code}]")

    def _format_downtime_duration(self):
        """Format downtime duration string based on config.

        Returns:
            String like "5 days" or "120m" based on self.days setting
        """
        return f"{self.days} days" if self.days is not None else f"{self.downtime_mins}m"

    def _print_toggle_action(self, enable, target_description):
        """Print enable/disable notification message.

        Args:
            enable: True for enabling, False for disabling
            target_description: Description of what's being toggled
        """
        action = "Enabling" if enable else "Disabling"
        print(f"{action} notifications for {target_description}...")

    def _matches_host(self, candidate_host, target_host):
        """Check if candidate hostname matches target (FQDN or shortname).

        Args:
            candidate_host: Hostname to check
            target_host: Target hostname to match against

        Returns:
            True if hosts match (exact or shortname match)
        """
        candidate_short = candidate_host.split(".")[0].lower()
        candidate_lower = candidate_host.lower()
        target_short = target_host.split(".")[0].lower()
        target_lower = target_host.lower()

        return candidate_lower == target_lower or candidate_short == target_short

    def _build_ack_payload(self, host, service=None):
        """Build acknowledgement command payload.

        Args:
            host: Target host
            service: Optional service name (None for host ack)

        Returns:
            Dictionary payload for cmd.cgi
        """
        payload = {
            "cmd_typ": 34 if service else 33,
            "cmd_mod": 2,
            "host": host,
            "sticky_ack": "on",
            "send_notification": "off",
            "persistent": "off",
        }
        if service:
            payload["service"] = service
        return payload

    def _build_downtime_payload(self, host, service=None, all_services=False):
        """Build downtime command payload.

        Args:
            host: Target host
            service: Optional service name
            all_services: If True, schedules downtime for host + all services

        Returns:
            Dictionary payload for cmd.cgi
        """
        start, end = self._get_downtime_windows()

        if all_services:
            cmd_typ = 86
            service_val = "all"
        elif service:
            cmd_typ = 56
            service_val = service
        else:
            cmd_typ = 55
            service_val = None

        payload = {
            "cmd_typ": cmd_typ,
            "cmd_mod": 2,
            "host": host,
            "fixed": 1,
            "start_time": start,
            "end_time": end,
        }

        if service_val:
            payload["service"] = service_val

        return payload

    def _build_service_result(self, host, service_name, details):
        """Build standardized service result dictionary.

        Args:
            host: Host name
            service_name: Service description
            details: Service details from API

        Returns:
            Dictionary with service result data
        """
        status_code = details.get("status")
        status_text = self._get_status_text(status_code, is_host=False)

        return {
            "host": host,
            "service": service_name,
            "status_code": status_code,
            "status": status_text,
            "plugin_output": details.get("plugin_output", ""),
            "long_plugin_output": details.get("long_plugin_output", ""),
        }

    def _fetch_availability_data(self, host, service=None, days=365):
        """Fetch availability data from archive API.

        Args:
            host: Target host
            service: Optional service name (None for host availability)
            days: Number of days to query

        Returns:
            Dictionary with availability percentages, or None on error
        """
        now_dt = datetime.datetime.now()
        start_dt = now_dt - datetime.timedelta(days=days)

        arch_params = {
            "query": "availability",
            "availabilityobjecttype": "services" if service else "hosts",
            "hostname": host,
            "starttime": int(start_dt.timestamp()),
            "endtime": int(now_dt.timestamp()),
            "assumeinitialstate": "true",
            "assumestateretention": "true",
            "assumestatesduringnagiosdowntime": "true",
        }

        if service:
            arch_params["servicedescription"] = service

        try:
            arch_resp = self.session.get(
                self.archive_url,
                params=arch_params,
                auth=self.auth,
                verify=self.verify_ssl
            )

            if arch_resp.status_code != 200:
                return None

            arch_data = arch_resp.json()
            avail_key = "service" if service else "host"
            avail = arch_data.get("data", {}).get(avail_key, {})

            if not avail:
                return None

            if service:
                if avail.get("description") != service:
                    return {"_debug_raw_dump": arch_data}

                t_ok = avail.get("time_ok", 0)
                t_warn = avail.get("time_warning", 0)
                t_unk = avail.get("time_unknown", 0)
                t_crit = avail.get("time_critical", 0)
                t_nodata = avail.get("time_indeterminate_nodata", 0)
                t_notrunning = avail.get("time_indeterminate_notrunning", 0)
                total_time = t_ok + t_warn + t_unk + t_crit + t_nodata + t_notrunning

                if total_time > 0:
                    return {
                        "percent_ok": (t_ok / total_time) * 100,
                        "percent_warning": (t_warn / total_time) * 100,
                        "percent_unknown": (t_unk / total_time) * 100,
                        "percent_critical": (t_crit / total_time) * 100,
                    }
            else:
                if not (avail.get("name") == host or avail.get("host_name") == host):
                    return None

                t_up = avail.get("time_up", 0)
                t_down = avail.get("time_down", 0)
                t_unreach = avail.get("time_unreachable", 0)
                t_nodata = avail.get("time_indeterminate_nodata", 0)
                t_notrunning = avail.get("time_indeterminate_notrunning", 0)
                total_time = t_up + t_down + t_unreach + t_nodata + t_notrunning

                if total_time > 0:
                    return {
                        "percent_up": (t_up / total_time) * 100,
                        "percent_down": (t_down / total_time) * 100,
                        "percent_unreachable": (t_unreach / total_time) * 100,
                    }

            return None

        except requests.exceptions.RequestException:
            return None

    def _print_uptime_report(self, report_data, output_format, is_host=False):
        """Print uptime/availability report in requested format.

        Args:
            report_data: Dictionary with report information
            output_format: One of "json", "csv", "text"
            is_host: True for host reports, False for service reports
        """
        if output_format == "json":
            print(json.dumps(report_data, indent=2))
        elif output_format == "csv":
            report_data.pop("_debug_raw_dump", None)
            writer = csv.DictWriter(sys.stdout, fieldnames=report_data.keys())
            writer.writeheader()
            writer.writerow(report_data)
        else:
            days = report_data.get("availability_days", 365)

            if is_host:
                print(f"\n--- Host Status & Uptime: '{report_data['host']}' ---")
                print(f"Status        : {report_data['status']}")
                print(f"State Duration: {report_data['duration']}")
                print(f"Output        : {report_data['output']}")
                print(f"\n--- {days}-Day Availability Report ---")

                if report_data.get("percent_up") is not None:
                    print(f"{'State':<12} | {'% Total Time':<15}")
                    print("-" * 32)
                    print(f"{'UP':<12} | {report_data['percent_up']:.3f}%")
                    print(f"{'DOWN':<12} | {report_data['percent_down']:.3f}%")
                    print(
                        f"{'UNREACHABLE':<12} | "
                        f"{report_data['percent_unreachable']:.3f}%"
                    )
            else:
                host = report_data.get("host")
                service = report_data.get("service")
                print(f"\n--- Status & Uptime: '{service}' on '{host}' ---")
                print(f"Status        : {report_data['status']}")
                print(f"State Duration: {report_data['duration']}")
                print(f"Output        : {report_data['output']}")
                print(f"\n--- {days}-Day Availability Report ---")

                if report_data.get("percent_ok") is not None:
                    print(f"{'State':<10} | {'% Total Time':<15}")
                    print("-" * 30)
                    print(f"{'OK':<10} | {report_data['percent_ok']:.3f}%")
                    print(f"{'WARNING':<10} | {report_data['percent_warning']:.3f}%")
                    print(f"{'UNKNOWN':<10} | {report_data['percent_unknown']:.3f}%")
                    print(f"{'CRITICAL':<10} | {report_data['percent_critical']:.3f}%")

    def ack_service(self, host, service):
        print(f"Acknowledging service '{service}' on host '{host}'...")
        payload = self._build_ack_payload(host, service=service)
        self._post_cmd(payload)

    def ack_host(self, host):
        print(f"Acknowledging host '{host}'...")
        payload = self._build_ack_payload(host)
        self._post_cmd(payload)

    def ack_all_services(self, host):
        print(f"Fetching all services for '{host}' to acknowledge...")
        services = (
            self._get_json({"query": "servicelist", "hostname": host})
            .get("data", {})
            .get("servicelist", {})
            .get(host, {})
        )
        if not services:
            print(f"No services found for host '{host}'.")
            return
        self.ack_host(host)
        for svc in services.keys():
            self.ack_service(host, svc)

    def set_downtime_service(self, host, service):
        duration_str = self._format_downtime_duration()
        print(
            f"Setting {duration_str} downtime for service "
            f"'{service}' on '{host}'..."
        )
        payload = self._build_downtime_payload(host, service=service)
        self._post_cmd(payload)

    def set_downtime_host(self, host):
        duration_str = self._format_downtime_duration()
        print(f"Setting {duration_str} downtime for host '{host}'...")
        payload = self._build_downtime_payload(host)
        self._post_cmd(payload)

    def set_downtime_all(self, host):
        duration_str = self._format_downtime_duration()
        print(
            f"Setting {duration_str} downtime for host '{host}' "
            "AND all its services..."
        )
        payload = self._build_downtime_payload(host, all_services=True)
        self._post_cmd(payload)

    def toggle_alerts(self, enable=True, host=None, service=None, all_services=False):
        if host:
            if all_services:
                cmd_typ = 28 if enable else 29
                self._print_toggle_action(enable, f"all services on '{host}'")
                self._post_cmd({"cmd_typ": cmd_typ, "cmd_mod": 2, "host": host})
            elif service:
                cmd_typ = 22 if enable else 23
                self._print_toggle_action(enable, f"'{service}' on '{host}'")
                self._post_cmd(
                    {
                        "cmd_typ": cmd_typ,
                        "cmd_mod": 2,
                        "host": host,
                        "service": service,
                    }
                )
            else:
                cmd_typ = 24 if enable else 25
                self._print_toggle_action(enable, f"host '{host}'")
                self._post_cmd({"cmd_typ": cmd_typ, "cmd_mod": 2, "host": host})
        else:
            self._print_toggle_action(enable, "global notifications")
            self._post_cmd({"cmd_typ": 12 if enable else 11, "cmd_mod": 2})

    def show_unhandled(self):
        print("\n--- Unhandled Service Alerts ---")

        # 1. Server-Side Filtering: Ask Nagios ONLY for non-OK services.
        query_str = (
            "query=servicelist&details=true&" "servicestatus=warning+critical+unknown"
        )
        services = self._get_json(query_str).get("data", {}).get("servicelist", {})

        if not services:
            print("🎉 No unhandled service alerts found!")
            return

        issue_states = {4: "WARNING", 8: "UNKNOWN", 16: "CRITICAL"}

        # 2. Pre-filter: identify hosts that actually need host-level checks
        hosts_needing_check = set()
        for host, svc_dict in services.items():
            for svc_name, details in svc_dict.items():
                status_code = details.get("status")

                if status_code not in issue_states.keys():
                    continue

                svc_ack = details.get(
                    "problem_has_been_acknowledged"
                ) or details.get("has_been_acknowledged", False)

                if (
                    not details.get("notifications_enabled", True)
                    or svc_ack
                    or details.get("scheduled_downtime_depth", 0) > 0
                ):
                    continue

                hosts_needing_check.add(host)
                break

        # 3. Lazy Loading: Fetch host details ONLY for hosts with unhandled services
        hosts = {}
        for host in hosts_needing_check:
            host_data = (
                self._get_json({"query": "host", "hostname": host})
                .get("data", {})
                .get("host", {})
            )
            hosts[host] = host_data

        found = False

        for host, svc_dict in services.items():
            # Skip hosts where all services are already handled at service level
            if host not in hosts_needing_check:
                continue

            host_details = hosts.get(host, {})
            host_ack = host_details.get(
                "problem_has_been_acknowledged"
            ) or host_details.get("has_been_acknowledged", False)

            if (
                not host_details.get("notifications_enabled", True)
                or host_ack
                or host_details.get("scheduled_downtime_depth", 0) > 0
            ):
                continue

            for svc_name, details in svc_dict.items():
                status_code = details.get("status")

                if status_code in issue_states:
                    svc_ack = details.get(
                        "problem_has_been_acknowledged"
                    ) or details.get("has_been_acknowledged", False)

                    if (
                        not details.get("notifications_enabled", True)
                        or svc_ack
                        or details.get("scheduled_downtime_depth", 0) > 0
                    ):
                        continue

                    found = True
                    status_text = issue_states[status_code]
                    print(
                        f"[{status_text}] {host} -> {svc_name}\n"
                        f"    Output: {details.get('plugin_output')}"
                    )

        if not found:
            print("🎉 No unhandled service alerts found!")

    def show_service_issues(self, host=None):
        issue_states = {4: "⚠️  WARNING", 8: "❓ UNKNOWN", 16: "❌ CRITICAL"}
        print("\n--- List Service Issues ---")

        params = {"query": "servicelist", "details": "false"}

        if host:
            params["hostname"] = host

        services = self._get_json(params).get("data", {}).get("servicelist", {})

        found = False
        for current_host, svc_dict in services.items():
            host_has_issues = False
            for svc_name, svc_status in svc_dict.items():
                if svc_status in issue_states:
                    host_has_issues = True
                    found = True

            if host_has_issues:
                print(f"{current_host}:")
                for svc_name, svc_status in svc_dict.items():
                    if svc_status in issue_states:
                        print(
                            f"    {issue_states[svc_status]} "
                            f"for service: {svc_name}"
                        )

        if not found:
            print("🎉 No service issues found!")

    def _print_service_results(
        self, results, output_format, show_output, header_text, secondary_key
    ):
        """Helper method to format and print service results consistently."""
        if output_format == "json":
            print(json.dumps(results, indent=2))
        elif output_format == "csv":
            writer = csv.DictWriter(
                sys.stdout,
                fieldnames=["host", "service", "status_code", "status"],
            )
            writer.writeheader()
            writer.writerows(
                [
                    {k: r[k] for k in ["host", "service", "status_code", "status"]}
                    for r in results
                ]
            )
        else:
            print(f"\n--- {header_text} ---")
            for r in results:
                extended_out = (
                    f"\n{'-' * 70}\n{r.get('plugin_output', '')}\n"
                    f"{r.get('long_plugin_output', '')}\n"
                    if show_output
                    else ""
                )
                print(
                    f"{'-' * 70}\n{r['status']:<12} | "
                    f"{r[secondary_key]}{extended_out}".strip()
                )
            print("-" * 70)

    def show_host_services(
        self,
        host,
        service=None,
        show_output=False,
        output_filter=None,
        output_format="text",
    ):
        """Displays services for a specific host, optionally filtered."""
        params = {
            "query": "servicelist",
            "hostname": host,
            "details": "true",
        }
        response = self._get_json(params)
        services = response.get("data", {}).get("servicelist", {}).get(host, {})

        if not services:
            print(f"⚠️  No services found for host '{host}'.", file=sys.stderr)
            return

        target_status = self.FILTER_MAP.get(output_filter.upper()) if output_filter else None

        results = []
        for svc_name, details in services.items():
            if service and svc_name != service:
                continue

            status_code = details.get("status")

            if target_status and status_code != target_status:
                continue

            result = self._build_service_result(host, svc_name, details)
            results.append(result)

        if not results:
            msg = f" for specified filter '{output_filter}'" if output_filter else ""
            print(
                f"⚠️  Service '{service}' not found on host '{host}'{msg}.",
                file=sys.stderr,
            )
            return

        header = (
            f"Monitored Service: '{service}' on '{host}'"
            if service
            else f"Monitored Services for Host: '{host}'"
        )
        self._print_service_results(
            results,
            output_format,
            show_output,
            header,
            secondary_key="service",
        )

    def show_single_service(
        self,
        service=None,
        show_output=False,
        output_filter=None,
        output_format="text",
    ):
        """Displays a specific service, across all hosts."""
        if not service:
            print(
                "⚠️  No service specified. We should never be here.",
                file=sys.stderr,
            )
            return

        params = {
            "query": "servicelist",
            "details": "true",
            "servicedescription": service,
        }

        response = self._get_json(params)
        services = response.get("data", {}).get("servicelist", {})

        if not services:
            print(
                f"⚠️  No hosts found running service '{service}'.",
                file=sys.stderr,
            )
            return

        target_status = self.FILTER_MAP.get(output_filter.upper()) if output_filter else None

        results = []
        for system_name, details in services.items():
            if service in details:
                svc_details = details[service]
                status_code = svc_details.get("status")

                if target_status and status_code != target_status:
                    continue

                result = self._build_service_result(system_name, service, svc_details)
                results.append(result)

        if not results:
            msg = (
                f" using the specified filter '{output_filter}'"
                if output_filter
                else ""
            )
            print(
                f"⚠️  No results found for service '{service}'{msg}.",
                file=sys.stderr,
            )
            return

        header = f"Monitored Service: '{service}'"
        self._print_service_results(
            results, output_format, show_output, header, secondary_key="host"
        )

    def show_service_uptime(self, host, service, days=365, output_format="text"):
        """Displays uptime duration and dynamic availability report."""
        params = {
            "query": "service",
            "hostname": host,
            "servicedescription": service,
        }
        response = self._get_json(params)
        svc_data = response.get("data", {}).get("service", {})

        if not svc_data:
            print(
                f"⚠️  Service '{service}' on host '{host}' not found.",
                file=sys.stderr,
            )
            return

        status_code = svc_data.get("status")
        status_text = self._get_status_text(status_code, is_host=False)
        plugin_output = svc_data.get("plugin_output", "N/A")

        last_change = svc_data.get("last_state_change", 0)
        duration_str = self._format_duration(last_change)

        report_data = {
            "host": host,
            "service": service,
            "status": status_text,
            "duration": duration_str,
            "output": plugin_output,
            "availability_days": days,
            "percent_ok": None,
            "percent_warning": None,
            "percent_unknown": None,
            "percent_critical": None,
        }

        # Fetch Dynamic Availability Report
        avail_data = self._fetch_availability_data(host, service=service, days=days)
        if avail_data:
            report_data.update(avail_data)

        self._print_uptime_report(report_data, output_format, is_host=False)

    def show_host_uptime(self, host, days=365, output_format="text"):
        """Displays uptime duration and availability report for a HOST."""
        params = {"query": "host", "hostname": host}
        response = self._get_json(params)
        host_data = response.get("data", {}).get("host", {})

        if not host_data:
            print(f"⚠️  Host '{host}' not found.", file=sys.stderr)
            return

        status_code = host_data.get("status")
        status_text = self._get_status_text(status_code, is_host=True)
        plugin_output = host_data.get("plugin_output", "N/A")

        last_change = host_data.get("last_state_change", 0)
        duration_str = self._format_duration(last_change)

        report_data = {
            "host": host,
            "status": status_text,
            "duration": duration_str,
            "output": plugin_output,
            "availability_days": days,
            "percent_up": None,
            "percent_down": None,
            "percent_unreachable": None,
        }

        avail_data = self._fetch_availability_data(host, service=None, days=days)
        if avail_data:
            report_data.update(avail_data)

        self._print_uptime_report(report_data, output_format, is_host=True)

    def show_status(self):
        print("\n--- Nagios Core Status ---")
        prog = (
            self._get_json({"query": "programstatus"})
            .get("data", {})
            .get("programstatus", {})
        )
        status_map = {
            "Notifications Enabled": prog.get("enable_notifications"),
            "Active Service Checks": prog.get("execute_service_checks"),
            "Active Host Checks": prog.get("execute_host_checks"),
            "Event Handlers": prog.get("enable_event_handlers"),
        }
        for key, val in status_map.items():
            print(f"{key:<25}: {'✅ ENABLED' if val else '❌ DISABLED'}")
        print()

    def show_ack_history(self, host, service=None, days=7):
        """Displays full acknowledgement history by querying active comments."""
        # Use query=commentlist with details=true for reliable Status API data
        params = {"query": "commentlist", "details": "true"}
        start_ts = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()

        print(f"\n--- Acknowledgement History ({days} days) ---")
        if service:
            print(f"Target: {host} -> {service}")
        else:
            print(f"Target: Host {host}")
        print("-" * 70)

        try:
            # Query active status for persistent comments
            resp = self._get_json(params)
            data = resp.get("data", {})
            comments_blob = data.get("commentlist") or data.get("comments") or {}

            # Correctly handle Nagios 4.4 dictionary iteration
            if isinstance(comments_blob, dict):
                comment_items = comments_blob.values()
            else:
                comment_items = comments_blob

            found_any = False
            for details in comment_items:
                # Ensure we have a valid data dictionary
                if not isinstance(details, dict):
                    continue

                # Type 4 is Acknowledgement
                if int(details.get("entry_type", 0)) != 4:
                    continue

                # Fix Millisecond timestamps (detect values > 10,000,000,000)
                entry_time = self._normalize_timestamp(float(details.get("entry_time", 0)))

                if entry_time < start_ts:
                    continue

                log_host = details.get("host_name", "")
                if not self._matches_host(log_host, host):
                    continue

                is_match = False
                if service:
                    # Service acks must match description exactly
                    log_svc = details.get("service_description", "").lower()
                    if log_svc == service.lower():
                        is_match = True
                else:
                    # Host acks have empty service descriptions
                    if not details.get("service_description"):
                        is_match = True

                if is_match:
                    found_any = True
                    ts = datetime.datetime.fromtimestamp(entry_time).strftime(
                        self.date_format
                    )
                    author = details.get("author", "Unknown")
                    msg = details.get("comment_data", "N/A")

                    print(f"[{ts}] Author: {author}")
                    print(f"    Message: {msg}")
                    print("-" * 30)

            if not found_any:
                print("No persistent acknowledgements found for this time range.")

        except Exception as e:
            print(f"❌ Error fetching history from status API: {e}")


def main():
    parser = argparse.ArgumentParser(
        prog="mozzo", description="Mozzo - Nagios Core command line assistant"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("-c", "--config", type=str, help="Path to config.yml")
    parser.add_argument(
        "-m",
        "--message",
        type=str,
        help="Custom message for acknowledgements/downtime",
    )
    parser.add_argument("--ack", action="store_true", help="Acknowledge an alert")
    parser.add_argument(
        "--downtime",
        "--set-downtime",
        dest="downtime",
        action="store_true",
        help="Set downtime",
    )
    parser.add_argument("--host", type=str, help="Target host")
    parser.add_argument("--service", type=str, help="Target service")
    parser.add_argument(
        "--all-services", action="store_true", help="Apply to all services on host"
    )
    parser.add_argument(
        "--unhandled", action="store_true", help="List unhandled alerts"
    )
    parser.add_argument(
        "--service-issues", action="store_true", help="List services with issues"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show status (global, host, or service)"
    )
    parser.add_argument(
        "--uptime",
        action="store_true",
        help="Show uptime/availability report for a service",
    )
    parser.add_argument(
        "--days",
        type=float,
        default=None,
        help="Number of days for availability report or history",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (text, json, csv)",
    )
    parser.add_argument(
        "--disable-alerts", action="store_true", help="Disable notifications"
    )
    parser.add_argument(
        "--enable-alerts", action="store_true", help="Enable notifications"
    )
    parser.add_argument(
        "--show-output",
        default=False,
        action="store_true",
        help="Show check output; only used with --service",
    )
    parser.add_argument(
        "--output-filter",
        type=str.upper,
        choices=["PENDING", "OK", "WARNING", "UNKNOWN", "CRITICAL"],
        default=None,
        help="Limit results by status (e.g., OK, CRITICAL)",
    )
    parser.add_argument(
        "--ack-history",
        action="store_true",
        help="Show history of acknowledgements",
    )

    args = parser.parse_args()
    client = MozzoNagiosClient(
        config_path=args.config, message=args.message, days=args.days
    )

    if args.unhandled:
        client.show_unhandled()
    elif args.service_issues:
        client.show_service_issues(args.host)
    elif args.status:
        if args.host and args.uptime:
            uptime_days = args.days if args.days is not None else client.report_days
            if args.service:
                client.show_service_uptime(
                    args.host, args.service, uptime_days, args.format
                )
            else:
                client.show_host_uptime(args.host, uptime_days, args.format)
        elif args.host:
            client.show_host_services(
                args.host,
                args.service,
                args.show_output,
                args.output_filter,
                args.format,
            )
        elif args.service:
            client.show_single_service(
                args.service, args.show_output, args.output_filter, args.format
            )
        else:
            client.show_status()
    elif args.disable_alerts:
        client.toggle_alerts(
            enable=False,
            host=args.host,
            service=args.service,
            all_services=args.all_services,
        )
    elif args.enable_alerts:
        client.toggle_alerts(
            enable=True,
            host=args.host,
            service=args.service,
            all_services=args.all_services,
        )
    elif args.ack and args.host:
        if args.all_services:
            client.ack_all_services(args.host)
        elif args.service:
            client.ack_service(args.host, args.service)
        else:
            client.ack_host(args.host)
    elif args.downtime and args.host:
        if args.all_services:
            client.set_downtime_all(args.host)
        elif args.service:
            client.set_downtime_service(args.host, args.service)
        else:
            client.set_downtime_host(args.host)
    elif args.ack_history and args.host:
        history_days = args.days if args.days is not None else client.report_days
        client.show_ack_history(args.host, args.service, history_days)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
