# SQLite to Parquet converter

Converts AllTheBacteria metadata SQLite tables to Parquet format for faster
analytical queries and reduced storage.

## Requirements

- Python 3.10+
- pandas
- pyarrow

## Usage

```
python sqlite_to_parquet.py <sqlite_path> [options]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `sqlite_path` | (required) | Path to the input SQLite database |
| `-o`, `--output-dir` | `metadata/parquet` | Directory for output Parquet files |
| `-t`, `--tables` | all | Convert only specific tables |
| `-c`, `--chunk-size` | `100000` | Rows per read/write chunk |
| `-s`, `--sample-size` | `10000` | Rows sampled for schema type detection |
| `--compression` | `zstd` | Parquet compression: zstd, snappy, gzip, lz4, brotli, none |

### Examples

Convert all tables with default settings:

```bash
python sqlite_to_parquet.py metadata/atb.metadata.202505.sqlite
```

Convert specific tables with snappy compression:

```bash
python sqlite_to_parquet.py metadata/atb.metadata.202505.sqlite \
    -t biosample sra \
    --compression snappy
```

## How it works

1. Samples rows from each table to detect column types (integer, float, or
   string). SQLite allows mixed types in a single column, so sampling avoids
   incorrect type inference.
2. Reads data in chunks to keep memory usage bounded.
3. Writes Parquet files with the chosen compression codec (zstd by default).
4. Verifies row counts match between source and output.
