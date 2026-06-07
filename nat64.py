# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "netmiko",
# ]
# ///

import argparse
import sys

from netmiko import ConnectHandler

# KONFIGURACJA NAT64
NAT64_COMMANDS = [
    # Workaround dla błędu przekazywania NAT64 w obrazach IOSv
    "ipv6 unicast-routing",
    "no ip cef",
    "no ipv6 cef",
    # Konfiguracja interfejsu IPv4 (Bezpośrednio w podsieci serwera)
    "interface GigabitEthernet0/0",
    "ip address 10.1.113.1 255.255.255.0",
    "nat64 enable",  # TODO: Włącz NAT64 dla interfejsu w stronę sieci IPv4 (Gi0/0)
    "no shutdown",
    # Konfiguracja interfejsu IPv6 (Bezpośrednio w podsieci klienta)
    "interface GigabitEthernet0/1",
    "ipv6 address 2001:DB8:3001::1/64",
    "nat64 enable",  # TODO: Włącz NAT64 dla interfejsu w stronę sieci IPv6 (Gi0/1)
    "no shutdown",
    "exit",
    # Lista dostępu dopasowująca sieć IPv6
    "ipv6 access-list nat64acl",
    "permit ipv6 2001:DB8:3001::/64 any",
    "exit",
    # Globalne reguły translacji NAT64 i pula IPv4
    "nat64 prefix stateful 2800:1503:2000:1:1::/96",  # TODO: Zdefiniuj prefiks NAT64 stateful (prefiks: 2800:1503:2000:1:1::/96)
    "nat64 v4 pool pool1 50.50.50.50 50.50.50.53",  # TODO: Zdefiniuj pulę IPv4 (min. 4 adresy: .50 do .53)
    "nat64 v6v4 list nat64acl pool pool1 overload",  # TODO: Powiąż listę 'nat64acl' z pulą 'pool1' (overload)
]


def run_commands(device_config, commands, is_config=True):
    try:
        with ConnectHandler(**device_config) as net:
            if not is_config:
                return net.send_command(commands)
            result = net.send_config_set(commands)
            net.save_config()
            return result
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Skrypt automatyzujący konfigurację Stateful NAT64"
    )
    parser.add_argument("--ip", required=True, help="Adres IP zarządzania routera")
    parser.add_argument(
        "--action",
        required=True,
        choices=["config", "translations", "statistics", "pingv6", "pingv4", "reset"],
        help="Akcja do wykonania",
    )

    args = parser.parse_args()

    device_config = {
        "device_type": "cisco_ios",
        "host": args.ip,
        "username": "admin",
        "password": "Cisco123!",
        "global_delay_factor": 1.5,
    }

    output = ""
    if args.action == "config":
        output = run_commands(device_config, NAT64_COMMANDS, is_config=True)
    elif args.action == "translations":
        output = run_commands(device_config, "show nat64 translations", is_config=False)
    elif args.action == "statistics":
        output = run_commands(device_config, "show nat64 statistics", is_config=False)
    elif args.action == "pingv6":
        output = run_commands(
            device_config, "ping ipv6 2001:DB8:3001::9", is_config=False
        )
    elif args.action == "pingv4":
        output = run_commands(device_config, "ping 10.1.113.2", is_config=False)
    elif args.action == "reset":
        reset_cmds = [
            "no nat64 v6v4 list nat64acl pool pool1",
            "no nat64 prefix stateful 2800:1503:2000:1:1::/96",
            "no nat64 v4 pool pool1",
            "no ipv6 access-list nat64acl",
            "default interface GigabitEthernet0/0",
            "interface GigabitEthernet0/0",
            "ip address 10.1.113.1 255.255.255.0",
            "no shutdown",
            "default interface GigabitEthernet0/1",
            "interface GigabitEthernet0/1",
            "ipv6 address 2001:DB8:3001::1/64",
            "no shutdown",
        ]
        output = run_commands(device_config, reset_cmds, is_config=True)
    print(output)


if __name__ == "__main__":
    main()
