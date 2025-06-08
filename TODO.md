# TODO

- add REST endpoint(s) for allowing the datasource to advertise commands list (inc if its supported)
- add stub executor so we can check the behavior of the command queue (for /command and /world endpoints)
- check that command queue also returns the output of the command, not just a bool 'did it work'
- add real datasource that uses the cache, queue, and executor
- python venv active state detection seems to be a bit too easy to trip in cleanup-py-env.ps1 - needs review
