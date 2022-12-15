CHANGELOG
=========

1.4.8 (2022-12-15)
------------------

- Merge pull request #383 from mozilla/dependabot/pip/cryptography-38.0.3

- Merge pull request #380 from mozilla/dependabot/pip/certifi-2022.12.7

- Bump certifi from 2022.6.15 to 2022.12.7

- Bump cryptography from 37.0.4 to 38.0.3

- Merge pull request #382 from mozilla/dependabot/pip/zest-releaser-7.2.0

- Bump zest-releaser from 7.0.0 to 7.2.0

- Merge pull request #378 from mozilla/dependabot/pip/swagger-spec-validator-3.0.3

- Bump swagger-spec-validator from 3.0.2 to 3.0.3

- Merge pull request #377 from mozilla/dependabot/pip/pytest-7.2.0

- Bump pytest from 7.1.3 to 7.2.0

- Merge pull request #376 from mozilla/dependabot/pip/swagger-spec-validator-3.0.2

- Bump swagger-spec-validator from 2.7.6 to 3.0.2

- Merge pull request #375 from mozilla/dependabot/pip/aiohttp-3.8.3

- Bump aiohttp from 3.8.1 to 3.8.3

- Merge pull request #374 from mozilla/dependabot/pip/zest-releaser-7.0.0

- Bump zest-releaser from 6.22.2 to 7.0.0

- Merge pull request #371 from mozilla/dependabot/pip/swagger-spec-validator-2.7.6

- Bump swagger-spec-validator from 2.7.4 to 2.7.6

- Merge pull request #372 from mozilla/dependabot/pip/pytest-7.1.3

- Bump pytest from 7.1.2 to 7.1.3

- Merge pull request #373 from gbrownmozilla/fix-lint

- remove unused import to fix lint error

- Merge pull request #370 from gbrownmozilla/upgrade-pytest

- Upgrade pytest-aiohttp to 1.0.4

- Merge pull request #369 from gbrownmozilla/upgrade-python

- Use python 3.8, re-pin requirements

- Merge pull request #368 from mozilla/dependabot/pip/flake8-5.0.4

- Bump flake8 from 4.0.1 to 5.0.4

- Merge pull request #367 from mozilla/dependabot/pip/lxml-4.9.1

- Bump lxml from 4.6.5 to 4.9.1

- Merge pull request #366 from mozilla/dependabot/pip/pytest-7.0.1

- Bump pytest from 7.0.0 to 7.0.1



1.4.7 (2022-03-01)
------------------

- Merge pull request #365 from jfx2006/tb_security_bugfix

- line too long fix

- Fix Thunderbird security advisories for patch level releases. #364

- Merge pull request #363 from gbrownmozilla/circleci-image

- update circleci image



1.4.6 (2022-02-08)
------------------

- Merge pull request #361 from gbrownmozilla/cleanup

- Add CODEOWNERS, remove some broken links

- Merge pull request #360 from gbrownmozilla/redirects

- Fix lint error

- Expand unit tests

- Merge pull request #358 from mozilla/dependabot/pip/aioresponses-0.7.3

- Merge pull request #359 from mozilla/dependabot/pip/pytest-7.0.0

- Merge pull request #357 from mozilla/dependabot/pip/lxml-4.6.5

- Use string.whitespace

- Harden trailing slashes redirect

- Bump pytest from 6.2.5 to 7.0.0

- Bump aioresponses from 0.7.2 to 0.7.3

- Bump lxml from 4.6.3 to 4.6.5

- Merge pull request #356 from mozilla/dependabot/pip/aiohttp-3.8.1

- Bump aiohttp from 3.8.0 to 3.8.1

- Merge pull request #355 from mozilla/dependabot/pip/swagger-spec-validator-2.7.4

- Merge pull request #354 from mozilla/dependabot/pip/aiohttp-3.8.0

- Bump aiohttp from 3.7.4.post0 to 3.8.0

- Merge pull request #353 from mozilla/dependabot/pip/aiohttp-swagger-1.0.16

- Bump swagger-spec-validator from 2.7.3 to 2.7.4

- Bump aiohttp-swagger from 1.0.15 to 1.0.16



1.4.5 (2021-10-14)
------------------

- Merge pull request #352 from gbrownmozilla/upgrade-requirments-txt

- upgrade all requirements via pip-compile --upgrade in python 3.6

- Merge pull request #351 from gbrownmozilla/permissions-fix

- use chown instead

- relax docker file permissions to allow run-tests.sh to run pip install successfully

- Merge pull request #349 from gbrownmozilla/python-version

- Merge pull request #348 from gbrownmozilla/reformat-requirements-txt

- add .python-version file, for dependabot

- update requirements.txt with modern pip-compile, python 3.6

- Merge pull request #346 from jfx2006/thunderbird-support

- Update test for Thunderbird Daily download link.

- Update Thunderbird Nightly download link query selector



1.4.4 (2021-03-01)
------------------

- (HEAD -> master, upstream/master) Merge pull request #333 from bhearsum/advisory-fix-1

- (sec/advisory-fix-1, origin/advisory-fix-1, advisory-fix-1) Fix invalid request in view test

- Add missing MarkupSafe hash

- Remove leading slashes in 404 redirections

- (tag: 1.4.3, sec/master, origin/master, origin/HEAD, open-redirect) Merge pull request #311 from mozbhearsum/remove-constraints

- (origin/remove-constraints, remove-constraints) Remove now-unused constraints file

- Version bump

- Merge pull request #308 from mozbhearsum/deps

- (origin/deps, deps) Fix deps

- Merge latest from master

- Fix async with in tests

- Bump dependencies

- Add requirements.in

- Merge pull request #278 from mozilla/dependabot/pip/markupsafe-1.1.1

- Merge pull request #253 from jfx2006/thunderbird-support

- Bump markupsafe from 1.0 to 1.1.1

- Add dependabot config

- Fix line length and whitespace test errors.

- Add some new tests for Thunderbird specific cases.

- Fixes for existing tests

- Make existing tests aware of thunderbird product.

- Support download links for Thunderbird release and beta.

- Add heartbeat for www.thunderbird.net

- Combine archives rules for RELASE and BETA/AURORA channels.

- Enable 'thunderbird' product.

- Disable checks that do not apply to Thunderbird releases.

- Support Thunderbird in product_details task.

- Support Thunderbird in bedrock task.

- Support Thunderbird in balrog task.

- Support Thunderbird in archive task.

- Support Thunderbird in bouncer task.

- Support Thunderbird in buildhub task.



1.4.2 (2019-11-05)
------------------

- (HEAD -> master, upstream/master) Merge pull request #252 from jcristau/bouncer-247

- (jcristau/bouncer-247) Stop scraping www.mozilla.org for bouncer download links



1.4.1 (2019-07-01)
------------------

- Upgrading PyYaml 4.2b4
- Update Jinja2
- Switch from Buildhub to Buildhub2 (#244)
- Fix CoC (#243)
- Pin requirements (#234)
- Rework local development environment so it's Docker-based


1.4.0 (2018-10-30)
------------------

- Nightly buildIDs depends on the *local* time (#237)
- new make-release script

1.3.0 (2018-10-29)
------------------

API changes:

- Add bouncer checks and endpoints.
- Remove the crash stats ADI endpoint.
- The ongoing-versions endpoint doesn't return a status: fixed the api.yaml
  file

Everything else

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

API changes:

- remove the crash stats ADI endpoint. (#219)
- fix the api.yaml: the ongoing-versions endpoint doesn't return a status.
- Add balrog checks and endpoints.
- Add buildhub checks and endpoints.
- Add Crash-Stats uptake check and endpoint.
- Add partner-repacks task and endpoint.
- Add Telemetry update parquet uptake check and endpoint.
- Remove multiple nightly archive checks.


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

API changes:

- Add multi channel handling.
- Add archive-date and archive-date-l10n checks and endpoints for nightly.
- Add the ongoing-versions endpoint.
- Add the list of checks for a given version endpoint.
- The security advisories tasks for nightly and beta now returns a "missing" status.
- archive-date and archive-date-l10n return a missing status for
  anything else than nightly versions.
- Add the devedition-beta-versions-matches endpoint and task.
- Add Cache-Control headers.

Everything else:

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
