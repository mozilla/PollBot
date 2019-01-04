CHANGELOG
=========

1.4.1 (2019-01-04)
------------------

- Upgrading PyYaml 4.2b4


1.4.0 (2018-10-30)
------------------

- Nightly buildIDs depends on the *local* time (#237)

- new make-release script

1.3.0 (2018-10-29)
------------------

- Release notes for DevEdition gets it's locales from the correct file on
  www.mozilla.org now.
  See https://github.com/mozilla/PollBot/issues/231

- Telemetry Uptake completely rewritten. Instead of creating a new query
  for each buildIDs+channel combo, we now have a specific known saved
  query that is run every 24h in Redash. PollBot now only queries its
  results. Also, the results isn't 1 number (row) but is grouped by
  channel and buildIDs and the Python code loops over the records (roughly
  6,000 rows) and extras the ``updated`` number for the buildIDs and
  channels that belongs to the query.
  No more need for a TELEMETRY_USER_ID.

1.2.1 (2018-10-05)
------------------

- Telemetry: Read the paginated results instead of from the body. (#226)

1.2.0 (2018-07-31)
------------------

- API change: remove the crash stats ADI endpoint. (#219)
- API change: fix the api.yaml: the ongoing-versions endpoint doesn't return a status.


1.1.5 (2018-05-16)
------------------

- Bug fix: loosen a test that was too strict.


1.1.4 (2018-02-21)
------------------

- Fix TELEMETRY_USER_ID comparison.


1.1.3 (2018-02-20)
------------------

- Only search for queries created by this user. (fixes #195)


1.1.2 (2018-02-15)
------------------

- Update the whatsdeployed URL.
- Add host to the OpenAPI specification.


1.1.1 (2018-02-14)
------------------

- Improve the Telemetry query to always update the yesterday filter. (#193)


1.1.0 (2018-02-14)
------------------

- Improve Telemetry ``main_summary`` query performances. (#188)


1.0.0 (2018-01-31)
------------------

- Add validation rules for release notes links (HTTPS, locale free). (#160)
- Read the correct mercurial shipped locale file for release candidates (#161)
- Add an actionable flag for tasks (#162)
- Order checks putting non actionable checks at the end. (#163)
- Add support for devedition checks (#166)
- Add a whatsdeployed link in the contribute.json file (#168)
- Use main_summary instead of update_parquet for the Telemetry uptake (#172)
- Calculate the crash-stats uptake including Beta previous version. (#174)
- Use the ``aurora`` channel for devedition checks (#177)
- Fix Balrog beta and devedition version comparison (#178)
- Display the backgroundRate value but do not use it to mark the check as incomplete (#180)
- Handle ``coming soon`` release notes status (#182)
- Take more versions into account for the crash-stats query (#184)
- Use the DEVEDITION specific Mercurial tag for shipped-locales (#185)


0.6.1 (2017-12-20)
------------------

- Fix release notes checks for ESR.


0.6.0 (2017-12-20)
------------------

- Reuse the same Nightly query for Telemetry Update Parquet (#141)
- Read the correct locale file for release candidates (#146)
- Add bouncer checks and endpoints (#147)
- Handle case when Download links return a 504 instead of a 302 (#152)
- Always expect a major version security advisory title for release and ESR (#150)
- Add an ``actionable`` flag for tasks to define if theyshould make the release fail or not (#151)
- Switch to Telemetry Athena Data Source (#155)
- Add an indication about Crash-Stats 24h latency (#156)
- Fix get_version_from_filename for all locales (#157)
- Validate Release notes links (#159)


0.5.0 (2017-11-06)
------------------

- Add support for release candidates (#137)
- Add support for new bedrock beta links (#139)


0.4.0 (2017-10-27)
------------------

- Add support for TaskError url (#113)
- Ignore ``Copy of`` Telemetry search results (#115)
- Deduplicate Balrog Build IDs (#116)
- Build telemetry query from a list of build IDs (#117)
- Add the product lists in the homepage (#118)
- Handle Telemetry empty results responses (#121)
- Enable a buildhub check for Nightly (#129)
- Keep only the Uptake ratio (#130)
- Use Buildhub prod (#131)


0.3.0 (2017-09-25)
------------------

- Update the archive check to validate that all expected files have been
  created for all locales and platforms (#48)
- Add a task and endpoint to check the release info in buildhub (#70)
- Add a task and endpoint to check the channel balrog rule (#72)
- Validate version number to avoid calling tasks with gibberish (#92)
- Remove archive nightly specific checks and endpoints (#95)
- Add a task and endpoint to check for partner-repacks (#100)
- Add a task and endpoint to get crash-stats uptake (#97)
- Add a task and endpoint to get telemetry update-parquet uptake (#97)


0.2.1 (2017-09-06)
------------------

- Fixes archive-l10n checks for nightly with new MAR files (#91)


0.2.0 (2017-09-01)
------------------

- Add a /v1/{product} endpoint (#47)
- Add a /v1/{product}/ongoing-versions endpoint (#52)
- Add a /v1/{product}/{version} that lists all checks (#62)
- Add a nightly specific task and endpoint for latest-date publication (#68)
- Add a nightly specific task and endpoint for latest-date-l10n publication (#68)
- Add more context about what the task have been checking (#58)
- Fix the ESR download links task url (#66)
- Add a task to validate if devedition and beta version matches (#78)
- Redirects URL ending by a / to URL without the / in case of 404 (#54)
- Add Cache-Control headers (#43)
- Handle aiohttp.ClientError as tasks errors (#76)
- Handle Archive CDN errors (#75)


0.1.0 (2017-08-08)
------------------

- Add the /v1/ info page (#10)
- Add the archive.mozilla.org bot (#17)
- Add the bedrock release-notes bot (#16)
- Add the bedrock security-advisories bot (#26)
- Add the bedrock download-page bot (#28)
- Add the product-details bot (#27)
- Expose the Open API Specification (#23)
- Add the contribute.json endpoint (#25)
- Add CORS support (#28)
- Add the /__version__ endpoint (39)
- Add the __heartbeat__ and __lbheartbeat__ endpoints (#38)
- Serve the Swagger documentation (#30)
