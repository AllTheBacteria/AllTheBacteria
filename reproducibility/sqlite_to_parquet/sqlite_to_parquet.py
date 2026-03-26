#!/usr/bin/env python3
"""Convert AllTheBacteria metadata SQLite tables to Parquet format."""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

COMPRESSION_CHOICES = ["zstd", "snappy", "gzip", "lz4", "brotli", "none"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert SQLite tables to Parquet files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "sqlite_path",
        type=Path,
        help="path to the input SQLite database",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("metadata/parquet"),
        help="directory for output Parquet files",
    )
    parser.add_argument(
        "-t",
        "--tables",
        nargs="+",
        metavar="TABLE",
        help="convert only these tables (default: all)",
    )
    parser.add_argument(
        "-c",
        "--chunk-size",
        type=int,
        default=100_000,
        help="rows per read/write chunk",
    )
    parser.add_argument(
        "-s",
        "--sample-size",
        type=int,
        default=10_000,
        help="rows sampled for schema type detection",
    )
    parser.add_argument(
        "--compression",
        choices=COMPRESSION_CHOICES,
        default="zstd",
        help="Parquet compression codec",
    )
    return parser.parse_args()


def get_tables(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]


def get_row_count(conn: sqlite3.Connection, table: str) -> int:
    cursor = conn.execute(f'SELECT COUNT(*) FROM "{table}"')
    return cursor.fetchone()[0]


def build_schema(
    conn: sqlite3.Connection, table: str, sample_size: int = 10_000
) -> pa.Schema:
    """Build Arrow schema by sampling data and detecting true numeric columns.

    SQLite allows mixed types in a column (e.g. sra_bytes can be int OR
    semicolon-separated string). We sample rows, read as text, and only
    promote to numeric if ALL non-null values parse as numbers.
    """
    sample = pd.read_sql_query(
        f'SELECT * FROM "{table}" ORDER BY RANDOM() LIMIT {sample_size}',
        conn,
        dtype=str,
    )
    fields = []
    for col in sample.columns:
        series = sample[col].dropna()
        if len(series) == 0:
            fields.append(pa.field(col, pa.large_string()))
            continue
        arrow_type = pa.large_string()
        try:
            pd.to_numeric(series, errors="raise")
            if series.str.contains(r"\.", regex=True).any():
                arrow_type = pa.float64()
            else:
                arrow_type = pa.int64()
        except (ValueError, TypeError):
            pass
        fields.append(pa.field(col, arrow_type))
    return pa.schema(fields)


def convert_table(
    conn: sqlite3.Connection,
    table: str,
    out_dir: Path,
    chunk_size: int = 100_000,
    sample_size: int = 10_000,
    compression: str = "zstd",
) -> dict:
    """Convert a single SQLite table to Parquet, writing in chunks."""
    out_path = out_dir / f"{table}.parquet"
    row_count = get_row_count(conn, table)
    schema = build_schema(conn, table, sample_size)
    num_cols = sum(1 for f in schema if not pa.types.is_large_string(f.type))
    print(
        f"  {table}: {row_count:,} rows, {len(schema)} cols ({num_cols} numeric)",
        flush=True,
    )

    pq_compression = None if compression == "none" else compression
    writer = pq.ParquetWriter(out_path, schema, compression=pq_compression)
    rows_written = 0
    t0 = time.time()

    try:
        for chunk in pd.read_sql_query(
            f'SELECT * FROM "{table}"', conn, chunksize=chunk_size, dtype=str
        ):
            arrays = {}
            for field in schema:
                series = chunk[field.name]
                if pa.types.is_large_string(field.type):
                    arrays[field.name] = pa.array(
                        series.where(series.notna(), None), type=pa.large_string()
                    )
                else:
                    numeric = pd.to_numeric(series, errors="coerce")
                    arrays[field.name] = pa.array(
                        numeric, type=field.type, from_pandas=True
                    )
            arrow_table = pa.table(arrays, schema=schema)
            writer.write_table(arrow_table)
            rows_written += len(chunk)
            print(
                f"    {rows_written:,}/{row_count:,} rows written",
                end="\r",
                flush=True,
            )
        print()
    finally:
        writer.close()

    elapsed = time.time() - t0
    file_size = out_path.stat().st_size
    return {
        "table": table,
        "rows": rows_written,
        "expected": row_count,
        "size_mb": file_size / (1024 * 1024),
        "seconds": elapsed,
    }


def main():
    args = parse_args()

    if not args.sqlite_path.exists():
        print(f"Error: {args.sqlite_path} not found")
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(f"file:{args.sqlite_path}?mode=ro", uri=True)

    all_tables = get_tables(conn)
    if args.tables:
        missing = set(args.tables) - set(all_tables)
        if missing:
            print(f"Error: tables not found in database: {', '.join(sorted(missing))}")
            conn.close()
            sys.exit(1)
        tables = args.tables
    else:
        tables = all_tables

    print(f"Found {len(tables)} tables: {', '.join(tables)}\n")

    results = []
    for table in tables:
        result = convert_table(
            conn,
            table,
            args.output_dir,
            chunk_size=args.chunk_size,
            sample_size=args.sample_size,
            compression=args.compression,
        )
        results.append(result)

    conn.close()

    print("\n--- Summary ---")
    total_size = 0
    all_match = True
    for r in results:
        match = "OK" if r["rows"] == r["expected"] else "MISMATCH"
        if match != "OK":
            all_match = False
        total_size += r["size_mb"]
        print(
            f"  {r['table']:25s} {r['rows']:>10,} rows  "
            f"{r['size_mb']:8.1f} MB  {r['seconds']:6.1f}s  [{match}]"
        )
    print(f"\n  Total Parquet size: {total_size:.1f} MB")

    sqlite_size = args.sqlite_path.stat().st_size / (1024 * 1024)
    print(f"  SQLite size:       {sqlite_size:.1f} MB")
    print(f"  Compression ratio: {sqlite_size / total_size:.1f}x")

    if not all_match:
        print("\nWARNING: Row count mismatch detected!")
        sys.exit(1)

    print("\nAll tables converted successfully.")


if __name__ == "__main__":
    main()
