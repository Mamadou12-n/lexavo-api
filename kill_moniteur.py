"""Kill all moniteur_scraper.py processes so orchestrator relaunches them with new code."""
import subprocess
import sys

# Use WMI via Python to find moniteur_scraper PIDs
result = subprocess.run(
    ['wmic', 'process', 'where', "name='python.exe'", 'get', 'ProcessId,CommandLine', '/format:list'],
    capture_output=True, text=True, timeout=30
)

lines = result.stdout.splitlines()
pids_to_kill = []
current_cmdline = ""
current_pid = None

for line in lines:
    line = line.strip()
    if line.startswith("CommandLine="):
        current_cmdline = line[len("CommandLine="):]
    elif line.startswith("ProcessId="):
        current_pid = line[len("ProcessId="):].strip()
        if current_cmdline and "moniteur_scraper" in current_cmdline.lower():
            pids_to_kill.append(current_pid)
            print(f"Found: PID={current_pid} | {current_cmdline[:100]}")
        current_cmdline = ""
        current_pid = None

if not pids_to_kill:
    print("Aucun processus moniteur_scraper trouvé — peut-être déjà arrêté ou orchestrateur le relancera.")
else:
    for pid in pids_to_kill:
        kill = subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, text=True)
        print(f"Kill PID {pid}: {kill.stdout.strip()} {kill.stderr.strip()}")
    print(f"\n{len(pids_to_kill)} processus tués. L'orchestrateur relancera moniteur_scraper sous 30s.")
