# orders-5k: copy the registry into the order table, or join on the MIC?

A small, runnable comparison. 5,000 fictional orders reference 50 venues.
There are two ways to give each order its venue's name, country, city and
status:

- **wide:** copy those registry fields into every order row;
- **narrow:** keep only the MIC on the order and join to
  `iso10383.parquet` when you need the details.

`generate_facts.py` builds both tables; `analyze.py` measures what each
costs and what happens when the registry changes.

## What is real and what is synthetic

| | Real | Synthetic |
|---|---|---|
| The 50 venues' MICs | yes, active operating MICs from this repository's `iso10383.json` | |
| Their names, countries, cities, statuses, websites, acronyms | yes, copied from the registry as it stands | |
| Which 50 venues | | picked at random with a fixed seed (10383); not the largest, not a recommendation |
| The 5,000 orders: ids, sides, quantities, prices, timestamps | | all of it, from a seeded random generator |
| Which venue an order went to | | random, weighted so a few venues get most orders |
| The registry change in part 3 of the analysis | | simulated on an in-memory copy; no file is modified |

Nothing here is trading data, and nothing says anything about how any
venue actually trades. The only things you can trust are the registry
fields. A null in a registry field (many venues have no acronym or no
LEI, for instance) is a real null, see [`docs/ENRICHMENT.md`](../../docs/ENRICHMENT.md).

## Run it

From this directory, with Python 3.10 or later:

```bash
pip install -r requirements.txt
python3 generate_facts.py
python3 analyze.py
```

The tables are written to `iso10383-orders-5k/` in your system temp
directory, so the checkout stays clean; pass `--out DIR` to
`generate_facts.py` and `--data DIR` to `analyze.py` to put them elsewhere.
The generator is deterministic: the same registry and the same pyarrow
version give byte-identical files.

`requirements.txt` pins `pyarrow==25.0.1`, the version the registry's
`iso10383.parquet` is built with (`constraints.txt` at the repository
root). The analysis only reads that file.

## What it printed

On registry snapshot 2026-09-23 with pyarrow 25.0.1 (your numbers will
differ after a refresh, and slightly with another pyarrow):

```
1. Storage
                    parquet   in memory    as CSV
   narrow           108,060     234,333   295,441
   wide             129,415     712,533   721,371
   copying adds 21,355 bytes of Parquet and 478,200 bytes in memory (95 per order)
   the join's other side, iso10383.parquet, is 202,257 bytes, shared by every table
   narrow + the whole registry file: 310,317 bytes, more than wide (129,415) in Parquet at this row count

2. Join on mic
   5,000 of 5,000 orders found their MIC in the registry
   joined fields equal the copied fields: True

3. A registry change (simulated; iso10383.parquet is not touched)
   ATLN: market_name changes; BAMX: status becomes EXPIRED
   registry rows to change:        2
   order rows the join corrects:   1,708 of 5,000, with no write to the orders
   order rows the copy leaves stale: 1,708
```

## How to read it

- **Storage in Parquet is not the argument at this size.** Parquet's
  dictionary encoding absorbs the repeated strings, so the copy adds only
  about 20% to the file. At 5,000 rows the registry file itself is larger
  than that saving. Do not choose the join to save disk.
- **Memory and text formats are.** Loaded into memory the wide table is
  about 3 times the narrow one; as CSV about 2.4 times. That is what you
  pay when the order table is read into a dataframe, exported, or sent
  over a wire.
- **Correctness is the real difference.** On the day the copy is made the
  two layouts agree (part 2). After that the registry moves: SWIFT renames
  a venue, a MIC expires. The join picks the change up with no write to the
  orders. The copy keeps the old value in every affected row until
  someone finds and rewrites them. Here two registry rows touch a third of
  the orders, because a few venues carry most of the volume.
- **A copy is right when you want the value as it was.** If an audit
  needs a venue's name as of the day of the order, a frozen copy is
  correct, and the narrow layout is wrong for that purpose. In that case
  record the registry's `source_snapshot` and version with the order
  rather than copying whole fields.

## What this does not show

It does not benchmark join speed (5,000 rows is too small to mean
anything), does not model late-arriving or corrected orders, and the
venue weights are arbitrary. It also uses only `iso10383.parquet`; the JSON,
CSV and SQL exports carry the same rows.
