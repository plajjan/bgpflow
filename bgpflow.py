#!/usr/bin/python2.4
# vim: et :

import os
import psycopg2
import radix
import re
import socket
import sys

from twisted.internet import abstract, fdesc, interfaces, protocol, reactor
from twisted.python import log
from twisted.protocols import basic
from twistedsnmp import snmpprotocol, agentproxy

from pybgp import speaker, pathattr, proto

import flowd

class BgpListener(speaker.BGP):
    def connectionMade(self):
        log.msg('connection made!')
        speaker.BGP.connectionMade(self)
        # notify our factory that someone has connected
        self.factory.client_connected(self)

class BgpFactory(protocol.Factory):
    protocol = BgpListener

    def client_connected(self, proto):
        # create a new peer
        peer = self.process.peer(proto)


class NfProtocol(protocol.Protocol):
    def __init__(self):
        log.msg("tjohej NfProtocol init!!")

    def dataReceived(self, buf):
        print "HEJSAN!!"

    def test(self):
        print "TJOHEJ!"

class NfFactory(protocol.Factory):
    protocol = NfProtocol

    def __init__(self, process):
        self.i = 0
        self.process = process
        self.db_cur = self.process.db_conn.cursor()

        self.del_query = "DELETE FROM raw WHERE insert_time < NOW() - '30 min'::interval"
        self.insert_query = "INSERT INTO raw (flow_start, flow_finish, agent, protocol, src_ip, dst_ip, src_port, dst_port, packets, octets, peer_src_as, peer_dst_as, src_as, dst_as, src_aspath, dst_aspath, ifindex_in, ifindex_out, if_in, if_out, sampling_interval) VALUES ((TIMESTAMP 'epoch' + (%(flow_start)s / 1000::numeric) * '1 seconds'::interval) AT TIME ZONE 'UTC', (TIMESTAMP 'epoch' + (%(flow_finish)s / 1000::numeric)* '1 second'::interval) AT TIME ZONE 'UTC', %(agent)s, %(protocol)s, %(src_ip)s, %(dst_ip)s, %(src_port)s, %(dst_port)s, %(packets)s, %(octets)s, %(peer_src_as)s, %(peer_dst_as)s, %(src_as)s, %(dst_as)s, %(src_aspath)s, %(dst_aspath)s, %(ifindex_in)s, %(ifindex_out)s, %(if_in)s, %(if_out)s, %(sampling_interval)s)"

        self.ifs = self.process.ifs
        self.rts = self.process.rts


    def makeConnection(self, protocol):
        log.msg("in makeConnection");
        pass

    def datagramReceived(self, buf, file):
        self.processFlow(buf)

    def processFlow(self, flowrec):
        flow = flowd.Flow(blob = flowrec)

        # these seem to be backwards.. strange
        # make sure we get it right, just in case
        if flow.flow_start > flow.flow_finish:
            large = flow.flow_start
            small = flow.flow_finish
        else:
            large = flow.flow_finish
            small = flow.flow_start
        # TODO: handle wrapping, ie finish has wrapped but start has not

        flow_start_in_ms = (flow.agent_sec*1000 + flow.agent_usec) + (flow.sys_uptime_ms - large)
        flow_finish_in_ms = (flow.agent_sec*1000 + flow.agent_usec) + (flow.sys_uptime_ms - small)

        try:
            if_in = self.ifs[flow.agent_addr][flow.if_ndx_in]['type']
        except:
            if_in = None

        try:
            if_out = self.ifs[flow.agent_addr][flow.if_ndx_out]['type']
        except:
            if_out = None

        try:
            rt = self.rts[flow.agent_addr]
        except:
            rt = None

        src_rnode = None
        dst_rnode = None

        if rt is not None:
            try:
                src_rnode = rt.search_best(flow.src_addr)
            except:
                src_rnode = None

            try:
                dst_rnode = rt.search_best(flow.dst_addr)
            except:
                dst_rnode = None

        if src_rnode is not None:
            try:
                src_as_array = src_rnode.data['aspath'].value[0]
            except:
                src_as_array = None
            try:
                src_as = int(src_as_array[-1])
            except:
                src_as = None
            src_aspath = ''
            last_asn = ''
            if src_as_array is not None:
                for asn in src_as_array:
                    if asn != last_asn:
                        if src_aspath != '':
                            src_aspath += ' '
                        src_aspath += str(asn)
                    last_asn = asn
        else:
            src_aspath = None
            src_as = None

        if dst_rnode is not None:
            try:
                dst_as_array = dst_rnode.data['aspath'].value[0]
            except:
                dst_as_array = None
            try:
                dst_as = int(dst_as_array[-1])
            except:
                dst_as = None
            dst_aspath = ''
            last_asn = ''
            if dst_as_array is not None:
                for asn in dst_as_array:
                    if asn != last_asn:
                        if dst_aspath != '':
                            dst_aspath += ' '
                        dst_aspath += str(asn)
                    last_asn = asn
        else:
            dst_aspath = None
            dst_as = None


        data = {'flow_start': flow_start_in_ms,
                'flow_finish': flow_finish_in_ms,
                'agent': flow.agent_addr,
                'protocol': flow.protocol,
                'src_ip': flow.src_addr,
                'dst_ip': flow.dst_addr,
                'src_port': flow.src_port,
                'dst_port': flow.dst_port,
                'packets': flow.packets,
                'octets': flow.octets,
                'src_as': src_as,
                'dst_as': dst_as,
                'src_aspath': src_aspath,
                'dst_aspath': dst_aspath,
   				'peer_src_as': flow.src_as,
				'peer_dst_as': flow.dst_as,
                'ifindex_in': flow.if_ndx_in,
                'ifindex_out': flow.if_ndx_out,
                'if_in': if_in,
                'if_out': if_out,
                'sampling_interval': 8192 }


#        try:
        self.db_cur.execute(self.insert_query, data)
        self.process.db_conn.commit()
 #       except:
    #        print sys.exc_info()
   #         import time
  #          time.sleep(600)

        self.i = self.i + 1
        if self.i%1000 == 0:
            self.i = 0
            self.db_cur.execute(self.del_query)
            self.process.db_conn.commit()


    def write(self, data):
        pass

    def loseConnection(self):
        self.fp.close()

class BgpPeer:
    def __init__(self, process, proto):
        self.proto = proto
        self.peer = self.proto.transport.getPeer()
        self.host = self.peer.host
        self.process = process
        self.i = 0
        self.last_aspath = ''
        self.ifs = {}
        self.rt = radix.Radix()

        log.msg("init of peer: ", self.host)

        self.reinit()
        self.snmp_protocol = snmpprotocol.port()

    def reinit(self, reconnect=False):
        self.state = 'idle'
        if reconnect:
            reactor.callLater(5, self.start)

    def start(self):
        if self.state!='idle':
            raise Exception('already connected')

        self.state = 'connecting'

    def closed(self, reason):
        # TODO: we should just remove the whole peer after "a while", since we
        # have any configuration on this side but just rely on the other end to
        # peer with us
        log.msg("connection to", self.host, "lost", reason)
        self.reinit(True)

    def ok(self, protocol):
        self.proto = protocol
        self.proto.closed = self.closed
        self.state = 'connected'

        log.msg("peer connected", self.host)

        # hook up the message callback to ourselves
        self.proto.handle_msg = self.msg

        # send an open
        self.proto.open(self.process.asnum, self.process.bgpid)

        # get the SNNMP thingy going!
        self.update_ifs()

    def err(self, reason):
        log.msg("connection to", self.host, "failed", reason)

        self.reinit()
        reactor.callLater(5, self.start)

    def msg(self, msg):
        if msg.kind=='open':
            if self.state!='connected':
                raise Exception('open at invalid time')

            log.msg("peer opened", self.host)

            self.state = 'open'
            self.proto.start_timer(msg.holdtime)

            reactor.callLater(0.5, self.send_updates)

        elif msg.kind=='notification':
            log.msg("notification from", self.host, msg)
            self.proto.transport.loseConnection()

            self.reinit(True)

        elif msg.kind=='update':
            if self.i % 10000 == 0:
                num_prefix = 0
                for prefix in self.rt:
                    num_prefix = num_prefix + 1
                print "Number of prefixes: ", num_prefix
            self.i = self.i + 1

            for prefix in msg.withdraw:
                try:
                    self.rt.delete(str(prefix))
                except:
                    pass

            if msg.pathattr.has_key('aspath'):
                self.last_aspath = msg.pathattr['aspath']
            for prefix in msg.nlri:
                rnode = self.rt.search_exact(str(prefix))
                if rnode is not None:
                    try:
                        self.rt.delete(str(prefix))
                    except:
                        pass

                rnode = self.rt.add(str(prefix))
                rnode.data['aspath'] = self.last_aspath

    def send_updates(self):
        if self.state!='open':
            return
        return

    def update_ifs(self):
        proxy = agentproxy.AgentProxy(
            self.host, 161,
            community = 'secret',
            snmpVersion = 'v2',
            protocol = self.snmp_protocol.protocol,
        )
        df = proxy.getTable([ '.1.3.6.1.2.1.31.1.1.1.18' ], timeout=5, retryCount=3)
        df.addCallback(self.snmp_ok)
        df.addErrback(self.snmp_fail)

        reactor.callLater(300, self.update_ifs)

        return df

    def snmp_ok(self, results):
        for base_oid in results:
            for oid in results[base_oid]:
                ifindex = int(oid[-1])
#                log.msg("ifindex:", ifindex, "   value:", results[base_oid][oid])
                self.ifs[ifindex] = {}
                self.ifs[ifindex]['desc'] = results[base_oid][oid]
                # determine if it's a peering interface, ie type = 0
                # if other end is a -CORE- machine it's a core interface (type=1)
                # otherwise it's a "customer" interface, ie type = 2
                #if re.match('ABR:AS[0-9]+;', self.ifs[ifindex]['desc']) is not None:
                if re.match('^.*ABR:AS[0-9]+;.*', self.ifs[ifindex]['desc']) is not None:
#                    log.msg('PEERING interface!')
                    self.ifs[ifindex]['type'] = 0
                elif re.match('^.*Link to .*-CORE-.*', self.ifs[ifindex]['desc']) is not None:
#                    log.msg('CORE interface!')
                    self.ifs[ifindex]['type'] = 1
                else:
#                    log.msg('other interface!')
                    self.ifs[ifindex]['type'] = 2

        return results

    def snmp_fail(self, err):
        print 'ERROR', err.getTraceback()
        return err



class BgpProcess:
    def __init__(self, asnum, bgpid):
        self.asnum = asnum
        self.bgpid = bgpid
        # our BGP peers
        self.peers = {}
        # for holding our route tables
        self.rts = {}
        # for holding router interface info
        self.ifs = {}

        self.timer = None

        self.protocol = speaker.BGP

    def peer(self, proto):
        log.msg('got new peer!')
        p = BgpPeer(self, proto)
        p.start()
        p.ok(proto)

        peer = proto.transport.getPeer()
        host = peer.host

        self.peers[host] = p

        self.rts[host] = p.rt
        self.ifs[host] = p.ifs

        return p



if __name__=='__main__':
    log.FileLogObserver.timeFormat = '%Y-%m-%d %H:%M:%S'
    log.startLogging(sys.stderr)

    myip = socket.gethostbyname(os.uname()[1])

    process = BgpProcess(1257, myip)

    factory = BgpFactory()
    factory.process = process

    try:
        process.db_conn = psycopg2.connect("dbname='flow' user='flowd' host='localhost' password='SECRET'");
    except:
        print "I am unable to connect to the flow database"

    named_pipe_file = '/tmp/flowd'

    nf_factory = NfFactory(process)

#    try:
#        os.unlink(named_pipe_file)
#    except:
#        pass
#    os.mkfifo(named_pipe_file)

    reactor.listenTCP(179, factory)
    reactor.listenUNIXDatagram(named_pipe_file, nf_factory)
    reactor.run()

#    os.unlink(named_pipe_file)




