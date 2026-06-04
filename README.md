CLI Alarm Clock

A command-line alarm clock built in Python with support for recurring alarms, persistence, snoozing, and cross-platform notifications.

Overview

This project was built as a CLI-only alarm clock with a focus on reliability, simplicity, and maintainability.

Rather than maximizing the number of features, the goal was to create a practical tool that supports common alarm-clock workflows while keeping the implementation easy to understand and test.

Key areas of focus:

- Clear command-line experience
- Reliable alarm scheduling
- Persistent storage without a database
- Cross-platform support
- Comprehensive automated testing


Quick Summary

| Capability | Supported |
|------------|-----------|
| One-time alarms | ✅ |
| Daily alarms | ✅ |
| Weekday alarms | ✅ |
| Weekend alarms | ✅ |
| Snooze | ✅ |
| Persistent storage | ✅ |
| Custom sounds | ✅ |
| Cross-platform notifications | ✅ |
| Automated tests | ✅ |
| External dependencies | ❌ |
| Database | ❌ |
| Web UI | ❌ |


Engineering Tradeoffs

| Question | Decision | Reasoning |
|-----------|-----------|-----------|
| Database or file storage? | JSON file | Simple, transparent, and sufficient for a local CLI application |
| Threads or foreground loop? | Foreground loop | Easier lifecycle management and fewer failure modes |
| UUIDs or integer IDs? | Integer IDs | Easier to read and reference from the terminal |
| Cron expressions or fixed recurrence? | Fixed recurrence | Covers common use cases without increasing complexity |
| Native audio libraries or system tools? | System tools | Avoids additional dependencies and remains cross-platform |


Development Notes

The assignment intentionally left room for interpretation, so I spent time defining scope before writing code. My approach was to prioritize correctness, usability, and maintainability rather than implementing as many features as possible. During development, I evaluated several alternative designs around scheduling, persistence, recurrence handling, and notifications before settling on the current implementation. 
Some ideas were intentionally left out because they increased complexity without providing meaningful value for a command-line application, including background daemons, plugin systems, cron-style recurrence rules, and additional runtime dependencies. 
I also spent time validating edge cases around time parsing, recurring schedules, storage behavior, and alarm triggering to ensure the core functionality remained predictable.
The resulting implementation reflects a balance between functionality, simplicity, and testability.


Manual Test Scenarios

| Scenario | Expected Result |
|-----------|----------------|
| Add alarm and list | Alarm appears in active alarms |
| Cancel alarm | Alarm is removed |
| Invalid time input | Validation error shown |
| Unknown alarm ID | Clear error message returned |
| Weekday recurrence | Alarm skips weekends |
| Snooze | New one-time alarm is created |
| Missing sound file | Alarm creation is rejected |
| Run with no alarms | Informative message displayed |
| Ctrl+C during scheduler | Graceful shutdown |
| Alarm trigger interaction | Snooze, dismiss, and quit actions work correctly |


## Future Improvements

| Priority | Enhancement |
|----------|-------------|
| High | Day-specific recurrence (`Mon, Wed, Fri`) |
| High | Native desktop notifications |
| Medium | Persistent scheduler state |
| Medium | Background service mode |
| Medium | Packaging and installation via pip |
| Low | Timezone-aware scheduling |


TO TEST RUN: 

Setup

Requires Python 3.9+.

Clone the repository:

```bash
git clone <repo-url>
cd alarm-clock-cli

python -m venv .venv
source .venv/bin/activate

.venv\Scripts\activate

//only for running test suite 
pip install -r requirements-dev.txt

python alarm.py --help

python alarm.py add "14:30" --label "Standup"

python alarm.py list

python alarm.py run

python alarm.py cancel 1

python alarm.py snooze 1 --minutes 5

//TEST
pytest
python -m pytest


NOTE: That's all you need. No mention of iOS, Android, React, or web platforms. 
