# Flow-Text Schema Report for Downstream Dataset

Scope: This report inspects only:
- `data/cleaned/train.csv`
- `data/cleaned/validation.csv`
- `data/cleaned/test.csv`

No files were modified. The preprocessing stage was not redone or changed.

## 1) Exact row and column counts

| File | Rows | Columns |
|---|---:|---:|
| `data/cleaned/train.csv` | 3,660,514 | 78 |
| `data/cleaned/validation.csv` | 784,396 | 78 |
| `data/cleaned/test.csv` | 784,396 | 78 |

## 2) Complete list of column names

The columns are, in order:

```text
DIntPktAct,
Seq,
SrcLoss,
TotPkts,
dMeanPktSz,
DstWin,
Mean,
SIntPktMax,
SIntPktIdl,
DIntPktMin,
DAppBytes,
Sport,
DstPkts,
DstRate,
PCRatio,
DIntPktMax,
DIntPkt,
TotAppByte,
SynAck,
Dport,
Rate,
SrcRate,
SrcLoad,
DstTCPBase,
sMeanPktSz,
SrcBytes,
sMinPktSz,
sTos,
SrcJitter,
DstLoss,
TotBytes,
Loss,
SIntPktMin,
SrcWin,
pLoss,
SIntPktAct,
SrcPkts,
AckDat,
Load,
Min,
DstBytes,
Sum,
SIntPkt,
Max,
sTtl,
sMaxPktSz,
dMaxPktSz,
sHops,
SrcTCPBase,
TcpRtt,
dMinPktSz,
DstLoad,
SAppBytes,
Proto_arp,
Proto_icmp,
Proto_ipv6-icmp,
Proto_tcp,
Proto_udp,
Flgs_e,
Flgs_e_*,
Flgs_e_d,
Flgs_e_g,
Flgs_e_r,
Flgs_e_s,
Flgs_eU,
State_CLO,
State_CON,
State_ECO,
State_FIN,
State_INT,
State_NRS,
State_REQ,
State_RSP,
State_RST,
State_TST,
State_URH,
State_URHPRO,
CategoryLabel
```

## 3) Data type of every column

```text
DIntPktAct: float64
Seq: int64
SrcLoss: int64
TotPkts: int64
dMeanPktSz: float64
DstWin: float64
Mean: float64
SIntPktMax: float64
SIntPktIdl: float64
DIntPktMin: float64
DAppBytes: int64
Sport: float64
DstPkts: int64
DstRate: float64
PCRatio: float64
DIntPktMax: float64
DIntPkt: float64
TotAppByte: int64
SynAck: float64
Dport: float64
Rate: float64
SrcRate: float64
SrcLoad: float64
DstTCPBase: float64
sMeanPktSz: float64
SrcBytes: int64
sMinPktSz: float64
sTos: float64
SrcJitter: float64
DstLoss: int64
TotBytes: int64
Loss: int64
SIntPktMin: float64
SrcWin: float64
pLoss: float64
SIntPktAct: float64
SrcPkts: int64
AckDat: float64
Load: float64
Min: float64
DstBytes: int64
Sum: float64
SIntPkt: float64
Max: float64
sTtl: float64
sMaxPktSz: float64
dMaxPktSz: float64
sHops: float64
SrcTCPBase: float64
TcpRtt: float64
dMinPktSz: float64
DstLoad: float64
SAppBytes: int64
Proto_arp: bool
Proto_icmp: bool
Proto_ipv6-icmp: bool
Proto_tcp: bool
Proto_udp: bool
Flgs_e: bool
Flgs_e_*: bool
Flgs_e_d: bool
Flgs_e_g: bool
Flgs_e_r: bool
Flgs_e_s: bool
Flgs_eU: bool
State_CLO: bool
State_CON: bool
State_ECO: bool
State_FIN: bool
State_INT: bool
State_NRS: bool
State_REQ: bool
State_RSP: bool
State_RST: bool
State_TST: bool
State_URH: bool
State_URHPRO: bool
CategoryLabel: string/object
```

## 4) Target / label column

The label column is:

- `CategoryLabel`

This is the multiclass target used for the intrusion detection task.

## 5) Columns containing useful network-flow information

These are the feature columns that represent actual flow behavior, traffic statistics, protocol flags, and connection state. The practical feature set is essentially all non-label columns, especially:

### Core flow and traffic metrics

- `DIntPktAct`
- `Seq`
- `SrcLoss`
- `TotPkts`
- `dMeanPktSz`
- `DstWin`
- `Mean`
- `SIntPktMax`
- `SIntPktIdl`
- `DIntPktMin`
- `DAppBytes`
- `DstPkts`
- `DstRate`
- `PCRatio`
- `DIntPktMax`
- `DIntPkt`
- `TotAppByte`
- `SynAck`
- `Rate`
- `SrcRate`
- `SrcLoad`
- `sMeanPktSz`
- `SrcBytes`
- `sMinPktSz`
- `sTos`
- `SrcJitter`
- `DstLoss`
- `TotBytes`
- `Loss`
- `SIntPktMin`
- `SrcWin`
- `pLoss`
- `SIntPktAct`
- `SrcPkts`
- `AckDat`
- `Load`
- `Min`
- `DstBytes`
- `Sum`
- `SIntPkt`
- `Max`
- `sTtl`
- `sMaxPktSz`
- `dMaxPktSz`
- `sHops`
- `TcpRtt`
- `dMinPktSz`
- `DstLoad`
- `SAppBytes`

### Protocol / connection flags / states

- `Proto_arp`
- `Proto_icmp`
- `Proto_ipv6-icmp`
- `Proto_tcp`
- `Proto_udp`
- `Flgs_e`
- `Flgs_e_*`
- `Flgs_e_d`
- `Flgs_e_g`
- `Flgs_e_r`
- `Flgs_e_s`
- `Flgs_eU`
- `State_CLO`
- `State_CON`
- `State_ECO`
- `State_FIN`
- `State_INT`
- `State_NRS`
- `State_REQ`
- `State_RSP`
- `State_RST`
- `State_TST`
- `State_URH`
- `State_URHPRO`

## 6) Columns not to include in the natural-language representation

The feature columns that are weak candidates for natural-language text because they are identifiers, low-signal, or not semantically useful for text summarization are:

- `Seq` — sequence counter / row-order signal, not a meaningful semantics feature
- `Sport` — source port identifier
- `Dport` — destination port identifier
- `SrcTCPBase` — low-level TCP base value, not semantic text content
- `DstTCPBase` — low-level TCP base value, not semantic text content

The label should not be included as an input feature:

- `CategoryLabel`

These should be excluded from any natural-language representation unless the goal is a very low-level connection trace description:

- `Seq`
- `Sport`
- `Dport`
- `SrcTCPBase`
- `DstTCPBase`

Everything else is a useful traffic/behavior feature and can be described in natural language.

## 7) Missing-value counts for every column

All columns have 0 missing values in all three files.

```text
DIntPktAct: 0
Seq: 0
SrcLoss: 0
TotPkts: 0
dMeanPktSz: 0
DstWin: 0
Mean: 0
SIntPktMax: 0
SIntPktIdl: 0
DIntPktMin: 0
DAppBytes: 0
Sport: 0
DstPkts: 0
DstRate: 0
PCRatio: 0
DIntPktMax: 0
DIntPkt: 0
TotAppByte: 0
SynAck: 0
Dport: 0
Rate: 0
SrcRate: 0
SrcLoad: 0
DstTCPBase: 0
sMeanPktSz: 0
SrcBytes: 0
sMinPktSz: 0
sTos: 0
SrcJitter: 0
DstLoss: 0
TotBytes: 0
Loss: 0
SIntPktMin: 0
SrcWin: 0
pLoss: 0
SIntPktAct: 0
SrcPkts: 0
AckDat: 0
Load: 0
Min: 0
DstBytes: 0
Sum: 0
SIntPkt: 0
Max: 0
sTtl: 0
sMaxPktSz: 0
dMaxPktSz: 0
sHops: 0
SrcTCPBase: 0
TcpRtt: 0
dMinPktSz: 0
DstLoad: 0
SAppBytes: 0
Proto_arp: 0
Proto_icmp: 0
Proto_ipv6-icmp: 0
Proto_tcp: 0
Proto_udp: 0
Flgs_e: 0
Flgs_e_*: 0
Flgs_e_d: 0
Flgs_e_g: 0
Flgs_e_r: 0
Flgs_e_s: 0
Flgs_eU: 0
State_CLO: 0
State_CON: 0
State_ECO: 0
State_FIN: 0
State_INT: 0
State_NRS: 0
State_REQ: 0
State_RSP: 0
State_RST: 0
State_TST: 0
State_URH: 0
State_URHPRO: 0
CategoryLabel: 0
```

## 8) Unique values for categorical columns where practical

### Target labels

```text
CategoryLabel unique values:
- benign
- bruteforce
- dos
- recon
```

### Binary protocol / flag / state columns

These are all binary indicators, and their values are effectively:

```text
{False, True}
```

Columns:

- `Proto_arp`
- `Proto_icmp`
- `Proto_ipv6-icmp`
- `Proto_tcp`
- `Proto_udp`
- `Flgs_e`
- `Flgs_e_*`
- `Flgs_e_d`
- `Flgs_e_g`
- `Flgs_e_r`
- `Flgs_e_s`
- `Flgs_eU`
- `State_CLO`
- `State_CON`
- `State_ECO`
- `State_FIN`
- `State_INT`
- `State_NRS`
- `State_REQ`
- `State_RSP`
- `State_RST`
- `State_TST`
- `State_URH`
- `State_URHPRO`

No other categorical columns beyond the target label are present in a conventional string form.

## 9) Minimum and maximum values for important numeric network fields

Using the training split as the reference feature distribution:

| Column | Min | Max |
|---|---:|---:|
| `TotPkts` | 1.0 | 54,058.0 |
| `TotBytes` | 60.0 | 80,980,442.0 |
| `SrcBytes` | 0.0 | 1,789,044.0 |
| `DstBytes` | 0.0 | 79,191,398.0 |
| `DAppBytes` | 0.0 | 77,274,816.0 |
| `TotAppByte` | 0.0 | 77,275,510.0 |
| `Rate` | 0.0 | 1,500,000.0 |
| `SrcRate` | 0.0 | 500,000.0 |
| `DstRate` | 0.0 | 500,000.0 |
| `SrcLoad` | 0.0 | 352,000,000.0 |
| `DstLoad` | 0.0 | 4,604,000,256.0 |
| `Load` | 0.0 | 4,844,000,256.0 |
| `PCRatio` | 0.0 | 1.0 |
| `pLoss` | 0.0 | 53.333333 |
| `SrcJitter` | 0.0 | 1,262,583.388931 |
| `TcpRtt` | 0.0 | 3.115158 |
| `sTtl` | 0.0 | 255.0 |
| `DstWin` | 0.0 | 16,776,960.0 |
| `SrcWin` | 0.0 | 8,222,720.0 |
| `SrcLoss` | 0.0 | 21.0 |
| `DstLoss` | 0.0 | 2,023.0 |
| `Loss` | 0.0 | 2,023.0 |

## 10) Are the schemas identical across train, validation, and test?

Yes. The schemas are identical across all three files.

Verified conditions:
- same number of columns: 78
- same column names and order
- same dtypes for corresponding columns
- same missing-value pattern (all zeros)

This means the train/validation/test split is consistent and suitable for model evaluation.

## Final assessment

The downstream dataset is clean, structurally consistent, and ready for downstream model input or natural-language feature generation. The most important label is `CategoryLabel`; the useful flow features are the numeric traffic/behavior metrics and the binary protocol/flag/state indicators. The low-signal identifier-like fields to avoid in natural-language text are `Seq`, `Sport`, `Dport`, `SrcTCPBase`, and `DstTCPBase`.
