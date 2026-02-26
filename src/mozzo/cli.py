import argparse
import yaml
import requests
import urllib3
import datetime
import sys
import os
import json
import csv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MozzoNagiosClient:
    def __init__(self, config_path=None, message=None):
        config_file = self._find_config(config_path)
        if not config_file:
            print(
                "❌ Could not find config.yml.\nPlease ensure config.yml exists in the current directory."
            )
            sys.exit(1)
        try:
            with open(config_file, "r") as f:
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
        self.verify_ssl = self.config.get("verify_ssl", True)
        self.date_format = self.config.get("date_format", "%m-%d-%Y %H:%M:%S")
        self.cmd_url = f"{self.server}/{self.cgi_path}/cmd.cgi"
        self.json_url = f"{self.server}/{self.cgi_path}/statusjson.cgi"

        # Set the custom message or fallback to default
        self.message = message if message else "Action issued by Mozzo CLI"

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

    def _post_cmd(self, payload):
        payload["btnSubmit"] = "Commit"
        payload["com_author"] = self.auth[0]
        payload["com_data"] = self.message

        try:
            response = requests.post(
                self.cmd_url, data=payload, auth=self.auth, verify=self.verify_ssl
            )
            response.raise_for_status()
            if "successfully submitted" in response.text:
                print("✅ Command successfully submitted to Nagios.")
            else:
                print(
                    "⚠️ Command sent, but success message not found. Check permissions."
                )
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP Error submitting command: {e}")

    def _get_json(self, params):
        try:
            response = requests.get(
                self.json_url, params=params, auth=self.auth, verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP Error fetching data: {e}")
            sys.exit(1)

    def _get_downtime_windows(self):
        now = datetime.datetime.now()
        end = now + datetime.timedelta(minutes=self.downtime_mins)
        return now.strftime(self.date_format), end.strftime(self.date_format)

    def ack_service(self, host, service):
        print(f"Acknowledging service '{service}' on host '{host}'...")
        payload = {
            "cmd_typ": 34,
            "cmd_mod": 2,
            "host": host,
            "service": service,
            "sticky_ack": "on",
            "send_notification": "off",
            "persistent": "off",
        }
        self._post_cmd(payload)

    def ack_host(self, host):
        print(f"Acknowledging host '{host}'...")
        payload = {
            "cmd_typ": 33,
            "cmd_mod": 2,
            "host": host,
            "sticky_ack": "on",
            "send_notification": "off",
            "persistent": "off",
        }
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
        start, end = self._get_downtime_windows()
        print(
            f"Setting {self.downtime_mins}m downtime for service '{service}' on '{host}'..."
        )
        payload = {
            "cmd_typ": 56,
            "cmd_mod": 2,
            "host": host,
            "service": service,
            "fixed": 1,
            "start_time": start,
            "end_time": end,
        }
        self._post_cmd(payload)

    def set_downtime_host(self, host):
        start, end = self._get_downtime_windows()
        print(f"Setting {self.downtime_mins}m downtime for host '{host}'...")
        payload = {
            "cmd_typ": 55,
            "cmd_mod": 2,
            "host": host,
            "fixed": 1,
            "start_time": start,
            "end_time": end,
        }
        self._post_cmd(payload)

    def set_downtime_all(self, host):
        start, end = self._get_downtime_windows()
        print(
            f"Setting {self.downtime_mins}m downtime for host '{host}' AND all its services..."
        )
        payload = {
            "cmd_typ": 86,
            "cmd_mod": 2,
            "host": host,
            "fixed": 1,
            "start_time": start,
            "end_time": end,
        }
        self._post_cmd(payload)

    def toggle_alerts(self, enable=True, host=None, service=None, all_services=False):
        if host:
            if all_services:
                cmd_typ = 28 if enable else 29
                print(
                    f"{'Enabling' if enable else 'Disabling'} notifications for all services on '{host}'..."
                )
                self._post_cmd({"cmd_typ": cmd_typ, "cmd_mod": 2, "host": host})
            elif service:
                cmd_typ = 22 if enable else 23
                print(
                    f"{'Enabling' if enable else 'Disabling'} notifications for '{service}' on '{host}'..."
                )
                self._post_cmd(
                    {"cmd_typ": cmd_typ, "cmd_mod": 2, "host": host, "service": service}
                )
            else:
                cmd_typ = 24 if enable else 25
                print(
                    f"{'Enabling' if enable else 'Disabling'} notifications for host '{host}'..."
                )
                self._post_cmd({"cmd_typ": cmd_typ, "cmd_mod": 2, "host": host})
        else:
            print(f"{'Enabling' if enable else 'Disabling'} global notifications...")
            self._post_cmd({"cmd_typ": 12 if enable else 11, "cmd_mod": 2})

    def show_unhandled(self):
        print("\n--- Unhandled Service Alerts ---")
        hosts = (
            self._get_json({"query": "hostlist", "details": "true"})
            .get("data", {})
            .get("hostlist", {})
        )
        services = (
            self._get_json({"query": "servicelist", "details": "true"})
            .get("data", {})
            .get("servicelist", {})
        )

        found = False
        for host, svc_dict in services.items():
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
                if status_code in (4, 8, 16):
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
                    status_text = {4: "WARNING", 8: "UNKNOWN", 16: "CRITICAL"}.get(
                        status_code, f"CODE_{status_code}"
                    )
                    print(
                        f"[{status_text}] {host} -> {svc_name}\n    Output: {details.get('plugin_output')}"
                    )
        if not found:
            print("🎉 No unhandled service alerts found!")

    def show_service_issues(self, host=None):
        conditions = {4: "⚠️  WARNING", 8: "❓UNKNOWN", 16: "❌ CRITICAL"}
        print("\n--- List Service Issues ---")
        services = (
            self._get_json({"query": "servicelist", "details": "false"})
            .get("data", {})
            .get("servicelist", {})
        )

        if host:
            if host in services:
                services = {host: services[host]}
            else:
                print(f"⚠️  {host} not found.")
                return

        found = False
        for key, value in services.items():
            host_has_issues = False
            for hkey, hvalue in value.items():
                if hvalue in (4, 8, 16):
                    host_has_issues = True
                    found = True
            if host_has_issues:
                print(f"{key}:")
                for hkey, hvalue in value.items():
                    if hvalue in (4, 8, 16):
                        print(f"    {conditions[hvalue]} for service: {hkey}")
        if not found:
            print("🎉 No service issues found!")

    def show_host_services(self, host, service=None, show_output=False, output_filter=0, output_format="text"):
        """Displays services for a specific host, optionally filtered by a specific service."""
        params = {"query": "servicelist", "hostname": host, "details": "true"}
        response = self._get_json(params)
        services = response.get("data", {}).get("servicelist", {}).get(host, {})

        if not services:
            print(f"⚠️  No services found for host '{host}'.", file=sys.stderr)
            return

        status_map = {
            1: "⏳ PENDING",
            2: "✅ OK",
            4: "⚠️  WARNING",
            8: "❓ UNKNOWN",
            16: "❌ CRITICAL",
        }

        results = []
        for svc_name, details in services.items():
            # If a specific service is requested, skip everything else
            if service and svc_name != service:
                continue

            status_code = details.get("status")
            status_text = status_map.get(status_code, f"[{status_code}]")
            if (output_filter > 0 and output_filter == status_code) or output_filter == 0:
                results.append(
                    {
                        "host": host,
                        "service": svc_name,
                        "status_code": status_code,
                        "status": status_text,
                        "plugin_output": details.get("plugin_output"),
                        "long_plugin_output": details.get("long_plugin_output"),
                    }
                )

        if not results and service:
            if output_filter > 0:
                print(
                    f"⚠️  Service '{service}' not found on host '{host}' for specified filter.", file=sys.stderr
                )
            else:
                print(
                    f"⚠️  Service '{service}' not found on host '{host}'.", file=sys.stderr
                )
            return

        if output_format == "json":
            print(json.dumps(results, indent=2))
        elif output_format == "csv":
            writer = csv.DictWriter(
                sys.stdout, fieldnames=["host", "service", "status_code", "status"]
            )
            writer.writeheader()
            writer.writerows(results)
        else:
            if service:
                print(f"\n--- Monitored Service: '{service}' on '{host}' ---")
            else:
                print(f"\n--- Monitored Services for Host: '{host}' ---")

            for r in results:
                print("------------------------------------")
                print(f"{r['status']:<12} | {r['service']:>20}")
                if show_output:
                    print("------------------------------------")
                    print(r['plugin_output'])
                    print(r['long_plugin_output'])
                    print("")
            print("------------------------------------")

    def show_single_service(self, service=None, show_output=False, output_filter=0, output_format="text"):
        """Displays a specific service, across all hosts."""
        if service is None:
            print("⚠️  No service specified.  We should never be here.", file=sys.stderr)
            return

        params = {"query": "servicelist", "details": "true"}
        response = self._get_json(params)
        services = response.get("data", {}).get("servicelist", {})

        if not services:
            print("⚠️  No services found.", file=sys.stderr)
            return

        status_map = {
            1: "⏳ PENDING",
            2: "✅ OK",
            4: "⚠️  WARNING ",
            8: "❓ UNKNOWN",
            16: "❌ CRITICAL",
        }

        results = []
        for system_name, details in services.items():
            if service in details:
                status_code = details.get(service).get("status")
                status_text = status_map.get(status_code, f"[{status_code}]")
                if (output_filter > 0 and output_filter == status_code) or output_filter == 0:
                    results.append(
                        {
                            "host": system_name,
                            "service": service,
                            "status_code": status_code,
                            "status": status_text,
                            "plugin_output": details.get(service).get("plugin_output"),
                            "long_plugin_output": details.get(service).get("long_plugin_output"),
                        }
                    )

        if not results and service:
            # it would not make sense to be here ...
            if output_filter > 0:
                print(
                    f"⚠️  No results found for service '{service}' using the specified filter.", file=sys.stderr
                )
            else:
                print(
                    f"⚠️  No results found for service '{service}'.", file=sys.stderr
                )
            return

        if output_format == "json":
            print(json.dumps(results, indent=2))
        elif output_format == "csv":
            writer = csv.DictWriter(
                sys.stdout, fieldnames=["host", "service", "status_code", "status"]
            )
            writer.writeheader()
            writer.writerows(results)
        else:
            print(f"\n--- Monitored Service: '{service}' ---")
            for r in results:
                print("-" * 70)
                print(f"{r['status']:<10} | {r['host']:>55}")
                if show_output:
                    print("-" * 70)
                    print(r['plugin_output'])
                    print(r['long_plugin_output'])
                    print("")
            print("-" * 70)

    def show_service_uptime(self, host, service, days=365, output_format="text"):
        """Displays the current uptime duration and dynamic availability report."""
        params = {"query": "service", "hostname": host, "servicedescription": service}
        response = self._get_json(params)
        svc_data = response.get("data", {}).get("service", {})

        if not svc_data:
            print(
                f"⚠️  Service '{service}' on host '{host}' not found.", file=sys.stderr
            )
            return

        status_map = {
            1: "⏳ PENDING",
            2: "✅ OK",
            4: "⚠️  WARNING",
            8: "❓ UNKNOWN",
            16: "❌ CRITICAL",
        }
        status_code = svc_data.get("status")
        status_text = status_map.get(status_code, f"CODE_{status_code}")
        plugin_output = svc_data.get("plugin_output", "N/A")

        last_change = svc_data.get("last_state_change", 0)
        duration_str = "N/A"
        if last_change > 0:
            if last_change > 9999999999:
                last_change /= 1000.0
            now = datetime.datetime.now().timestamp()
            delta = datetime.timedelta(seconds=int(now - last_change))
            hours, rem = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(rem, 60)
            duration_str = f"{delta.days}d {hours}h {minutes}m {seconds}s"

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
        now_dt = datetime.datetime.now()
        start_dt = now_dt - datetime.timedelta(days=days)
        archive_url = f"{self.server}/{self.cgi_path}/archivejson.cgi"

        arch_params = {
            "query": "availability",
            "availabilityobjecttype": "services",
            "hostname": host,
            "servicedescription": service,
            "starttime": int(start_dt.timestamp()),
            "endtime": int(now_dt.timestamp()),
            "assumeinitialstate": "true",
            "assumestateretention": "true",
            "assumestatesduringnagiosdowntime": "true",
        }

        try:
            arch_resp = requests.get(
                archive_url,
                params=arch_params,
                auth=self.auth,
                verify=self.verify_ssl,
                timeout=15,
            )
            if arch_resp.status_code == 200:
                arch_data = arch_resp.json()

                avail = arch_data.get("data", {}).get("service", {})

                if avail and avail.get("description") == service:
                    t_ok = avail.get("time_ok", 0)
                    t_warn = avail.get("time_warning", 0)
                    t_unk = avail.get("time_unknown", 0)
                    t_crit = avail.get("time_critical", 0)

                    t_nodata = avail.get("time_indeterminate_nodata", 0)
                    t_notrunning = avail.get("time_indeterminate_notrunning", 0)

                    total_time = (
                        t_ok + t_warn + t_unk + t_crit + t_nodata + t_notrunning
                    )

                    if total_time > 0:
                        report_data["percent_ok"] = (t_ok / total_time) * 100
                        report_data["percent_warning"] = (t_warn / total_time) * 100
                        report_data["percent_unknown"] = (t_unk / total_time) * 100
                        report_data["percent_critical"] = (t_crit / total_time) * 100
                    else:
                        report_data["percent_ok"] = 0.0
                        report_data["percent_warning"] = 0.0
                        report_data["percent_unknown"] = 0.0
                        report_data["percent_critical"] = 0.0
                else:
                    report_data["_debug_raw_dump"] = arch_data

        except requests.exceptions.RequestException as e:
            if output_format == "text":
                print(
                    f"⚠️  Could not retrieve availability report via archivejson: {e}",
                    file=sys.stderr,
                )

        if output_format == "json":
            print(json.dumps(report_data, indent=2))
        elif output_format == "csv":
            report_data.pop("_debug_raw_dump", None)
            writer = csv.DictWriter(sys.stdout, fieldnames=report_data.keys())
            writer.writeheader()
            writer.writerow(report_data)
        else:
            print(f"\n--- Service Status & Uptime: '{service}' on '{host}' ---")
            print(f"Status        : {report_data['status']}")
            print(f"State Duration: {report_data['duration']}")
            print(f"Output        : {report_data['output']}")
            print(f"\n--- {days}-Day Availability Report ---")

            if report_data["percent_ok"] is not None:
                print(f"{'State':<10} | {'% Total Time':<15}")
                print("-" * 30)
                print(f"{'OK':<10} | {report_data['percent_ok']:.3f}%")
                print(f"{'WARNING':<10} | {report_data['percent_warning']:.3f}%")
                print(f"{'UNKNOWN':<10} | {report_data['percent_unknown']:.3f}%")
                print(f"{'CRITICAL':<10} | {report_data['percent_critical']:.3f}%")
            else:
                print(
                    f"No historical availability data found for the last {days} days."
                )
                if "_debug_raw_dump" in report_data:
                    print(
                        "\n[DEBUG] Nagios returned an empty availability object. Here is the raw API response:"
                    )
                    print(json.dumps(report_data["_debug_raw_dump"], indent=2))

    def show_host_uptime(self, host, days=365, output_format="text"):
        """Displays the current uptime duration and dynamic availability report for a HOST."""
        params = {"query": "host", "hostname": host}
        response = self._get_json(params)
        host_data = response.get("data", {}).get("host", {})

        if not host_data:
            print(f"⚠️  Host '{host}' not found.", file=sys.stderr)
            return

        status_map = {0: "⏳ PENDING", 2: "✅ UP", 4: "❌ DOWN", 8: "❓ UNREACHABLE"}
        status_code = host_data.get("status")
        status_text = status_map.get(status_code, f"CODE_{status_code}")
        plugin_output = host_data.get("plugin_output", "N/A")

        last_change = host_data.get("last_state_change", 0)
        duration_str = "N/A"
        if last_change > 0:
            if last_change > 9999999999:
                last_change /= 1000.0
            now = datetime.datetime.now().timestamp()
            delta = datetime.timedelta(seconds=int(now - last_change))
            hours, rem = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(rem, 60)
            duration_str = f"{delta.days}d {hours}h {minutes}m {seconds}s"

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

        # Fetch Dynamic Availability Report for HOST
        now_dt = datetime.datetime.now()
        start_dt = now_dt - datetime.timedelta(days=days)
        archive_url = f"{self.server}/{self.cgi_path}/archivejson.cgi"

        arch_params = {
            "query": "availability",
            "availabilityobjecttype": "hosts",
            "hostname": host,
            "starttime": int(start_dt.timestamp()),
            "endtime": int(now_dt.timestamp()),
            "assumeinitialstate": "true",
            "assumestateretention": "true",
            "assumestatesduringnagiosdowntime": "true",
        }

        try:
            arch_resp = requests.get(
                archive_url,
                params=arch_params,
                auth=self.auth,
                verify=self.verify_ssl,
                timeout=15,
            )
            if arch_resp.status_code == 200:
                arch_data = arch_resp.json()

                # Check if Nagios threw a parameter error inside a 200 OK wrapper
                if arch_data.get("result", {}).get("type_code") != 0:
                    report_data["_debug_raw_dump"] = arch_data
                else:
                    avail = arch_data.get("data", {}).get("host", {})

                    if avail and (
                        avail.get("name") == host or avail.get("host_name") == host
                    ):
                        t_up = avail.get("time_up", 0)
                        t_down = avail.get("time_down", 0)
                        t_unreach = avail.get("time_unreachable", 0)

                        t_nodata = avail.get("time_indeterminate_nodata", 0)
                        t_notrunning = avail.get("time_indeterminate_notrunning", 0)

                        total_time = t_up + t_down + t_unreach + t_nodata + t_notrunning

                        if total_time > 0:
                            report_data["percent_up"] = (t_up / total_time) * 100
                            report_data["percent_down"] = (t_down / total_time) * 100
                            report_data["percent_unreachable"] = (
                                t_unreach / total_time
                            ) * 100
                        else:
                            report_data["percent_up"] = report_data["percent_down"] = (
                                report_data["percent_unreachable"]
                            ) = 0.0
                    else:
                        report_data["_debug_raw_dump"] = arch_data

        except requests.exceptions.RequestException as e:
            if output_format == "text":
                print(
                    f"⚠️  Could not retrieve availability report via archivejson: {e}",
                    file=sys.stderr,
                )

        if output_format == "json":
            print(json.dumps(report_data, indent=2))
        elif output_format == "csv":
            report_data.pop("_debug_raw_dump", None)
            writer = csv.DictWriter(sys.stdout, fieldnames=report_data.keys())
            writer.writeheader()
            writer.writerow(report_data)
        else:
            print(f"\n--- Host Status & Uptime: '{host}' ---")
            print(f"Status        : {report_data['status']}")
            print(f"State Duration: {report_data['duration']}")
            print(f"Output        : {report_data['output']}")
            print(f"\n--- {days}-Day Availability Report ---")

            if report_data["percent_up"] is not None:
                print(f"{'State':<12} | {'% Total Time':<15}")
                print("-" * 32)
                print(f"{'UP':<12} | {report_data['percent_up']:.3f}%")
                print(f"{'DOWN':<12} | {report_data['percent_down']:.3f}%")
                print(
                    f"{'UNREACHABLE':<12} | {report_data['percent_unreachable']:.3f}%"
                )
            else:
                print(
                    f"No historical availability data found for the last {days} days."
                )
                if "_debug_raw_dump" in report_data:
                    print(
                        "\n[DEBUG] Nagios returned an empty availability object. Here is the raw API response:"
                    )
                    print(json.dumps(report_data["_debug_raw_dump"], indent=2))

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


def main():
    parser = argparse.ArgumentParser(
        description="Mozzo - Nagios Core command line assistant"
    )
    parser.add_argument("-c", "--config", type=str, help="Path to specific config.yml")
    parser.add_argument(
        "-m", "--message", type=str, help="Custom message for acknowledgements/downtime"
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
        type=int,
        default=365,
        help="Number of days for availability report (default: 365)",
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
        "--show-output", default=False, action="store_true", help="Show check output; only used with --service"
    )
    parser.add_argument(
        "--output-filter",
        type=int,
        default=0,
        help="Limit --show-output results (1 = PENDING; 2 = OK; 4 = WARNING; 8 = UNKNOWN; 16 = CRITICAL)",
    )

    args = parser.parse_args()
    client = MozzoNagiosClient(config_path=args.config, message=args.message)

    if args.unhandled:
        client.show_unhandled()
    elif args.service_issues:
        client.show_service_issues(args.host)
    elif args.status:
        if args.host and args.uptime:
            if args.service:
                client.show_service_uptime(
                    args.host, args.service, args.days, args.format
                )
            else:
                client.show_host_uptime(args.host, args.days, args.format)
        elif args.host:
            client.show_host_services(args.host, args.service, args.show_output, args.output_filter, args.format)
        elif args.service:
            client.show_single_service(args.service, args.show_output, args.output_filter, args.format)
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
