#!/usr/bin/env python3
import argparse
import csv
import gzip
import hashlib
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, Tuple, List, Optional


def open_maybe_gz(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", newline="")
    return open(path, "rt", newline="")


def md5_file(p: Path) -> str:
    """Return lowercase md5 for file path."""
    # Uses system md5sum for speed (much faster than Python loop for large files)
    try:
        out = subprocess.check_output(["md5sum", str(p)], text=True)
        return out.split()[0].lower()
    except Exception:
        h = hashlib.md5()
        with p.open("rb") as f:
            while True:
                b = f.read(1024 * 1024)
                if not b:
                    break
                h.update(b)
        return h.hexdigest().lower()


_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_name(s: str) -> str:
    s = s.replace("/", "__").replace(" ", "_")
    s = _SAFE_RE.sub("_", s)
    return s.strip("_") or "EMPTY"


def now_ts() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def run_cmd(cmd: List[str], log_path: Path, cwd: Optional[Path] = None) -> int:
    with log_path.open("a") as log:
        log.write(f"\n[{now_ts()}] CMD: {' '.join(cmd)}\n")
        log.flush()
        proc = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=log,
            cwd=str(cwd) if cwd else None,
            text=True,
        )
        return proc.wait()


def extract_tar(tar_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            tf.extractall(dest_dir)
    except tarfile.TarError:
        subprocess.check_call(["tar", "-xf", str(tar_path), "-C", str(dest_dir)])


def find_jsons(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*.json") if p.is_file()])


def move_outputs_filtered(
    tmp_out: Path,
    final_faa_dir: Path,
    final_bakta_log_dir: Path,
    per_tar_log: Path,
    prefix: str,
) -> Tuple[int, int]:
    """
    Keep ONLY:
      - <prefix>.faa  (main FAA)
      - *.log         (bakta_io logs, including reconstruction log)
    Delete everything else (incl hypotheticals.faa, tsv, gbff, etc).
    """
    final_faa_dir.mkdir(parents=True, exist_ok=True)
    final_bakta_log_dir.mkdir(parents=True, exist_ok=True)

    faa_moved = 0
    log_moved = 0

    # Keep ONLY the main faa
    wanted_faa = tmp_out / f"{prefix}.faa"
    if wanted_faa.exists():
        target = final_faa_dir / wanted_faa.name
        if target.exists():
            target = final_faa_dir / (wanted_faa.stem + f"__dup{os.getpid()}.faa")
        shutil.move(str(wanted_faa), str(target))
        faa_moved += 1

    # Keep all *.log produced by bakta_io
    for f in tmp_out.glob("*.log"):
        target = final_bakta_log_dir / f.name
        if target.exists():
            target = final_bakta_log_dir / (f.stem + f"__dup{os.getpid()}.log")
        shutil.move(str(f), str(target))
        log_moved += 1

    # Delete remaining outputs (incl hypotheticals.faa etc)
    for f in tmp_out.glob("*"):
        try:
            if f.is_file():
                f.unlink()
            else:
                shutil.rmtree(f)
        except Exception:
            pass

    with per_tar_log.open("a") as log:
        log.write(f"[INFO] moved faa={faa_moved}, logs={log_moved} (prefix={prefix}) from {tmp_out}\n")

    return faa_moved, log_moved


def write_master(master_log: Path, lock: Lock, msg: str) -> None:
    line = f"[{now_ts()}] {msg}\n"
    with lock:
        with master_log.open("a") as f:
            f.write(line)


def parse_jobs_from_tsv(tsv_path: Path) -> List[Dict]:
    """Read full ATB TSV (header required) -> jobs list (deduped)."""
    with open_maybe_gz(tsv_path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for col in ("filename", "url", "md5"):
            if col not in (reader.fieldnames or []):
                raise SystemExit(f"TSV missing required column: {col}")

        seen = set()
        jobs = []
        for row in reader:
            fname = (row.get("filename") or "").strip()
            url = (row.get("url") or "").strip()
            md5 = (row.get("md5") or "").lower().strip()
            if not fname or not url:
                continue
            key = (fname, url, md5)
            if key in seen:
                continue
            seen.add(key)
            jobs.append({"filename": fname, "url": url, "md5": md5})
    return jobs


def parse_jobs_from_jobs_file(jobs_file: Path) -> List[Dict]:
    """
    Read a simple tab-delimited jobs file WITHOUT header.
    Expected columns:
      filename<TAB>url<TAB>md5
    url and md5 can be blank (we don't need url if tar already exists).
    """
    jobs = []
    seen = set()
    with open_maybe_gz(jobs_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            # Allow 1-3 columns
            fname = parts[0].strip()
            url = parts[1].strip() if len(parts) > 1 else ""
            md5 = parts[2].strip().lower() if len(parts) > 2 else ""
            if not fname:
                continue
            key = (fname, url, md5)
            if key in seen:
                continue
            seen.add(key)
            jobs.append({"filename": fname, "url": url, "md5": md5})
    return jobs


def process_tar(
    job: Dict,
    scratch_root: Path,
    final_root: Path,
    downloads_dir: Path,
    master_log: Path,
    master_lock: Lock,
    verify_md5: bool,
    delete_tar_after: bool,
) -> Dict:
    fname = Path(job["filename"]).name
    expected_md5 = (job.get("md5") or "").lower().strip()

    tarbase = re.sub(r"\.tar\..+$", "", fname)
    per_tar_log = scratch_root / "logs" / "per_tar" / f"{fname}.log"
    per_tar_log.parent.mkdir(parents=True, exist_ok=True)
    per_tar_log.write_text("")

    work_root = scratch_root / "work"
    tar_path = downloads_dir / fname

    # Final outputs go to long-term folder
    final_faa_dir = final_root / "faa"
    final_bakta_log_dir = final_root / "bakta_logs"

    result = {
        "filename": fname,
        "tar_path": str(tar_path),
        "expected_md5": expected_md5,
        "observed_md5": "",
        "md5_match": "SKIP",
        "json_count": 0,
        "faa_moved": 0,
        "logs_moved": 0,
        "status": "OK",
    }

    write_master(master_log, master_lock, f"START {fname} tar={tar_path}")

    tmp_work = None
    try:
        if not tar_path.exists():
            raise FileNotFoundError(f"Tar not found: {tar_path}")

        if verify_md5 and expected_md5:
            obs = md5_file(tar_path)
            result["observed_md5"] = obs
            if obs == expected_md5:
                result["md5_match"] = "YES"
            else:
                result["md5_match"] = "NO"
                result["status"] = "MD5_MISMATCH"
                # Continue anyway (sometimes md5 in TSV can be wrong), but mark status.

        tmp_work = Path(tempfile.mkdtemp(prefix=f"{tarbase}.", dir=str(work_root)))
        extract_tar(tar_path, tmp_work)

        jsons = find_jsons(tmp_work)
        result["json_count"] = len(jsons)

        for j in jsons:
            # Prefix should be the JSON basename without .json
            prefix = Path(j).name
            if prefix.endswith(".json"):
                prefix = prefix[:-5]
            prefix = safe_name(prefix)

            tmp_out = tmp_work / "bakta_tmp" / prefix
            if tmp_out.exists():
                shutil.rmtree(tmp_out)
            tmp_out.parent.mkdir(parents=True, exist_ok=True)

            cmd = ["bakta_io", "--output", str(tmp_out), "--prefix", prefix, str(j)]
            rc = run_cmd(cmd, per_tar_log)
            if rc != 0:
                result["status"] = "BAKTA_IO_FAILED"
                continue

            faa_m, log_m = move_outputs_filtered(tmp_out, final_faa_dir, final_bakta_log_dir, per_tar_log, prefix)
            result["faa_moved"] += faa_m
            result["logs_moved"] += log_m

            if tmp_out.exists():
                shutil.rmtree(tmp_out)

        write_master(
            master_log,
            master_lock,
            f"END   {fname} status={result['status']} md5={result['md5_match']} json={result['json_count']} faa={result['faa_moved']} logs={result['logs_moved']}",
        )
        return result

    except Exception as e:
        result["status"] = f"ERROR:{type(e).__name__}"
        with per_tar_log.open("a") as log:
            log.write(f"[ERROR] {e}\n")
        write_master(master_log, master_lock, f"END   {fname} status={result['status']} err={e}")
        return result

    finally:
        # Cleanup scratch work to control storage
        try:
            if tmp_work and tmp_work.exists():
                shutil.rmtree(tmp_work)
        except Exception:
            pass
        # Optionally delete tar after processing (saves scratch space)
        if delete_tar_after:
            try:
                if tar_path.exists():
                    tar_path.unlink()
            except Exception:
                pass


def write_summary(summary_path: Path, rows: Iterable[Dict]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "filename", "tar_path", "expected_md5", "observed_md5", "md5_match",
        "json_count", "faa_moved", "logs_moved", "status"
    ]
    with summary_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for r in sorted(rows, key=lambda x: x["filename"]):
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser(description="ATB Bakta tar.xz -> JSON -> bakta_io; keep only FAA and logs")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--tsv", type=Path, help="ATB TSV with header (filename,url,md5)")
    src.add_argument("--jobs-file", type=Path, help="Jobs file without header: filename<TAB>url<TAB>md5")

    ap.add_argument("--scratch-out", required=True, type=Path, help="Scratch working directory (logs/work)")
    ap.add_argument("--final-out", required=True, type=Path, help="Final long-term output directory (faa/, bakta_logs/)")
    ap.add_argument("--downloads-dir", required=True, type=Path, help="Directory that already contains downloaded tar files")
    ap.add_argument("--jobs", type=int, default=10, help="Parallel tar files within this process")
    ap.add_argument("--verify-md5", action="store_true", help="Verify md5 for each tar against provided md5")
    ap.add_argument("--delete-tar-after", action="store_true", help="Delete tar from downloads-dir after processing")

    args = ap.parse_args()

    scratch = args.scratch_out
    final = args.final_out
    downloads_dir = args.downloads_dir

    (scratch / "report").mkdir(parents=True, exist_ok=True)
    (scratch / "logs" / "per_tar").mkdir(parents=True, exist_ok=True)
    (scratch / "work").mkdir(parents=True, exist_ok=True)

    # Final dirs
    (final / "faa").mkdir(parents=True, exist_ok=True)
    (final / "bakta_logs").mkdir(parents=True, exist_ok=True)
    (final / "report").mkdir(parents=True, exist_ok=True)

    master_log = scratch / "logs" / f"master.{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    master_lock = Lock()

    src_label = str(args.tsv) if args.tsv else str(args.jobs_file)
    write_master(master_log, master_lock, f"RUN start src={src_label} scratch={scratch} final={final} downloads={downloads_dir} jobs={args.jobs} host={os.uname().nodename}")
    write_master(master_log, master_lock, f"ENV python={os.sys.version.split()[0]} cwd={os.getcwd()} verify_md5={args.verify_md5} delete_tar_after={args.delete_tar_after}")

    if args.tsv:
        jobs = parse_jobs_from_tsv(args.tsv)
    else:
        jobs = parse_jobs_from_jobs_file(args.jobs_file)

    write_master(master_log, master_lock, f"RUN jobs_total={len(jobs)}")

    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = [
            ex.submit(
                process_tar,
                j,
                scratch,
                final,
                downloads_dir,
                master_log,
                master_lock,
                args.verify_md5,
                args.delete_tar_after,
            )
            for j in jobs
        ]
        for fut in as_completed(futs):
            results.append(fut.result())

    summary_path = scratch / "report" / "summary.tsv"
    write_summary(summary_path, results)

    # Copy summary to final report (append task ID if running as array)
    task_id = os.environ.get("SLURM_ARRAY_TASK_ID")
    final_summary = final / "report" / (f"summary.task_{int(task_id):06d}.tsv" if task_id and task_id.isdigit() else "summary.tsv")
    try:
        shutil.copy2(summary_path, final_summary)
    except Exception:
        pass

    ok = sum(1 for r in results if r["status"] == "OK")
    mism = sum(1 for r in results if r["status"] == "MD5_MISMATCH")
    err = len(results) - ok - mism
    write_master(master_log, master_lock, f"RUN end rows={len(results)} ok={ok} md5_mismatch={mism} other_err={err}")
    print(f"[DONE] Scratch summary: {summary_path}")
    print(f"[DONE] Master log: {master_log}")
    print(f"[DONE] Final out: {final}")


if __name__ == "__main__":
    main()
