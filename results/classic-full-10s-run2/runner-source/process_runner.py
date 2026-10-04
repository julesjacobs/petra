"""Sample a benchmark's process tree, including children that create sessions.

This is a portable pilot runner, not a replacement for Linux cgroup limits.
Short-lived children can escape sampling; CPU/RSS are sampled lower bounds.
"""
import subprocess
import time

import psutil


def run(command, cwd, seconds, output):
    start = time.perf_counter()
    known, cpu = {}, {}
    peak_rss = 0
    expired = False
    with output.open('w') as stream:
        child = subprocess.Popen(command, cwd=cwd, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        root = psutil.Process(child.pid)
        known[(root.pid, root.create_time())] = root
        try:
            while True:
                for process in list(known.values()):
                    try:
                        for descendant in process.children(recursive=True):
                            known[(descendant.pid, descendant.create_time())] = descendant
                    except psutil.Error:
                        pass
                rss = 0
                for identity, process in known.items():
                    try:
                        if not process.is_running():
                            continue
                        times = process.cpu_times()
                        cpu[identity] = times.user + times.system
                        rss += process.memory_info().rss
                    except psutil.Error:
                        pass
                peak_rss = max(peak_rss, rss)
                if child.poll() is not None:
                    break
                if time.perf_counter() - start >= seconds:
                    expired = True
                    break
                time.sleep(0.01)
        finally:
            # SMPT starts reduce/walk/Z3 in independent process groups.
            for process in reversed(list(known.values())):
                try:
                    if process.is_running():
                        process.kill()
                except psutil.Error:
                    pass
            if child.poll() is None:
                child.kill()
            child.wait()
    usage = dict(sampled_cpu_seconds=sum(cpu.values()), sampled_peak_rss_bytes=peak_rss,
                 observed_processes=len(known), sampling_interval_seconds=0.01)
    return time.perf_counter()-start, child.returncode, expired, usage
