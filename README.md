# Deadlock Parry Practice

Randomly punches you every few minutes. When you hear the sound, press F.

```
Usage: deadlock_parry.exe [OPTIONS]

Options:
  -m, --delay-min INTEGER     The minimum delay before a random punch, in
                              seconds (Default: 30)
  -x, --delay-max INTEGER     The maximum delay before a random punch, in
                              seconds (Default: 300)
  -w, --parry-window INTEGER  The maximum allowed duration for parrying before
                              being hit, in milliseconds (Default: 600)
  -k, --parry-key TEXT        The key binding for parry (Default: F)
  --help                      Show this message and exit.
```

See success rate and average response time.

```
...
Parry success: 430ms
5 / 7 (71.43%), average response: 392ms
Parry success: 429ms
6 / 8 (75.00%), average response: 398ms
Parry failed, you died.
6 / 9 (66.67%), average response: 398ms
```
