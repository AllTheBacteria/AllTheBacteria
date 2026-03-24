#!/usr/bin/env python3
"""
build_hash_sequence_table.py

Build a comprehensive hash-to-sequence mapping table from FAA files and report statistics.

Inputs
------
- samples_with_ids.tsv: Sample metadata with columns: SampleID, Sample, SpeciesID, Species, HQ
- faa_dir: Directory containing .bakta.faa files (or .faa files)

Outputs
-------
1. hash_to_sequence.tsv: Hash ID and corresponding amino acid sequence
2. records_per_faa.tsv: Number of protein records per FAA file
3. records_per_species.tsv: Total protein records per species

Features
--------
- Uses same blake2b_128 hashing as WhatsGNU_ATB.py
- Deduplicates sequences (same hash = same sequence)
- Reports both per-file and per-species statistics

Dependencies
------------
None (pure Python stdlib)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterator, List, Set, Tuple


HEADER_RE = re.compile(r"^>(\S+)\s*(.*)$")


# -----------------------------
# FASTA parsing
# -----------------------------
def parse_faa(path: Path) -> Iterator[Tuple[str, str, str]]:
    """
    Yield (protein_id, aa_sequence, function_string) from a .faa.
    - protein_id: first token after '>'
    - function_string: rest of header line after first whitespace
    """
    pid = ""
    func = ""
    seq_lines: List[str] = []
    with path.open("rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith(">"):
                if pid and seq_lines:
                    yield (pid, "".join(seq_lines), func)
                    seq_lines = []
                m = HEADER_RE.match(line)
                if m:
                    pid = m.group(1)
                    func = (m.group(2) or "").strip()
                else:
                    pid = line[1:].split()[0] if line[1:].strip() else ""
                    func = ""
            else:
                seq_lines.append(line.strip())
        if pid and seq_lines:
            yield (pid, "".join(seq_lines), func)


# -----------------------------
# Logging setup
# -----------------------------
def setup_logging(log_file: Path) -> None:
    """Setup logging to both file and console."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# -----------------------------
# Hashing (same as WhatsGNU_ATB)
# -----------------------------
def hash_allele_128(aa_seq: str) -> bytes:
    """Return blake2b_128 hash as raw bytes (same as WhatsGNU_ATB.py)."""
    return hashlib.blake2b(aa_seq.encode("utf-8"), digest_size=16).digest()

def hash_to_hex(hash_bytes: bytes) -> str:
    """Convert hash bytes to hex string for display."""
    return hash_bytes.hex()


# -----------------------------
# Sample metadata loading
# -----------------------------
def load_samples_metadata(tsv_path: Path) -> List[Dict[str, str]]:
    """
    Load samples_with_ids.tsv.
    Returns list of dicts with keys: SampleID, Sample, SpeciesID, Species, HQ
    """
    samples = []
    with tsv_path.open("rt", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            samples.append(row)
    return samples


# -----------------------------
# Main processing
# -----------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build hash-to-sequence table and compute protein record statistics"
    )
    ap.add_argument("--samples_tsv", required=True, 
                    help="Path to samples_with_ids.tsv")
    ap.add_argument("--faa_dir", required=True, 
                    help="Directory containing .bakta.faa (or .faa) files")
    ap.add_argument("--out_dir", required=True, 
                    help="Output directory for generated files")
    ap.add_argument("--faa_suffix", default=".bakta.faa", 
                    help="FAA file suffix (default: .bakta.faa)")
    ap.add_argument("--log_file", default=None,
                    help="Path to log file (default: <out_dir>/build_hash_table.log)")
    ap.add_argument("--memory_efficient", action="store_true",
                    help="Write hash table incrementally to reduce memory usage (slower but uses less RAM)")
    ap.add_argument("--checkpoint_interval", type=int, default=100,
                    help="Save progress every N samples (default: 100)")
    ap.add_argument("--resume", action="store_true",
                    help="Resume from previous checkpoint if available")
    
    args = ap.parse_args()
    
    samples_tsv = Path(args.samples_tsv)
    faa_dir = Path(args.faa_dir)
    out_dir = Path(args.out_dir)
    faa_suffix = args.faa_suffix
    
    # Setup logging
    if args.log_file:
        log_file = Path(args.log_file)
    else:
        log_file = out_dir / "build_hash_table.log"
    
    setup_logging(log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("Starting hash-to-sequence table builder")
    logger.info("="*60)
    logger.info(f"Samples TSV: {samples_tsv}")
    logger.info(f"FAA directory: {faa_dir}")
    logger.info(f"Output directory: {out_dir}")
    logger.info(f"FAA suffix: {faa_suffix}")
    logger.info(f"Memory efficient mode: {args.memory_efficient}")
    logger.info(f"Log file: {log_file}")
    
    if not samples_tsv.exists():
        logger.error(f"samples_with_ids.tsv not found at {samples_tsv}")
        return 2
    
    if not faa_dir.exists():
        logger.error(f"FAA directory not found at {faa_dir}")
        return 2
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load sample metadata
    logger.info("Loading sample metadata...")
    samples = load_samples_metadata(samples_tsv)
    logger.info(f"Loaded {len(samples)} samples")
    
    # Checkpoint file
    checkpoint_file = out_dir / "checkpoint.txt"
    processed_samples_set = set()
    
    if args.resume and checkpoint_file.exists():
        logger.info(f"Resume mode: loading checkpoint from {checkpoint_file}")
        with checkpoint_file.open("rt") as f:
            for line in f:
                sample_name = line.strip()
                if sample_name:
                    processed_samples_set.add(sample_name)
        logger.info(f"Found {len(processed_samples_set)} already-processed samples")
    
    # Data structures
    hash_to_seq: Dict[bytes, str] = {}  # hash_bytes -> aa_sequence (deduplicated)
    records_per_faa: Dict[str, int] = {}  # sample_name -> record_count
    records_per_species: Dict[str, int] = defaultdict(int)  # species_id -> total_records
    species_names: Dict[str, str] = {}  # species_id -> species_name
    
    # Process each sample
    missing_files = []
    processed_count = 0
    total_samples = len(samples)
    
    logger.info(f"Processing {total_samples} FAA files...")
    
    start_time = time.time()
    last_report_time = start_time
    
    # Define progress milestones: 10, 1K, 10K, 100K, 200K, 400K, 600K, 800K, then every 200K
    milestones = [10, 1000, 10000, 100000, 200000, 400000, 600000, 800000]
    for i in range(1000000, 2800000, 200000):
        milestones.append(i)
    milestones_set = set(milestones)  # Convert to set for O(1) lookup
    
    # Open hash table file in memory-efficient mode if requested
    hash_seq_file = out_dir / "hash_to_sequence.tsv"
    hash_file_handle = None
    checkpoint_handle = None
    faa_stats_handle = None
    
    try:
        if args.memory_efficient:
            logger.info("Memory-efficient mode: writing hash table incrementally")
            # Open in append mode if resuming
            mode = "at" if (args.resume and hash_seq_file.exists()) else "wt"
            hash_file_handle = hash_seq_file.open(mode, encoding="utf-8")
            if mode == "wt":
                hash_file_handle.write("hash_id\taa_sequence\n")
        
        # Open per-FAA statistics file for incremental writing
        faa_stats_file = out_dir / "records_per_faa.tsv"
        mode = "at" if (args.resume and faa_stats_file.exists()) else "wt"
        faa_stats_handle = faa_stats_file.open(mode, encoding="utf-8", buffering=1)  # Line buffered
        if mode == "wt":
            faa_stats_handle.write("sample_name\trecord_count\n")
        
        # Open checkpoint file for writing
        checkpoint_handle = checkpoint_file.open("at", encoding="utf-8", buffering=1)  # Line buffered
        
        for sample in samples:
            sample_name = sample["Sample"]
            species_id = sample["SpeciesID"]
            species_name = sample["Species"]
            
            # Skip if already processed
            if sample_name in processed_samples_set:
                logger.debug(f"Skipping already-processed sample: {sample_name}")
                continue
            
            # Track species name
            species_names[species_id] = species_name
            
            # Find FAA file
            faa_file = faa_dir / f"{sample_name}{faa_suffix}"
            
            # Try fallback to .faa if .bakta.faa not found
            if not faa_file.exists() and faa_suffix == ".bakta.faa":
                faa_file = faa_dir / f"{sample_name}.faa"
            
            if not faa_file.exists():
                missing_files.append(sample_name)
                logger.warning(f"FAA file not found: {sample_name}")
                continue
            
            # Process FAA
            processed_count += 1
            record_count = 0
            
            # Smart progress logging at specific milestones
            if processed_count in milestones_set:
                current_time = time.time()
                elapsed = current_time - start_time
                rate = processed_count / elapsed if elapsed > 0 else 0
                remaining = total_samples - processed_count
                eta_seconds = remaining / rate if rate > 0 else 0
                logger.info("=" * 60)
                logger.info(f"MILESTONE: {processed_count:,} / {total_samples:,} samples processed")
                logger.info(f"  Elapsed: {elapsed/3600:.2f}h | Rate: {rate*3600:.1f}/hr | ETA: {eta_seconds/3600:.2f}h")
                logger.info(f"  Unique hashes: {len(hash_to_seq):,}")
                logger.info(f"  Processing: {sample_name}")
                logger.info("=" * 60)
            elif processed_count % 10000 == 0:
                # Brief log every 10K samples (not milestones)
                logger.info(f"[{processed_count:,}/{total_samples:,}] {sample_name}")
            
            for pid, aa_seq, func in parse_faa(faa_file):
                if not aa_seq:
                    continue
                
                record_count += 1
                
                # Compute hash (returns bytes, same as WhatsGNU_ATB)
                hash_bytes = hash_allele_128(aa_seq)
                
                # Store hash-to-sequence mapping (deduplicated)
                if hash_bytes not in hash_to_seq:
                    if args.memory_efficient:
                        # Write immediately and don't store in memory
                        hash_hex = hash_to_hex(hash_bytes)
                        hash_file_handle.write(f"{hash_hex}\t{aa_seq}\n")  # type: ignore
                        hash_to_seq[hash_bytes] = ""  # Mark as seen but don't store sequence
                    else:
                        # Store in memory
                        hash_to_seq[hash_bytes] = aa_seq
            
            # Record statistics
            records_per_faa[sample_name] = record_count
            records_per_species[species_id] += record_count
            
            # Write per-FAA statistic immediately
            faa_stats_handle.write(f"{sample_name}\t{record_count}\n")  # type: ignore
            
            # Write checkpoint
            checkpoint_handle.write(f"{sample_name}\n")  # type: ignore
            
            # Flush checkpoint and stats periodically (silent - milestones handle logging)
            if processed_count % args.checkpoint_interval == 0:
                checkpoint_handle.flush()  # type: ignore
                faa_stats_handle.flush()  # type: ignore
                if hash_file_handle:
                    hash_file_handle.flush()
    
    except Exception as e:
        logger.error(f"ERROR during processing: {type(e).__name__}: {e}")
        logger.exception("Full traceback:")
        # Continue to finally block to close files
    
    finally:
        # Always close file handles, even if there's an error
        logger.info("Closing file handles...")
        if checkpoint_handle:
            checkpoint_handle.close()
            logger.info("Closed checkpoint file")
        
        if faa_stats_handle:
            faa_stats_handle.close()
            logger.info(f"Closed per-FAA statistics file")
        
        if hash_file_handle:
            hash_file_handle.close()
            logger.info(f"Closed hash table file")
    
    if missing_files:
        logger.warning(f"{len(missing_files)} FAA files not found")
        logger.debug("Missing files: " + ", ".join(missing_files[:20]))
    
    # Write hash-to-sequence table (skip if memory-efficient mode already wrote it)
    if not args.memory_efficient:
        logger.info("Writing hash-to-sequence table...")
        with hash_seq_file.open("wt", encoding="utf-8") as f:
            f.write("hash_id\taa_sequence\n")
            # Sort by hex representation for consistent output
            for hash_bytes in sorted(hash_to_seq.keys()):
                hash_hex = hash_to_hex(hash_bytes)
                aa_seq = hash_to_seq[hash_bytes]
                f.write(f"{hash_hex}\t{aa_seq}\n")
        logger.info(f"Wrote {len(hash_to_seq)} unique sequences to {hash_seq_file}")
    else:
        logger.info(f"Hash table already written (memory-efficient mode): {len(hash_to_seq)} unique sequences")
    
    # Write records per species (only at the end)
    species_stats_file = out_dir / "records_per_species.tsv"
    logger.info("Writing records per species...")
    with species_stats_file.open("wt", encoding="utf-8") as f:
        f.write("species_id\tspecies_name\ttotal_records\n")
        for species_id in sorted(records_per_species.keys(), key=int):
            total_records = records_per_species[species_id]
            sp_name = species_names.get(species_id, "Unknown")
            f.write(f"{species_id}\t{sp_name}\t{total_records}\n")
    logger.info(f"Wrote statistics for {len(records_per_species)} species to {species_stats_file}")
    
    # Summary
    logger.info("="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    total_elapsed = time.time() - start_time
    logger.info(f"Total elapsed time: {total_elapsed/3600:.2f} hours ({total_elapsed/60:.1f} minutes)")
    logger.info(f"Total unique sequences (hashes): {len(hash_to_seq):,}")
    logger.info(f"Total FAA files processed: {len(records_per_faa):,}")
    logger.info(f"Total species: {len(records_per_species):,}")
    total_proteins = sum(records_per_faa.values())
    logger.info(f"Total protein records: {total_proteins:,}")
    if total_elapsed > 0:
        logger.info(f"Processing rate: {len(records_per_faa)/total_elapsed*3600:.1f} samples/hour")
    
    logger.info("\nTop 5 species by record count:")
    top_species = sorted(records_per_species.items(), key=lambda x: x[1], reverse=True)[:5]
    for species_id, count in top_species:
        sp_name = species_names.get(species_id, "Unknown")
        logger.info(f"  {species_id}: {sp_name} - {count:,} records")
    
    logger.info("="*60)
    logger.info("Processing complete!")
    logger.info("="*60)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
