# Sandbox attack report

Image `python:3.11-slim`, time limit 10 s (+ start-up). Flags: `--rm -i --network none --memory 256m --memory-swap 256m --cpus 1 --pids-limit 64 --read-only --tmpfs /tmp:rw,size=16m,mode=1777 --workdir /tmp --user 65534:65534 --cap-drop ALL --security-opt no-new-privileges --ulimit fsize=1048576:1048576 --ulimit nofile=64:64 --env PYTHONDONTWRITEBYTECODE=1 --env PYTHONHASHSEED=0`.

**24 of 24 attacks behaved as expected.** After the suite: Docker responds = True, leftover sandbox containers = 0.

Every attack is a submission for `add(a, b)` with one visible and one hidden test, so a successful attack would show up as harm or as a false pass.

| attack | category | expected | result | tests passed | time | ok |
|---|---|---|---|---|---|---|
| infinite loop | resource | killed at the time limit; no test passes | timeout: killed after 10s | 0/2 | 13.27s | yes |
| sleep forever | resource | killed at the time limit | timeout: killed after 10s | 0/2 | 13.24s | yes |
| fork bomb | resource | stopped by the 64-process limit, then the time limit; host unaffected | timeout: killed after 10s | 0/2 | 13.52s | yes |
| memory bomb | resource | MemoryError or OOM kill at 256 MB | killed: killed (exit 137: out of memory or process limit) | 0/2 | 0.86s | yes |
| CPU threads | resource | limited to 1 CPU; the tests still run (threads do not block grading) | ok | 2/2 | 5.54s | yes |
| output flood | resource | killed at the output cap | output_limit: output over 64000 bytes | 0/2 | 0.82s | yes |
| disk fill /tmp | resource | stopped by the 1 MB file-size limit / 16 MB tmpfs; grading continues | ok / printed: `stopped: [Errno 27] File too large
` | 2/2 | 0.74s | yes |
| deep recursion | resource | crash stays inside the container | killed: killed (exit 137: out of memory or process limit) | 0/2 | 2.02s | yes |
| read environment | secrets | no host variables, no API key | ok / printed: `{'PATH': '/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin` | 2/2 | 0.61s | yes |
| read /proc/1/environ | secrets | only the container's own variables | ok / printed: `b'PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/b` | 2/2 | 0.67s | yes |
| read project .env | secrets | host files are not mounted, so there is no .env to find | ok / printed: `/ilm_academy/.env FileNotFoundError
/app/.env FileNotFoundError
/home/.env FileN` | 2/2 | 0.74s | yes |
| read /etc/shadow | secrets | PermissionError (runs as nobody) | ok / printed: `blocked PermissionError
` | 2/2 | 0.69s | yes |
| network: raw socket | network | no route out | ok / printed: `blocked OSError
` | 2/2 | 1.1s | yes |
| network: HTTP + DNS | network | no DNS, no HTTP | ok / printed: `blocked URLError
` | 2/2 | 1.45s | yes |
| write outside /tmp | filesystem | read-only filesystem | ok / printed: `blocked /usr/local/lib/evil.py OSError
blocked /etc/evil OSError
blocked /evil O` | 2/2 | 1.16s | yes |
| become root | privilege | setuid fails, mount fails, uid stays 65534 | ok / printed: `blocked PermissionError
result 8192
uid 65534
` | 2/2 | 1.06s | yes |
| fake result line | grade integrity | flagged as tampering; no test passes | tampered: output contains fake result lines (flagged for the teacher) | 0/2 | 4.01s | yes |
| steal nonce + forge + exit | grade integrity | the forged line is accepted as the result, but the HOST compares 999 with the expected answers, so nothing passes (expected answers never enter the container) | ok | 0/2 | 1.6s | yes |
| always-equal object | grade integrity | reported as a non-plain object; fails | ok | 0/2 | 0.9s | yes |
| int subclass | grade integrity | exact type check: Fake is not int; fails | ok | 0/2 | 0.85s | yes |
| patch builtins | grade integrity | the harness kept its own references; 0 is reported and fails | ok | 0/2 | 0.9s | yes |
| atexit fake line | grade integrity | os._exit skips atexit; fails normally | ok | 0/2 | 0.79s | yes |
| hardcode visible test | grade integrity | passes the visible test only; the hidden test catches it (partial marks) | ok | 1/2 | 0.78s | yes |
| control: correct solution | control | both tests pass (the sandbox does not break honest code) | ok | 2/2 | 0.91s | yes |
