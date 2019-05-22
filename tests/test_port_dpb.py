from swsscommon import swsscommon
import redis
import time
import os
import pytest
from pytest import *
import json
import re
from port_dpb import Port

@pytest.mark.usefixtures('dpb_setup_fixture')
class TestPortDPB(object):

    def breakin(self, dvs, port_names):
        child_ports = []
        for pname in port_names:
            cp = Port(dvs, pname)
            cp.sync_from_config_db()
            child_ports.append(cp)

        for cp in child_ports:
            cp.delete_from_config_db()
            # TBD, need vs lib to support removing hostif 
            #dvs.runcmd("ip link delete " + cp.get_name())
        print "Deleted child ports:%s from config DB"%port_names

        time.sleep(6)

        for cp in child_ports:
            assert(cp.exists_in_config_db() == False)
        for cp in child_ports:
            assert(cp.exists_in_app_db() == False)
        for cp in child_ports:
            assert(cp.exists_in_asic_db() == False)
        print "Verified child ports are deleted from all DBs"

        p = Port(dvs)
        p.port_merge(child_ports)
        p.write_to_config_db()
        print "Added port:%s to config DB"%p.get_name()
        time.sleep(2)

        p.verify_config_db()
        print "Config DB verification passed!"

        p.verify_app_db()
        print "Application DB verification passed!"

        p.verify_asic_db()
        print "ASIC DB verification passed!"

    def breakout(self, dvs, port_name, num_child_ports):

        p = Port(dvs, port_name)
        p.sync_from_config_db()

        # Delete port from config DB and kernel
        p.delete_from_config_db()
        # TBD, need vs lib to support hostif removal
        #dvs.runcmd("ip link delete " + p.get_name())
        print "Deleted port:%s from config DB"%port_name
        time.sleep(6)

        # Verify port is deleted from all DBs
        assert(p.exists_in_config_db() == False)
        assert(p.exists_in_app_db() == False)
        assert(p.exists_in_asic_db() == False)

        # Create child ports and write to config DB
        child_ports = p.port_split(num_child_ports)
        child_port_names = []
        for cp in child_ports:
            cp.write_to_config_db()
            child_port_names.append(cp.get_name())
        print "Added child ports:%s to config DB"%child_port_names
        time.sleep(6)

        for cp in child_ports:
            assert(cp.exists_in_config_db() == True)
            cp.verify_config_db()
        print "Config DB verification passed"
        for cp in child_ports:
            assert(cp.exists_in_app_db() == True)
            cp.verify_app_db()
        print "APP DB verification passed"
        for cp in child_ports:
            assert(cp.exists_in_asic_db() == True)
            cp.verify_asic_db()
        print "ASIC DB verification passed"

    def change_speed_and_verify(self, dvs, port_names, speed = 100000):
        for port_name  in port_names:
            p = Port(dvs, port_name)
            p.sync_from_config_db()
            p.set_speed(speed)
            p.write_to_config_db()
            p.verify_config_db()
            time.sleep(1)
            p.verify_app_db()
            time.sleep(1)
            p.verify_asic_db()

    '''
    |--------------------------------------------------
    |        | 1X100G | 1X40G | 4X10G | 4X25G | 2X50G |
    |--------------------------------------------------
    | 1X100G |   NA   |   P   |   P   |   P   |   P   |
    |--------------------------------------------------
    | 1X40G  |   P    |   NA  |   P   |   P   |       |
    |--------------------------------------------------
    | 4X10G  |   P    |   P   |   NA  |   P   |       |
    |--------------------------------------------------
    | 4X25G  |   P    |   P   |   P   |   NA  |       |
    |--------------------------------------------------
    | 2X50G  |   P    |       |       |       |   NA  |
    |--------------------------------------------------
    NA    --> Not Applicable
    P     --> Pass
    F     --> Fail
    Empty --> Not Tested
    '''

    '''
    @pytest.mark.skip()
    '''
    def test_port_breakout_one(self, dvs):
        self.breakout(dvs, "Ethernet0", 4)
        print "**** 1X40G --> 4X10G passed ****"
        self.change_speed_and_verify(dvs, ["Ethernet0", "Ethernet1", "Ethernet2", "Ethernet3"], 25000)
        print "**** 4X10G --> 4X25G passed ****"
        self.change_speed_and_verify(dvs, ["Ethernet0", "Ethernet1", "Ethernet2", "Ethernet3"], 10000)
        print "**** 4X25G --> 4X10G passed ****"
        self.breakin(dvs, ["Ethernet0", "Ethernet1", "Ethernet2", "Ethernet3"])
        print "**** 4X10G --> 1X40G passed ****"
        self.change_speed_and_verify(dvs, ["Ethernet0"], 100000)
        print "**** 1X40G --> 1X100G passed ****"
        self.breakout(dvs, "Ethernet0", 4)
        print "**** 1X100G --> 4X25G passed ****"
        self.change_speed_and_verify(dvs, ["Ethernet0", "Ethernet1", "Ethernet2", "Ethernet3"], 10000)
        print "**** 4X25G --> 4X10G passed ****"
        self.change_speed_and_verify(dvs, ["Ethernet0", "Ethernet1", "Ethernet2", "Ethernet3"], 25000)
        print "**** 4X10G --> 4X25G passed ****"
        self.breakin(dvs, ["Ethernet0", "Ethernet1", "Ethernet2", "Ethernet3"])
        print "**** 4X25G --> 1X100G passed ****"
        self.breakout(dvs, "Ethernet0", 2)
        print "**** 1X100G --> 2X50G passed ****"
        self.breakin(dvs, ["Ethernet0", "Ethernet2"])
        print "**** 2X50G --> 1X100G passed ****"
        self.change_speed_and_verify(dvs, ["Ethernet0"], 40000)
        print "**** 1X100G --> 1X40G passed ****"

    '''
    @pytest.mark.skip()
    '''
    def test_port_breakout_multiple(self, dvs):
        port_names = ["Ethernet0", "Ethernet12", "Ethernet64", "Ethernet112"]
        for pname in port_names:
            self.breakout(dvs, pname, 4)
        self.breakin(dvs, ["Ethernet0", "Ethernet1", "Ethernet2", "Ethernet3"])
        self.breakin(dvs, ["Ethernet12", "Ethernet13", "Ethernet14", "Ethernet15"])
        self.breakin(dvs, ["Ethernet64", "Ethernet65", "Ethernet66", "Ethernet67"])
        self.breakin(dvs, ["Ethernet112", "Ethernet113", "Ethernet114", "Ethernet115"])

    @pytest.mark.skip()
    def test_port_breakout_all(self, dvs):
        port_names = []
        for i in range(32):
            pname = "Ethernet" + str(i*4)
            port_names.append(pname)

        for pname in port_names:
            self.breakout(dvs, pname, 4)

        child_port_names = []
        for i in range(128):
            cpname = "Ethernet" + str(i)
            child_port_names.append(cpname)

        for i in range(32):
            start = i*4
            end = start+4
            self.breakin(dvs, child_port_names[start:end])
