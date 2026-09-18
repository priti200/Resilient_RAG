import unittest

from src.representation.flow_to_text import (
    active_flags,
    active_states,
    protocol_from_row,
    row_to_record,
    row_to_text,
)


def make_row(**overrides):
    row = {
        "CategoryLabel": "dos",
        "Seq": 42,
        "SrcTCPBase": 10,
        "DstTCPBase": 20,
        "Sport": 1234,
        "Dport": 80,
        "Proto_arp": False,
        "Proto_icmp": False,
        "Proto_ipv6-icmp": False,
        "Proto_tcp": False,
        "Proto_udp": False,
        "Flgs_e": False,
        "Flgs_e_*": False,
        "Flgs_e_d": False,
        "Flgs_e_g": False,
        "Flgs_e_r": False,
        "Flgs_e_s": False,
        "Flgs_eU": False,
        "State_CLO": False,
        "State_CON": False,
        "State_ECO": False,
        "State_FIN": False,
        "State_INT": False,
        "State_NRS": False,
        "State_REQ": False,
        "State_RSP": False,
        "State_RST": False,
        "State_TST": False,
        "State_URH": False,
        "State_URHPRO": False,
        "TotPkts": 12,
        "TotBytes": 200,
        "TotAppByte": 150,
        "SrcPkts": 6,
        "DstPkts": 6,
        "SrcBytes": 100,
        "DstBytes": 100,
        "SAppBytes": 80,
        "DAppBytes": 70,
        "sMeanPktSz": 15.0,
        "dMeanPktSz": 16.0,
        "sMinPktSz": 10,
        "dMinPktSz": 11,
        "sMaxPktSz": 20,
        "dMaxPktSz": 21,
        "Mean": 15.5,
        "Min": 10,
        "Max": 21,
        "Sum": 180,
        "Rate": 1000,
        "SrcRate": 500,
        "DstRate": 500,
        "Load": 2000,
        "SrcLoad": 1000,
        "DstLoad": 1000,
        "SrcLoss": 2,
        "DstLoss": 1,
        "Loss": 3,
        "pLoss": 25,
        "DIntPktAct": 12,
        "SIntPktAct": 13,
        "DIntPkt": 14,
        "SIntPkt": 15,
        "DIntPktMin": 10,
        "DIntPktMax": 20,
        "SIntPktMin": 11,
        "SIntPktMax": 21,
        "SIntPktIdl": 22,
        "SrcJitter": 3.2,
        "TcpRtt": 0.5,
        "DstWin": 64,
        "SrcWin": 128,
        "SynAck": 1,
        "AckDat": 0,
        "sTos": 0,
        "sTtl": 64,
        "sHops": 3,
        "PCRatio": 0.5,
    }
    row.update(overrides)
    return row


class FlowToTextTests(unittest.TestCase):
    def test_tcp_flow(self):
        row = make_row(Proto_tcp=True)
        self.assertEqual(protocol_from_row(row), "TCP")
        text = row_to_text(row)
        self.assertIn("Protocol: TCP", text)
        self.assertIn("Source port: 1234", text)
        self.assertIn("Destination port: 80", text)

    def test_udp_flow(self):
        row = make_row(Proto_udp=True)
        self.assertEqual(protocol_from_row(row), "UDP")
        self.assertIn("Protocol: UDP", row_to_text(row))

    def test_icmp_flow(self):
        row = make_row(Proto_icmp=True)
        self.assertEqual(protocol_from_row(row), "ICMP")
        self.assertIn("Protocol: ICMP", row_to_text(row))

    def test_no_active_flags(self):
        row = make_row()
        self.assertEqual(active_flags(row), "none")
        self.assertIn("Active flow flags: none", row_to_text(row))

    def test_multiple_active_flags(self):
        row = make_row(Flgs_e=True, Flgs_e_s=True, Flgs_e_r=True)
        self.assertEqual(active_flags(row), "e, e_s, e_r")
        self.assertIn("Active flow flags: e, e_s, e_r", row_to_text(row))

    def test_multiple_active_states(self):
        row = make_row(State_CON=True, State_RST=True, State_REQ=True)
        self.assertEqual(active_states(row), "CON, REQ, RST")
        self.assertIn("Connection states: CON, REQ, RST", row_to_text(row))

    def test_missing_or_invalid_protocol_indicators(self):
        row = make_row(Proto_arp=False, Proto_icmp=False, Proto_ipv6_icmp=False, Proto_tcp=False, Proto_udp=False)
        self.assertEqual(protocol_from_row(row), "unknown")

        row2 = make_row(Proto_arp=True, Proto_tcp=True)
        self.assertEqual(protocol_from_row(row2), "ARP, TCP")

    def test_deterministic_output(self):
        row = make_row(Proto_tcp=True, Flgs_e=True, Flgs_e_s=True, State_CON=True, State_RSP=True)
        text1 = row_to_text(row)
        text2 = row_to_text(row)
        self.assertEqual(text1, text2)

    def test_category_label_not_in_text(self):
        row = make_row(CategoryLabel="benign", Proto_tcp=True)
        text = row_to_text(row)
        self.assertNotIn("benign", text.lower())
        self.assertNotIn("CategoryLabel", text)

    def test_excluded_columns_not_in_text(self):
        row = make_row(Seq=99, SrcTCPBase=12, DstTCPBase=34, Proto_tcp=True)
        text = row_to_text(row)
        self.assertNotIn("SrcTCPBase", text)
        self.assertNotIn("DstTCPBase", text)
        self.assertNotIn("Seq", text)

    def test_ports_are_represented(self):
        row = make_row(Proto_udp=True, Sport=5432, Dport=53)
        text = row_to_text(row)
        self.assertIn("Source port: 5432", text)
        self.assertIn("Destination port: 53", text)

    def test_record_metadata_keeps_label(self):
        row = make_row(Proto_tcp=True, Sport=1111, Dport=2222)
        record = row_to_record(row, "train", 1)
        self.assertEqual(record["id"], "train_00000001")
        self.assertEqual(record["label"], "dos")
        self.assertEqual(record["metadata"]["CategoryLabel"], "dos")
        self.assertEqual(record["metadata"]["protocol"], "TCP")
        self.assertEqual(record["metadata"]["Sport"], 1111)
        self.assertEqual(record["metadata"]["Dport"], 2222)
        self.assertNotIn("CategoryLabel", record["text"].lower())


if __name__ == "__main__":
    unittest.main()
