API Changelog
=============

1.3 (unreleased)
----------------

- Add bouncer checks and endpoints.


1.2 (2017-09-25)
----------------

- Add balrog checks and endpoints.
- Add buildhub checks and endpoints.
- Add Crash-Stats uptake check and endpoint.
- Add partner-repacks task and endpoint.
- Add Telemetry update parquet uptake check and endpoint.
- Remove multiple nightly archive checks.


1.1 (2017-09-01)
----------------

- Add multi channel handling.
- Add archive-date and archive-date-l10n checks and endpoints for nightly.
- Add the ongoing-versions endpoint.
- Add the list of checks for a given version endpoint.
- The security advisories tasks for nightly and beta now returns a "missing" status.
- archive-date and archive-date-l10n return a missing status for
  anything else than nightly versions.
- Add the devedition-beta-versions-matches endpoint and task.
- Add Cache-Control headers.


1.0 (2017-08-08)
----------------

- First version of PollBot.
