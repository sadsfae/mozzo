import argparse
import yaml
import requests
import urllib3
import datetime
import sys
import os

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

        # Priority order: User profile -> System-wide -> Current Directory (repo)
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
        # Inject the dynamically set message
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

            # Use tuple for explicit fallback lookups
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
                if hvalue == 4 or hvalue == 8 or hvalue == 16:
                    host_has_issues = True
                    found = True
            if host_has_issues:
                print(f"{key}:")
                for hkey, hvalue in value.items():
                    if hvalue == 4 or hvalue == 8 or hvalue == 16:
                        print(f"    {conditions[hvalue]} for service: {hkey}")

        if not found:
            print("🎉 No service issues found!")

    def show_status(self):
        print("\n--- Nagios Core Status ---")
        prog = (
            self._get_json({"query": "programstatus"})
            .get("data", {})
            .get("programstatus", {})
        )
        # Updated to the correct Nagios JSON keys
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
        "-m",
        "--message",
        type=str,
        help="Custom message/comment for acknowledgements and downtime",
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
        "--service-issues",
        action="store_true",
        help="List services with issues, acked or otherwise",
    )
    parser.add_argument(
        "--status", action="store_true", help="Show Nagios process status"
    )
    parser.add_argument(
        "--disable-alerts", action="store_true", help="Disable notifications"
    )
    parser.add_argument(
        "--enable-alerts", action="store_true", help="Enable notifications"
    )

    args = parser.parse_args()

    # Pass the message argument to the client
    client = MozzoNagiosClient(config_path=args.config, message=args.message)

    if args.unhandled:
        client.show_unhandled()
    elif args.service_issues:
        client.show_service_issues(args.host)
    elif args.status:
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
