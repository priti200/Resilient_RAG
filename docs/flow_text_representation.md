# Flow-to-Text Representation

This milestone creates a deterministic, rule-based natural-language representation for the cleaned network-flow dataset without modifying the source CSV files.

## Source inputs

The representation layer reads only these downstream files:

- `data/cleaned/train.csv`
- `data/cleaned/validation.csv`
- `data/cleaned/test.csv`

It does not use `data/cleaned/train_balanced.csv`.

## Excluded columns

The following columns are excluded from the generated text because they are not meaningful narrative features or they must remain as metadata only:

- `Seq`
- `SrcTCPBase`
- `DstTCPBase`
- `CategoryLabel`

The research requirement still keeps `Sport` and `Dport` in the flow text because they are protocol and endpoint-relevant features.

## Included network information

The text generator preserves the key network-flow fields grouped as follows:

- Flow / traffic volume
- Packet characteristics
- Traffic rates and load
- Loss / reliability
- Timing / inter-packet behavior
- TCP / connection characteristics
- Protocol indicators
- Flow flags
- Connection states
- Source and destination ports

## Protocol conversion

The one-hot protocol indicators are converted into a single human-readable protocol value:

- `Proto_arp` -> `ARP`
- `Proto_icmp` -> `ICMP`
- `Proto_ipv6-icmp` -> `IPv6-ICMP`
- `Proto_tcp` -> `TCP`
- `Proto_udp` -> `UDP`

If no protocol indicator is active, the protocol is rendered as `unknown`.
If multiple are active, the output preserves all active protocol names in deterministic order.

## Flag conversion

The flow flag columns are converted into a human-readable list:

- `Flgs_e` -> `e`
- `Flgs_e_*` -> `e_*`
- `Flgs_e_d` -> `e_d`
- `Flgs_e_g` -> `e_g`
- `Flgs_e_r` -> `e_r`
- `Flgs_e_s` -> `e_s`
- `Flgs_eU` -> `eU`

Example output:

`Active flow flags: e, e_s`

If no flags are active:

`Active flow flags: none`

## State conversion

The connection-state columns are converted into a human-readable list as well:

- `State_CLO` -> `CLO`
- `State_CON` -> `CON`
- `State_ECO` -> `ECO`
- `State_FIN` -> `FIN`
- `State_INT` -> `INT`
- `State_NRS` -> `NRS`
- `State_REQ` -> `REQ`
- `State_RSP` -> `RSP`
- `State_RST` -> `RST`
- `State_TST` -> `TST`
- `State_URH` -> `URH`
- `State_URHPRO` -> `URHPRO`

Examples:

- `Connection states: CON`
- `Connection states: CON, RST`
- `Connection states: none`

## Text template

The generator uses a fixed deterministic template:

```text
Network flow:
- Protocol: TCP
- Source port: 1234
- Destination port: 80

Traffic volume:
- Total packets: 123
- Total bytes: 4567
- Application bytes: 2345
- Source packets: 60
- Destination packets: 63
- Source bytes: 2200
- Destination bytes: 2367
- Source application bytes: 1200
- Destination application bytes: 1145

Packet characteristics:
- ...

Traffic rates and load:
- ...

Loss:
- ...

Timing:
- ...

TCP/connection characteristics:
- ...

Connection behavior:
- Active flow flags: e, e_s
- Connection states: CON, RST
```

This is deterministic: the same row always yields the same text.

## Output JSONL schema

Each generated record is a JSON object with this structure:

```json
{
  "id": "train_00000001",
  "text": "...deterministic text...",
  "label": "dos",
  "metadata": {
    "flow_id": "train_00000001",
    "CategoryLabel": "dos",
    "protocol": "TCP",
    "Sport": 1234,
    "Dport": 80,
    "features": {
      "...": "..."
    }
  }
}
```

## Deterministic behavior

The transformation is rule-based and deterministic. It does not:

- paraphrase rows differently
- invoke an LLM
- add synthetic values
- change the underlying stored values in the CSVs
- hide active protocol/flag/state indicators

The same row processed twice will produce the same output string.

## Why CategoryLabel stays in metadata

`CategoryLabel` is necessary for later evaluation and downstream analysis, but it must not be included in the generated natural-language text.

This preserves the research requirement that the generated text remains a flow description without embedding labels that would leak future class information into the representation layer.
