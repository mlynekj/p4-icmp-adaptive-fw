# Adaptive firewall implemented using the P4 language

School project: Implementation of simple adaptive firewall, reacting to number of ICMP packets sent through switch interfaces. This project was only meant as a proof of concept of how SDN networks can be defined.

The vSwitches are programmed using the P4 language, while the SDN controller is written in Python.

Brief description of the project is below. More deatils are included in the *.pdf* file in the *latex* directory. Working demonstration is presented in the *.mkv* video file below.

https://github.com/user-attachments/assets/fc96026a-05eb-4938-9dc2-7068c43d4682

A prebuilt basic example `basic.p4` was used to implement the adaptive firewall. It consisted of the basic P4 programs, as well as basic network topology with 4 hosts and 4 switches.

![image](https://github.com/user-attachments/assets/59503dc6-79fe-4470-aad8-73827c96c47f)

---

## Adaptive Firewall Implementation

The goal is to dynamically allow or block traffic based on the number of ICMP packets observed.

### Counting IPv4 Packets

#### Code Modifications

Added a `counter` in the `Ingress` section named `port_counter` to count packets and bytes per port.

#### Reading Counter Values

Used `Runtime CLI` to inspect counter values via thrift ports (9090–9093 for switches s1–s4).

### ICMP Packet Detection

ICMP identified using the `protocol` field in the IPv4 header (value `1` for ICMP). Required:
- Table definition
- Action for processing
- Table application condition

Manual table entries were added via `sX-runtime.json` to activate ICMP processing.

#### Functionality Verification

Verified by sending 10 pings (20 ICMP packets). Non-ICMP traffic (e.g. `telnet`) did not affect the ICMP counter.

#### Distinguishing REQUEST vs REPLY

Used the `code` field in the ICMP header (`8` for request, `0` for reply).  
Added:
- ICMP header definition
- ICMP parser
- Logic for distinguishing message types
- ICMP deparser

Final implementation counted only ICMP Echo Reply messages.

### Controller Implementation

Python-based controller using **P4Runtime** over **gRPC**.

#### Communication with Switches

P4Runtime runs via gRPC server on TCP port `9559`.

#### Controller Skeleton

Main method `main()`:
- Connects to switches
- Sends master arbitration update
- Reads tables and counters every 2 seconds

#### Table Manipulation

- `writeIpForwardRule()` adds routing entries
- `deleteIpForwardRule()` removes them (required custom `DeleteTableEntry` implementation)

#### Blocking/Unblocking Logic

If ICMP Echo Reply packet count exceeds a threshold (default: 10 in 10s), routing entries for ports 1 and 2 are deleted. When the count drops below the threshold, entries are re-added.

Tested using:

```bash
ping -i 0.5
```

This command sends 2 packets per second, causing periodic blocking and unblocking.

## References

1. [P4 Guide Installation](https://github.com/jafingerhut/p4-guide/blob/master/bin/README-install-troubleshooting.md)  
2. [P4 Language Specification](https://p4.org/p4-spec/docs/P4-16-v1.2.2.html)  
3. [P4 Language Tutorial](https://opennetworking.org/wp-content/uploads/2020/12/P4_tutorial_01_basics.gslide.pdf)  
4. [Cornell CS 6114: P4 Traffic Monitoring](https://cornell-pl.github.io/cs6114/lecture07.html)  
5. [BMv2 Simple Switch](https://github.com/p4lang/behavioral-model/blob/main/docs/simple_switch.md)  
6. [P4-Learning](https://github.com/nsg-ethz/p4-learning)  
7. [Runtime CLI](https://github.com/p4lang/behavioral-model/blob/main/docs/runtime_CLI.md)  
8. [List of IP protocol numbers](https://en.wikipedia.org/wiki/List_of_IP_protocol_numbers)  
9. [ICMP Control Messages](https://en.wikipedia.org/wiki/Internet_Control_Message_Protocol%5C#Control_messages)
