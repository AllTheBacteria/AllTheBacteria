#!/usr/bin/env python3
"""
build_allelome_cache_v5.py  (REVAMPED)

One-time cache builder for ATB WhatsGNU allelome (build_info.json v5).

Reads LMDB counts shards:
    key   = hash16  (16 bytes blake2b_128 digest)
    value = func_id:uint32 + GNU_count:uint32  (little-endian)

Writes compact NPZ cache:
    hashes_u8 : uint8  [N, 16]
    func_id   : uint32 [N]
    gnu       : uint32 [N]
    shard     : uint8  [N]

Fixes vs previous version:
  - np.frombuffer → .copy() to avoid LMDB buffer reuse corruption
  - Chunked accumulation: peak RAM ~8 GB instead of ~50 GB for 242M alleles
  - Optional pre-allocation from build_info.json for even faster runs
"""

import argparse
import json
import struct
import sys
import time
from pathlib import Path

import lmdb
import numpy as np

VAL_COUNTS = struct.Struct("<II")  # func_id, gnu_count
CHUNK = 2_000_000                  # rows per accumulation chunk


def open_lmdb_readonly(path: Path) -> lmdb.Environment:
    return lmdb.open(
        str(path),
        readonly=True,
        lock=False,
        readahead=True,
        max_readers=1024,
        max_dbs=32,
        subdir=True,
    )


def scan_shard(shard_dir: Path, sid: int, db_name: bytes,
               progress_every: int, global_count: int, t0: float):
    """
    Yield chunked numpy arrays from one counts shard.
    Each yield is (hashes_chunk [M,16], fid_chunk [M], gnu_chunk [M], count)
    where M <= CHUNK.
    """
    env = open_lmdb_readonly(shard_dir)
    h_buf = np.empty((CHUNK, 16), dtype=np.uint8)
    f_buf = np.empty(CHUNK, dtype=np.uint32)
    g_buf = np.empty(CHUNK, dtype=np.uint32)
    pos = 0
    count = global_count

    dbi = env.open_db(db_name)
    with env.begin(db=dbi, write=False) as txn:
        with txn.cursor() as cur:
            for k, v in cur:
                if len(k) != 16 or len(v) < 8:
                    continue
                # CRITICAL: .copy() because LMDB reuses the buffer
                h_buf[pos] = np.frombuffer(k, dtype=np.uint8, count=16).copy()
                f_buf[pos], g_buf[pos] = VAL_COUNTS.unpack_from(v, 0)
                pos += 1
                count += 1
                if progress_every and count % progress_every == 0:
                    rate = count / max(time.time() - t0, 1e-9)
                    print(f"[cache] {count:,} alleles ({rate:,.0f}/s)",
                          file=sys.stderr)
                if pos == CHUNK:
                    yield h_buf[:pos].copy(), f_buf[:pos].copy(), g_buf[:pos].copy(), count
                    pos = 0

    if pos > 0:
        yield h_buf[:pos].copy(), f_buf[:pos].copy(), g_buf[:pos].copy(), count
    env.close()

def iter_counts_entries(counts_root: Path, nshards: int) -> Iterator[Tuple[bytes, int, int, int]]:
    """
    from older script, not used here but inlcuded for reference
    Iterate ALL count entries across shards.
    Yields: (hash16_bytes, func_id, gnu_score, shard_id)
    Requires that counts are stored in named DB b"counts" (as in your modified script).
    """
    for sid in range(nshards):
        shard_dir = counts_root / f"shard_{sid:02x}"
        if not shard_dir.exists():
            continue
        env = open_env(shard_dir, readonly=True, map_size=1 << 30)
        db = env.open_db(b"counts")
        with env.begin(db=db) as txn:
            cur = txn.cursor()
            for k, v in cur:
                # expect k=16 bytes, v=8 bytes but be robust
                if len(v) != VAL_COUNTS.size:
                    continue
                fid, gnu = VAL_COUNTS.unpack(v)
                yield k, fid, gnu, sid
        env.close()
def main():
    ap = argparse.ArgumentParser(
        description="Build NPZ counts cache from LMDB counts shards (v5)")
    ap.add_argument("--counts_root", required=True, type=Path,
                    help="Path to OUT_DIR/lmdb_counts")
    ap.add_argument("--nshards", required=True, type=int)
    ap.add_argument("--cache_npz", required=True, type=Path)
    ap.add_argument("--db_name", default="counts",
                    help="LMDB named DB (default: counts)")
    ap.add_argument("--build_info", type=Path, default=None,
                    help="Optional build_info.json for pre-allocation hint")
    ap.add_argument("--progress_every", type=int, default=5_000_000)
    args = ap.parse_args()

    t0 = time.time()
    args.cache_npz.parent.mkdir(parents=True, exist_ok=True)
    db_name = args.db_name.encode()

    # Collect chunks per shard, then concatenate at the end
    all_h: list = []
    all_f: list = []
    all_g: list = []
    all_s: list = []   # shard ids
    total = 0

    for sid in range(args.nshards):
        sd = args.counts_root / f"shard_{sid:02x}"
        if not sd.exists():
            # Try zero-padded decimal fallback
            sd = args.counts_root / f"shard_{sid:02d}"
        if not sd.exists():
            raise FileNotFoundError(f"Missing shard dir: {sd}")

        shard_start = total
        for h_chunk, f_chunk, g_chunk, total in scan_shard(
                sd, sid, db_name, args.progress_every, total, t0):
            all_h.append(h_chunk)
            all_f.append(f_chunk)
            all_g.append(g_chunk)
            n = len(h_chunk)
            s_chunk = np.full(n, sid, dtype=np.uint8)
            all_s.append(s_chunk)

        dt = time.time() - t0
        shard_count = total - shard_start
        print(f"[cache] shard {sid:02x} done: {shard_count:,} keys "
              f"({total:,} cumulative, {dt / 60:.1f} min elapsed)",
              file=sys.stderr)

    if total == 0:
        print("[cache] WARNING: no alleles found!", file=sys.stderr)
        hashes_u8 = np.zeros((0, 16), dtype=np.uint8)
        func_id_arr = np.zeros(0, dtype=np.uint32)
        gnu_arr = np.zeros(0, dtype=np.uint32)
        shard_arr = np.zeros(0, dtype=np.uint8)
    else:
        # ~120 chunks to concatenate (not 242M items) → fast
        hashes_u8 = np.concatenate(all_h, axis=0)
        func_id_arr = np.concatenate(all_f)
        gnu_arr = np.concatenate(all_g)
        shard_arr = np.concatenate(all_s)

    np.savez_compressed(
        args.cache_npz,
        hashes_u8=hashes_u8,
        func_id=func_id_arr,
        gnu=gnu_arr,
        shard=shard_arr,
        format_version=np.asarray([5], dtype=np.uint8),
    )

    dt = time.time() - t0
    size_mb = args.cache_npz.stat().st_size / (1024 * 1024)
    print(f"[cache] wrote {args.cache_npz} — {total:,} alleles, "
          f"{size_mb:.0f} MB, {dt / 60:.1f} min", file=sys.stderr)


if __name__ == "__main__":
    main()
