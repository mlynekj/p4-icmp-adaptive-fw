#!/usr/bin/env python3
import random
import socket
import sys

from time import sleep
from scapy.all import IP, TCP, Ether, ICMP,  get_if_hwaddr, get_if_list, sendp

"""
Posila pravidelne ICMP packety, dle frekvence specifikovane v argumentu
"""

def get_if():
    ifs=get_if_list()
    iface=None # "h1-eth0"
    for i in get_if_list():
        if "eth0" in i:
            iface=i
            break;
    if not iface:
        print("Cannot find eth0 interface")
        exit(1)
    return iface


def main():

    if len(sys.argv)<3:
        print('pass argument: <destination> <frequency>')
        exit(1)

    addr = socket.gethostbyname(sys.argv[1])
    iface = get_if()

    frequency = int(sys.argv[2])

    print("sending on interface %s to %s with frequency %d" % (iface, str(addr), frequency))
    pkt =  Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
    pkt = pkt /IP(dst=addr) / ICMP()
    pkt.show2()

    try:
        while (True):
            sleep(1/frequency)
            sendp(pkt, iface=iface, verbose=False)
    except KeyboardInterrupt:
            print(" Shutting down.")


if __name__ == '__main__':
    main()