"""CLI entry point for KooDynaDiag."""

import argparse
import os
import sys
from pathlib import Path

from koodyna import __version__


def _open_in_browser(html_path: Path, log):
    """Open HTML report in browser — Windows Chrome-friendly.

    Strategy (Windows):
      1. Try Chrome directly via well-known install paths
      2. Fall back to webbrowser.open() with file:// URI
    Other OS: webbrowser.open() with file:// URI only.
    """
    import webbrowser

    file_uri = html_path.resolve().as_uri()  # file:///C:/… or file:///home/…

    if sys.platform == "win32":
        import subprocess
        # 일반적인 Chrome 설치 경로 후보
        chrome_candidates = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
        # LOCALAPPDATA env 기반 경로도 확인
        import os
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            chrome_candidates.append(Path(local_app) / "Google" / "Chrome" / "Application" / "chrome.exe")

        for chrome in chrome_candidates:
            if chrome.exists():
                try:
                    subprocess.Popen([str(chrome), file_uri])
                    log(f"Chrome으로 열었습니다: {file_uri}")
                    return
                except OSError:
                    continue

        # Chrome 없으면 기본 브라우저로 폴백
        log("Chrome을 찾지 못하여 기본 브라우저로 열겠습니다.")

    # 기본 브라우저 (macOS / Linux / Windows 폴백)
    opened = webbrowser.open(file_uri)
    if opened:
        log(f"브라우저로 열었습니다: {file_uri}")
    else:
        log(f"브라우저 자동 열기 실패. 수동으로 열어주세요: {html_path}")


def _analyze_single(args: tuple) -> dict:
    """Worker function for parallel batch analysis. Runs in subprocess."""
    folder, gen_html = args
    from pathlib import Path
    result = {"dir": str(folder), "status": "UNKNOWN", "findings": 0, "error": None}
    try:
        from koodyna.analyzer import Analyzer
        from koodyna.report.json_report import write_json_report, report_to_dict
        from koodyna.report.html_report import write_html_report

        a = Analyzer(Path(folder))
        r = a.run()
        result["status"] = r.termination.status.value
        result["findings"] = len(r.findings)
        crits = sum(1 for f in r.findings if f.severity.value == "CRITICAL")
        result["critical"] = crits

        # Save JSON
        json_path = Path(folder) / "koodyna_report.json"
        write_json_report(r, json_path)

        # Save HTML
        if gen_html:
            html_path = Path(folder) / "koodyna_report.html"
            write_html_report(r, html_path)

    except Exception as e:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(e)
    return result


def _run_parallel_batch(base_dir: Path, keyword: str, np_count: int, no_html: bool):
    """Find subdirectories matching keyword with d3hsp, analyze in parallel."""
    import multiprocessing
    import time

    if not base_dir.is_dir():
        print(f"Error: '{base_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Find matching directories
    targets = []
    for root, dirs, files in os.walk(base_dir):
        p = Path(root)
        if keyword.lower() in p.name.lower():
            if (p / "d3hsp").exists() or (p / "mes0000").exists():
                targets.append(p)

    if not targets:
        print(f"No directories found matching '{keyword}' with d3hsp/mes0000 in '{base_dir}'")
        sys.exit(0)

    targets.sort()
    gen_html = not no_html

    print(f"=" * 60)
    print(f" KooDynaDiag Parallel Batch Analysis")
    print(f"=" * 60)
    print(f"  Base directory : {base_dir}")
    print(f"  Keyword filter : '{keyword}'")
    print(f"  Matched folders: {len(targets)}")
    print(f"  Parallel procs : {np_count}")
    print(f"  HTML reports   : {'Yes' if gen_html else 'No'}")
    print(f"=" * 60)
    print()

    start_time = time.time()

    work_items = [(str(t), gen_html) for t in targets]

    with multiprocessing.Pool(processes=np_count) as pool:
        results = []
        for i, result in enumerate(pool.imap_unordered(_analyze_single, work_items)):
            i += 1
            name = Path(result["dir"]).name
            status = result["status"]
            findings = result["findings"]
            crits = result.get("critical", 0)
            err = result.get("error", "")

            if err:
                print(f"  [{i:>4d}/{len(targets)}] ERROR     {name}: {err}")
            else:
                crit_mark = f" ★{crits}CRIT" if crits > 0 else ""
                print(f"  [{i:>4d}/{len(targets)}] {status:<12s} findings={findings:>2d}{crit_mark}  {name}")
            results.append(result)

    elapsed = time.time() - start_time

    # Summary
    print()
    print(f"=" * 60)
    from collections import Counter
    status_counts = Counter(r["status"] for r in results)
    for s, c in status_counts.most_common():
        print(f"  {s}: {c}")
    print(f"  Total: {len(results)} cases in {elapsed:.1f}s ({elapsed/len(results):.1f}s/case)")
    print(f"=" * 60)


def _run_gui_mode():
    """GUI mode: folder picker → progress window → browser open."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext
    except ImportError:
        print(
            "GUI 모드를 사용하려면 tkinter가 필요합니다.\n"
            "CLI 모드: koodyna <결과폴더경로>",
            file=sys.stderr,
        )
        sys.exit(1)

    import threading

    root = tk.Tk()
    root.withdraw()

    # 1) 폴더 선택
    folder = filedialog.askdirectory(title="LS-DYNA 결과 폴더 선택")
    if not folder:
        root.destroy()
        return

    result_dir = Path(folder)

    # 2) 검증
    d3hsp = result_dir / "d3hsp"
    mes0000 = result_dir / "mes0000"
    if not d3hsp.exists() and not mes0000.exists():
        messagebox.showerror(
            "오류",
            f"'{result_dir}'에 d3hsp 또는 mes0000이 없습니다.\n"
            "LS-DYNA 결과 폴더가 맞는지 확인하세요.",
        )
        root.destroy()
        return

    # 3) 진행 창 생성
    root.deiconify()
    root.title("KooDynaDiag")
    root.geometry("720x500")
    root.resizable(True, True)

    text_area = scrolledtext.ScrolledText(
        root, wrap=tk.WORD, font=("Consolas", 10),
        bg="#1a1b26", fg="#c0caf5", insertbackground="#c0caf5",
    )
    text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
    text_area.configure(state=tk.DISABLED)

    btn_frame = tk.Frame(root)
    btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    close_btn = tk.Button(
        btn_frame, text="닫기", command=root.destroy, state=tk.DISABLED,
    )
    close_btn.pack(side=tk.RIGHT)

    def log(msg):
        """Thread-safe text append."""
        def _append():
            text_area.configure(state=tk.NORMAL)
            text_area.insert(tk.END, msg + "\n")
            text_area.see(tk.END)
            text_area.configure(state=tk.DISABLED)
        root.after(0, _append)

    # 4) 백그라운드 스레드에서 분석 실행
    def run_analysis():
        try:
            from koodyna import __version__, BUILD_DATE, EXPIRE_DAYS
            from datetime import datetime, timedelta
            expire = datetime.strptime(BUILD_DATE, "%Y-%m-%d") + timedelta(days=EXPIRE_DAYS)
            log(f"KooDynaDiag v{__version__} (빌드: {BUILD_DATE})")
            log(f"사용 만료일: {expire.strftime('%Y-%m-%d')}")
            log("")
            log(f"분석 폴더: {result_dir}")
            log("")

            # stdout 캡처 (verbose 출력용)
            import io
            old_stdout = sys.stdout

            class TeeWriter:
                """Write to both buffer and GUI log."""
                def __init__(self):
                    self.buf = io.StringIO()
                def write(self, s):
                    self.buf.write(s)
                    # 줄 단위로 GUI에 출력
                    for line in s.splitlines():
                        stripped = line.strip()
                        if stripped:
                            log(stripped)
                def flush(self):
                    pass

            tee = TeeWriter()
            sys.stdout = tee

            log("파서 초기화 중...")
            from koodyna.analyzer import Analyzer
            analyzer = Analyzer(result_dir, verbose=True)

            log("분석 실행 중...")
            log("")
            report = analyzer.run()

            sys.stdout = old_stdout

            log("")
            log("HTML 리포트 생성 중...")
            from koodyna.report.html_report import write_html_report
            html_path = result_dir / "koodyna_report.html"
            write_html_report(report, html_path)
            log(f"저장 완료: {html_path}")

            log("")
            log("브라우저에서 리포트를 여는 중...")
            _open_in_browser(html_path, log)

            log("")
            log("=" * 50)
            log("  분석 완료! 브라우저에서 리포트를 확인하세요.")
            log("=" * 50)

        except Exception as e:
            sys.stdout = old_stdout if 'old_stdout' in dir() else sys.__stdout__
            log(f"\n오류 발생: {e}")
            import traceback
            log(traceback.format_exc())

        finally:
            sys.stdout = sys.__stdout__
            root.after(0, lambda: close_btn.configure(state=tk.NORMAL))

    thread = threading.Thread(target=run_analysis, daemon=True)
    thread.start()

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(
        prog="koodyna",
        description="LS-DYNA simulation result analyzer for debugging and performance profiling",
    )
    parser.add_argument(
        "result_dir",
        nargs="?",
        type=Path,
        default=None,
        help="Path to LS-DYNA result folder (omit for GUI mode)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Write JSON report to file",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed parsing progress",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Write HTML report to file (Korean output)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored terminal output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--scan",
        type=Path,
        default=None,
        metavar="BASE_DIR",
        help="Scan BASE_DIR recursively for d3plot directories and update the index",
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=None,
        metavar="INDEX_PATH",
        help="Index file path (default: ~/.koodyna/index.json)",
    )
    parser.add_argument(
        "--list-index",
        action="store_true",
        help="Print the contents of the result index",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze all pending entries in the index (use with --scan or alone)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="OUTPUT_DIR",
        help="Directory for batch analysis JSON reports (default: ~/.koodyna/reports/)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Max number of cases to analyze in batch mode (0 = all)",
    )
    parser.add_argument(
        "--reanalyze",
        action="store_true",
        help="Re-run analysis even for already-analyzed entries",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Skip HTML report generation in batch mode (JSON only)",
    )
    parser.add_argument(
        "-k", "--keyword",
        type=str,
        default=None,
        metavar="KEYWORD",
        help="Filter subdirectories containing KEYWORD (use with result_dir for parallel batch)",
    )
    parser.add_argument(
        "--np",
        type=int,
        default=4,
        metavar="N",
        help="Number of parallel processes for batch analysis (default: 4)",
    )

    args = parser.parse_args()

    # --scan mode (optionally followed by --analyze)
    if args.scan is not None:
        from koodyna.scanner import run_batch_scan, run_batch_analyze, DEFAULT_INDEX_PATH
        index_path = args.index or DEFAULT_INDEX_PATH
        if not args.scan.is_dir():
            print(f"Error: '{args.scan}' is not a directory", file=sys.stderr)
            sys.exit(1)
        run_batch_scan(args.scan, index_path=index_path, verbose=args.verbose)
        if args.analyze:
            run_batch_analyze(
                index_path=index_path,
                output_dir=args.output_dir,
                verbose=args.verbose,
                limit=args.limit,
                reanalyze=args.reanalyze,
                html=not args.no_html,
            )
        return

    # --analyze mode (without --scan: analyze pending from existing index)
    if args.analyze:
        from koodyna.scanner import run_batch_analyze, DEFAULT_INDEX_PATH
        index_path = args.index or DEFAULT_INDEX_PATH
        run_batch_analyze(
            index_path=index_path,
            output_dir=args.output_dir,
            verbose=args.verbose,
            limit=args.limit,
            reanalyze=args.reanalyze,
            html=not args.no_html,
        )
        return

    # --list-index mode
    if args.list_index:
        from koodyna.scanner import print_index, DEFAULT_INDEX_PATH
        index_path = args.index or DEFAULT_INDEX_PATH
        print_index(index_path)
        return

    # Parallel batch mode: result_dir + keyword
    if args.result_dir is not None and args.keyword is not None:
        _run_parallel_batch(args.result_dir, args.keyword, args.np, args.no_html)
        return

    # GUI mode: no arguments provided
    if args.result_dir is None:
        _run_gui_mode()
        return

    if not args.result_dir.is_dir():
        print(f"Error: '{args.result_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    d3hsp = args.result_dir / "d3hsp"
    mes0000 = args.result_dir / "mes0000"
    if not d3hsp.exists() and not mes0000.exists():
        print(
            f"Error: No d3hsp or mes0000 found in '{args.result_dir}'. "
            "Is this an LS-DYNA result folder?",
            file=sys.stderr,
        )
        sys.exit(1)

    from koodyna.analyzer import Analyzer
    from koodyna.report.terminal import render_report
    from koodyna.report.json_report import write_json_report

    analyzer = Analyzer(args.result_dir, verbose=args.verbose)
    report = analyzer.run()

    render_report(report, no_color=args.no_color)

    if args.output:
        write_json_report(report, args.output)
        from rich.console import Console
        console = Console(force_terminal=not args.no_color)
        console.print(f"\n[dim]JSON report saved to: {args.output}[/dim]")

    if args.html:
        from koodyna.report.html_report import write_html_report
        write_html_report(report, args.html)
        from rich.console import Console
        console = Console(force_terminal=not args.no_color)
        console.print(f"\n[dim]HTML report saved to: {args.html}[/dim]")
