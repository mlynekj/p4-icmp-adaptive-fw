#!/usr/bin/env python3
import argparse
import os
import sys
from time import sleep
import grpc

# Import P4Runtime lib from parent utils dir
# Probably there's a better way of doing this.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),'../../utils/'))

import p4runtime_lib.bmv2
import p4runtime_lib.helper
from p4runtime_lib.switch import ShutdownAllSwitchConnections

prumerovaci_doba = 10
kriticka_hodnota_ICMP = 10

def printCounter(p4info_helper, sw, counter_name, index):
    for response in sw.ReadCounters(p4info_helper.get_counters_id(counter_name), index):
        for entity in response.entities:
            counter = entity.counter_entry
            print("%s %s %d: %d packets (%d bytes)" % (
                sw.name, counter_name, index,
                counter.data.packet_count, counter.data.byte_count
            ))


def getCounterPacketCountDifference(p4info_helper, sw, counter_name, index):
    """
    Vraci pocet ICMP packetu za poslednich {prumerovaci_doba} vterin

    :param p4info_helper: P4Info helper
    :param sw: cislo switche
    :param counter_name: nazev counteru ktery chci vycitat
    :param index: index counteru ktery chci vycitat
    """
    for response in sw.ReadCounters(p4info_helper.get_counters_id(counter_name), index):    
        for entity in response.entities:
            counter_old = int(entity.counter_entry.data.packet_count)
    sleep(prumerovaci_doba)
    for response in sw.ReadCounters(p4info_helper.get_counters_id(counter_name), index):    
        for entity in response.entities:
            counter_new = int(entity.counter_entry.data.packet_count)
    return(counter_new - counter_old)
            

def writeIpForwardRule(p4info_helper, sw, dst_ip_addr, dst_mac_addr, port):
    """
    Instalace pravidla do tabulky IPv4 forward

    :param p4info_helper: P4Info helper
    :param sw: cislo switche
    :param dst_ip_addr: cilova IP adresa
    :param dst_mac_addr: cilova MAC adresa
    :param port: cislo portu (rozhrani switche)
    """
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        match_fields={
            "hdr.ipv4.dstAddr": (dst_ip_addr, 32)
        },
        action_name="MyIngress.ipv4_forward",
        action_params={
            "dstAddr": dst_mac_addr,
            "port": port
        })
    sw.WriteTableEntry(table_entry)
    print("Installed IPv4 forward rule on %s" % sw.name)


def deleteIpforwardRule(p4info_helper, sw, dst_ip_addr, dst_mac_addr, port):
    """
    Odstraneni pravidla z tabulky IPv4 forward

    :param p4info_helper: P4Info helper
    :param sw: cislo switche
    :param dst_ip_addr: cilova IP adresa
    :param dst_mac_addr: cilova MAC adresa
    :param port: cislo portu (rozhrani switche)
    """
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        match_fields={
            "hdr.ipv4.dstAddr": (dst_ip_addr, 32)
        },
        action_name="MyIngress.ipv4_forward",
        action_params={
            "dstAddr": dst_mac_addr,
            "port": port
        })
    sw.DeleteTableEntry(table_entry)
    print("Removed IPv4 forward rule from %s" % sw.name)


def readTableRules(p4info_helper, sw):
    """
    Reads the table entries from all tables on the switch.

    :param p4info_helper: the P4Info helper
    :param sw: the switch connection
    """
    print('\n----- Reading tables rules for %s -----' % sw.name)
    for response in sw.ReadTableEntries():
        for entity in response.entities:
            entry = entity.table_entry
            table_name = p4info_helper.get_tables_name(entry.table_id)
            print('%s: ' % table_name, end=' ')
            for m in entry.match:
                print(p4info_helper.get_match_field_name(table_name, m.field_id), end=' ')
                print('%r' % (p4info_helper.get_match_field_value(m),), end=' ')
            action = entry.action.action
            action_name = p4info_helper.get_actions_name(action.action_id)
            print('->', action_name, end=' ')
            for p in action.params:
                print(p4info_helper.get_action_param_name(action_name, p.param_id), end=' ')
                print('%r' % p.value, end=' ')
            print()


def printGrpcError(e):
    print("gRPC Error:", e.details(), end=' ')
    status_code = e.code()
    print("(%s)" % status_code.name, end=' ')
    traceback = sys.exc_info()[2]
    print("[%s:%d]" % (traceback.tb_frame.f_code.co_filename, traceback.tb_lineno))


def main(p4info_file_path, bmv2_file_path):
    # Instantiate a P4Runtime helper from the p4info file
    p4info_helper = p4runtime_lib.helper.P4InfoHelper(p4info_file_path)

    try:
        # Create a switch connection object for s1, s2, s3, s4;
        # this is backed by a P4Runtime gRPC connection.
        # Also, dump all P4Runtime messages sent to switch to given txt files.
        s1 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name='s1',
            address='127.0.0.1:50051',
            device_id=0,
            proto_dump_file='logs/s1-p4runtime-requests.txt')
        s2 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name='s2',
            address='127.0.0.1:50052',
            device_id=1,
            proto_dump_file='logs/s2-p4runtime-requests.txt')
        s3 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name='s3',
            address='127.0.0.1:50053',
            device_id=2,
            proto_dump_file='logs/s3-p4runtime-requests.txt')
        s4 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name='s4',
            address='127.0.0.1:50054',
            device_id=3,
            proto_dump_file='logs/s4-p4runtime-requests.txt')

        # Send master arbitration update message to establish this controller as master (required by P4Runtime before performing any other write operation)
        s1.MasterArbitrationUpdate()
        s2.MasterArbitrationUpdate()
        s3.MasterArbitrationUpdate()
        s4.MasterArbitrationUpdate()

        #Uncomment the following lines to read table entries from s1 and s2
        #readTableRules(p4info_helper, s1)
        #readTableRules(p4info_helper, s2)
        #readTableRules(p4info_helper, s3)
        #readTableRules(p4info_helper, s4)
        
        #oznacuje jestli je na switchich zablokovany provoz (abychom nemazali neexistujici pravidla, a naopak)
        s1_blocked_flag = False
        s2_blocked_flag = False

        while True:
            icmp_counter_difference_s1 = getCounterPacketCountDifference(p4info_helper, s1, "MyIngress.icmp_counter", 1)
            icmp_counter_difference_s2 = getCounterPacketCountDifference(p4info_helper, s2, "MyIngress.icmp_counter", 1)

            if (icmp_counter_difference_s1 > kriticka_hodnota_ICMP):
                if (not s1_blocked_flag):
                    print(f"Blokuju provoz na s1, porty 1,2; Pocet ICMP za poslednich {prumerovaci_doba} vterin::{icmp_counter_difference_s1}, prahova hodnota je: {kriticka_hodnota_ICMP}")
                    deleteIpforwardRule(p4info_helper, sw=s1, dst_ip_addr="10.0.1.1", dst_mac_addr="08:00:00:00:01:11", port=1)
                    deleteIpforwardRule(p4info_helper, sw=s1, dst_ip_addr="10.0.2.2", dst_mac_addr="08:00:00:00:02:22", port=2)
                    s1_blocked_flag = True
            else:
                if (s1_blocked_flag):
                    print(f"Povoluju provoz na s1, porty 1,2; Pocet ICMP za poslednich {prumerovaci_doba} vterin::{icmp_counter_difference_s1},  prahova hodnota je: {kriticka_hodnota_ICMP}")
                    writeIpForwardRule(p4info_helper, sw=s1, dst_ip_addr="10.0.1.1", dst_mac_addr="08:00:00:00:01:11", port=1)
                    writeIpForwardRule(p4info_helper, sw=s1, dst_ip_addr="10.0.2.2", dst_mac_addr="08:00:00:00:02:22", port=2)
                    s1_blocked_flag = False

            if (icmp_counter_difference_s2 > kriticka_hodnota_ICMP):
                if (not s2_blocked_flag):
                    print(f"Blokuju provoz na s2, porty 1,2;  Pocet ICMP za poslednich {prumerovaci_doba} vterin::{icmp_counter_difference_s2}, prahova hodnota je: {kriticka_hodnota_ICMP}")
                    deleteIpforwardRule(p4info_helper, sw=s2, dst_ip_addr="10.0.3.3", dst_mac_addr="08:00:00:00:03:33", port=1)
                    deleteIpforwardRule(p4info_helper, sw=s2, dst_ip_addr="10.0.4.4", dst_mac_addr="08:00:00:00:04:44", port=2)
                    s2_blocked_flag = True
            else:
                if (s2_blocked_flag):
                    print(f"Povoluju provoz na s2, porty 1,2; Pocet ICMP za poslednich {prumerovaci_doba} vterin::{icmp_counter_difference_s1}, prahova hodnota je: {kriticka_hodnota_ICMP}")
                    writeIpForwardRule(p4info_helper, sw=s2, dst_ip_addr="10.0.3.3", dst_mac_addr="08:00:00:00:03:33", port=1)
                    writeIpForwardRule(p4info_helper, sw=s2, dst_ip_addr="10.0.4.4", dst_mac_addr="08:00:00:00:04:44", port=2)
                    s2_blocked_flag = False

        # Print the counters every 2 seconds
        #while True:
            #sleep(2)
            #print('\n----- Reading counters -----')
            #printCounter(p4info_helper, s1, "MyIngress.port_counter", 1)
            #printCounter(p4info_helper, s1, "MyIngress.icmp_counter", 1)
            #printCounter(p4info_helper, s3, "MyIngress.icmp_counter", 1)
            #printCounter(p4info_helper, s4, "MyIngress.icmp_counter", 1)

    except KeyboardInterrupt:
        print(" Shutting down.")
    except grpc.RpcError as e:
        printGrpcError(e)

    ShutdownAllSwitchConnections()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='P4Runtime Controller')
    parser.add_argument('--p4info', help='p4info proto in text format from p4c',
                        type=str, action="store", required=False,
                        default='./build/adaptivni_fw.p4.p4info.txt')
    parser.add_argument('--bmv2-json', help='BMv2 JSON file from p4c',
                        type=str, action="store", required=False,
                        default='./build/adaptivni_fw.json')
    args = parser.parse_args()

    if not os.path.exists(args.p4info):
        parser.print_help()
        print("\np4info file not found: %s\nHave you run 'make'?" % args.p4info)
        parser.exit(1)
    if not os.path.exists(args.bmv2_json):
        parser.print_help()
        print("\nBMv2 JSON file not found: %s\nHave you run 'make'?" % args.bmv2_json)
        parser.exit(1)
    main(args.p4info, args.bmv2_json)