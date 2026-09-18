# CHANGELOG


## v0.12.4 (2026-09-18)

### Bug Fixes

- Clear no-match message for --status --host --output-filter
  ([`3cdd46f`](https://github.com/sadsfae/mozzo/commit/3cdd46fdb7534dd3d3ca2820f6bb25488b9f0698))

With a filter but no --service, the no-results path printed 'Service None not found ...'. Say no
  services match the filter; keep 'Service X not found' only for the --service case. Found in live
  smoke testing against Nagios 4.4.14.

fixes: https://github.com/sadsfae/mozzo/issues/64

- Close empty-service host-guard bypass
  ([`c401507`](https://github.com/sadsfae/mozzo/commit/c4015070320650899ffeb97e161d9d24e21a6583))

--service "" is falsy, so the require-host guard let it through and a host-scoped toggle still
  flipped global notifications. Treat any --service value as host-scoped. Also harden the Python 3.6
  stdout rewrap against streams exposing buffer without errors/line_buffering.

fixes: https://github.com/sadsfae/mozzo/issues/51

- Keep Python 3.6 support and harden the host guard
  ([`bf834a9`](https://github.com/sadsfae/mozzo/commit/bf834a93783fd636573558f85caf6c988ac58fb7))

Addresses review feedback on requires-python and guard placement.

- Revert requires-python to >=3.6 and add a 3.6 UTF-8 fallback (io.TextIOWrapper rewrap of
  sys.stdout.buffer) so mozzo still runs on EL8 platform-python (3.6.8) without a venv, while
  preserving emoji output. - Extract the UTF-8 logic into _force_utf8_stdout for testability and add
  a test for the 3.6 branch. - Move the --host guard ahead of MozzoNagiosClient construction so
  argument validation fires before any config read or requests session. - Simplify the argv test
  fixture to use monkeypatch.setattr and drop the manual try/finally restore. - Assert the guard
  passes in the two smoke tests.

Tests: 62 passed (was 61); flake8 clean; cli coverage 51% -> 52%.

- Only disable urllib3 warnings when SSL verification is off
  ([`8b0bbff`](https://github.com/sadsfae/mozzo/commit/8b0bbffc70cb2070fa65d1d89bfde089b774ebf2))

Move urllib3.disable_warnings out of module import into the client constructor, gated on verify_ssl
  being false. Importing mozzo.cli as a library no longer weakens HTTPS warnings process-wide.

Fixes: https://github.com/sadsfae/mozzo/issues/52

- Raise minimum Python version to 3.7
  ([`d73ff25`](https://github.com/sadsfae/mozzo/commit/d73ff2524e122d35a5de53a77fa6b70f78b522a4))

sys.stdout.reconfigure requires Python 3.7+.

fixes: https://github.com/sadsfae/mozzo/issues/53

- Require --host for host-scoped mutating commands
  ([`a4025a2`](https://github.com/sadsfae/mozzo/commit/a4025a24e7dac86eb3d5836a42e41e017e3116dd))

--service/--all-services without --host silently toggled global notifications. Guard in main() now
  errors for ack/downtime/enable/disable-alerts when a host-scoped modifier is used without a host.

fixes: https://github.com/sadsfae/mozzo/issues/51

- Stop sending off-valued ack checkboxes to cmd.cgi
  ([`d5a3231`](https://github.com/sadsfae/mozzo/commit/d5a3231a0a5e99d6914c2bac4946bb8790a1d2c3))

cmd.cgi parses send_notification/persistent as checkbox presence, so the "off" values were
  interpreted as enabled: acks notified and persisted. Omitting the keys keeps both disabled as
  documented.

fixes: https://github.com/sadsfae/mozzo/issues/59

### Documentation

- Note system deps and venv for pip install
  ([`cecb30b`](https://github.com/sadsfae/mozzo/commit/cecb30be26c308b77de710937a557a967780faa3))

Document required python3-requests and python3-pyyaml for the standalone (Option 1) install, and
  instantiate a virtual environment before pip install in Option 2 so it matches the venv pattern
  used by the pypi option.

### Refactoring

- Extract shared alerting-services filter into a generator
  ([`e449413`](https://github.com/sadsfae/mozzo/commit/e44941343c8f5f137208e426a18a1d57662bb889))

The 'fetch servicelist, keep issue codes, skip handled' loop was copy pasted into
  acknowledge_all_alerting_services, show_unhandled, and show_service_issues. Extract
  _iter_alerting_services() yielding (host, svc_name, status_code, details) with a skip_handled
  toggle, and have all three consume it. show_service_issues now reuses the shared alerting fetch
  (details=true) which returns the same issue set.

Fixes: https://github.com/sadsfae/mozzo/issues/54

### Testing

- Cover argparse dispatch layer and command methods
  ([`dac1b08`](https://github.com/sadsfae/mozzo/commit/dac1b08e2bf0caa74d3d17637399a4e54a99a4c3))

Add parametrized tests driving mozzo.cli.main() end to end via sys.argv with
  requests.Session.get/post patched at the class level and capsys. Exercises every dispatch branch:
  ack/downtime/toggle commands, status, uptime, unhandled, service-issues, ack-history, logs, help,
  JSON output, and the --all/--service mutual-exclusion error.

POST commands assert the posted cmd_typ, host, and service so a dispatch swap, an enable/disable
  inversion, or a right-command-to-wrong-target bug is caught; read commands assert data-derived
  output rather than static headers.

cli.py coverage rises from 45% to 88%.

Fixes: https://github.com/sadsfae/mozzo/issues/50

- Harden dispatch and alerting-service mocks
  ([`73e5a94`](https://github.com/sadsfae/mozzo/commit/73e5a948a54103cb413fd859e2631b3ecb50ae8f))

Mirror real statusjson.cgi shapes in the iteration mock, drop the unreachable details=false fixture
  branch, and cover the remaining dispatch rows (service-issues --host, --output-filter, csv format,
  service ack-history, enable-alerts).


## v0.12.3 (2026-07-15)

### Bug Fixes

- Refactor for DRY principles.
  ([`3ce2cca`](https://github.com/sadsfae/mozzo/commit/3ce2cca4570d1d0044e4a247d5a880d9eb0a8f40))

Source code (cli.py): - C1: Replaced 10-line _get_version() file parser with from mozzo import
  __version__ - C5: Removed redundant timeout=60 kwarg - S12: Moved "cmd_mod": 2 injection into
  _post_cmd(), removed from 6 callers - S1: Extracted _fetch_alerting_services() helper, replacing
  identical 5-line blocks in 2 methods - S2: Added ISSUE_STATUS_CODES = {4, 8, 16} class constant,
  updated 2 of 3 references (line 631 kept as-is per plan)


## v0.12.2 (2026-05-29)

### Bug Fixes

- Regression was a URL encoding.
  ([`462b7ba`](https://github.com/sadsfae/mozzo/commit/462b7ba2ecec86d9f7ae4fd6005c86f52310dd0a))

* introduced during major refactor.

Assisted-by: claude


## v0.12.1 (2026-05-21)

### Bug Fixes

- Fix refactoring regression
  ([`ba9e2bb`](https://github.com/sadsfae/mozzo/commit/ba9e2bbdbe4bd3ec1cdae15d8e6df7df6ccd52c1))

- Issue with uptime command, major refactor
  ([`ba14251`](https://github.com/sadsfae/mozzo/commit/ba14251c83cddaa10ce16a07e67cf1e1bf109f66))


## v0.12.0 (2026-05-21)

### Chores

- Fix tests
  ([`d0ccb0e`](https://github.com/sadsfae/mozzo/commit/d0ccb0e5fdb99da9b5e1f687067bf6337533960c))

### Features

- Add --ack --all
  ([`d481590`](https://github.com/sadsfae/mozzo/commit/d48159033c6a3f6a9aeb4e15739a87c7c38718dd))


## v0.11.0 (2026-04-29)

### Chores

- Fix tests
  ([`43e5f66`](https://github.com/sadsfae/mozzo/commit/43e5f66fddcc36f09a6fb89c8d4b885fd302b6d5))

- Set mozzo.py to be executable
  ([`13f1b69`](https://github.com/sadsfae/mozzo/commit/13f1b694f07331c96da66f665247f6094749dbd0))

- Use class constant for emoji usage
  ([`f61f3f4`](https://github.com/sadsfae/mozzo/commit/f61f3f4be0661ac1d4be83086170754fd8db0a3e))

### Features

- --log to view nagios logs
  ([`063a4a6`](https://github.com/sadsfae/mozzo/commit/063a4a6b817d22939f59112272e81680c2209d5e))

fixes: https://github.com/sadsfae/mozzo/issues/43


## v0.10.1 (2026-04-22)

### Bug Fixes

- Perf regression, restore lazy-loading.
  ([`4aa6812`](https://github.com/sadsfae/mozzo/commit/4aa6812b3ef6ec1012a8c976b8d30b9745de9179))

- Restored lazy-loading approach - Added smart pre-filtering at service level to minimize host API
  calls - Reduced from 26+ API calls down to just 3

- Performance regression, restore lazy loading
  ([`7772173`](https://github.com/sadsfae/mozzo/commit/7772173fb68176999215006c49da8ba500aaaced))

- Restored lazy-loading approach - Added smart pre-filtering at service level to minimize host API
  calls - Reduced from 26+ API calls down to just 3


## v0.10.0 (2026-04-22)

### Chores

- Cleanup
  ([`79ad9a6`](https://github.com/sadsfae/mozzo/commit/79ad9a6d5d94086fe3d6f236fececac492d2e4f0))

- Fix tests
  ([`eeb774d`](https://github.com/sadsfae/mozzo/commit/eeb774da7c43fdb36ee4a67257fb1cefc5013731))

### Features

- Add helper methods, local testing.
  ([`aec5d68`](https://github.com/sadsfae/mozzo/commit/aec5d68fa1653fd9944e78118deb65a59c7ebea9))

* Major refactor * Added helpers

- _get_status_text() - Unified status code to text mapping - _format_downtime_duration() -
  Centralized duration string formatting - _print_toggle_action() - Standardized alert toggle
  messaging - _matches_host() - Bidirectional hostname matching (FQDN and shortname) -
  _build_ack_payload() - Acknowledgement payload construction - _build_downtime_payload() - Downtime
  payload construction - _build_service_result() - Service result dictionary builder -
  _fetch_availability_data() - Archive API availability fetching - _print_uptime_report() - Uptime
  report output formatting

- Add pytest GHA
  ([`f31ccc1`](https://github.com/sadsfae/mozzo/commit/f31ccc1b84e9102c0feb970a1b4ebd5ce2c7ae5f))


## v0.9.0 (2026-04-12)

### Features

- Major refactor, global timeout, cleanup.
  ([`16777b0`](https://github.com/sadsfae/mozzo/commit/16777b0c09b4d68c56dfe54ab29c08adfc2f0780))

* Added global 60s timeout * Major refactoring * Major cleanup and removing duplication of some
  processing * Ensure status map usage to reduce code surface.

- Move global timeout to session layer
  ([`3ec4aa4`](https://github.com/sadsfae/mozzo/commit/3ec4aa471837baca24b034a485ab6794ad02acea))


## v0.8.0 (2026-04-01)

### Features

- Add acknowledgement history via CLI.
  ([`80e86c9`](https://github.com/sadsfae/mozzo/commit/80e86c97aa41cec6a2c8d976678aca8a6aa4027d))

fixes: https://github.com/sadsfae/mozzo/issues/37


## v0.7.1 (2026-03-30)

### Bug Fixes

- --unhandled not parsing statusjson.cgi fully.
  ([`91b57dc`](https://github.com/sadsfae/mozzo/commit/91b57dcdfe9c9e990688a94c10797dd82cea4b13))

* Fix issue where warning+critical+unknown wasn't interpreted properly causing --unhandled to not
  return accurately. * Fix falling back to pagination * Add limit '0' globally to ensure pagination
  doesn't trip us.


## v0.7.0 (2026-03-27)

### Chores

- Add --version
  ([`a223911`](https://github.com/sadsfae/mozzo/commit/a2239110bab3461d2a6caf4b269bae0b4cf758e2))

* It's about time we supported --version * Let's try to do it in a python-package friendly way but
  fall back if mozzo is run as a script too.

- Add --version method
  ([`a1bf6e9`](https://github.com/sadsfae/mozzo/commit/a1bf6e918d17b0a99ff1840a9f770186cb393c80))

chore: add small --version method

- Change --version approach
  ([`f851fa4`](https://github.com/sadsfae/mozzo/commit/f851fa4105ee432e86ebd270be93dd79b6453546))

- Fix emojibake issue with utf8.
  ([`43f9b89`](https://github.com/sadsfae/mozzo/commit/43f9b8923f8303e5a81502c62535686c93fdefb3))

* This is very important to Kambiz.

- Update example config.yml
  ([`d7183b9`](https://github.com/sadsfae/mozzo/commit/d7183b991e831adbc0534b06cca15085b0417e41))

* Update config.yml with new default_reporting_days value.

### Features

- Massive performance enhancements
  ([`df42177`](https://github.com/sadsfae/mozzo/commit/df42177294c4b16c807a74c6f05e344086970fe5))

* Massive speed-ups using lazyloading so we dont need to pull the entire multi-MB CGI JSON response.
  * First filter at server side for only services in scope for show_single_service and:

--unhandled --service-issues

- Massive speed increase for CGI return.
  ([`a26e92b`](https://github.com/sadsfae/mozzo/commit/a26e92b5b6b185d74aed592e583f82cdc1787a11))

* Massive speed-ups using lazyloading so we dont need to pull the entire multi-MB CGI JSON response.
  * First filter at server side for only services in scope for:

--unhandled --service-issues

- Performance fix for show_single_service
  ([`d8a43fb`](https://github.com/sadsfae/mozzo/commit/d8a43fb8685d700fbd51ca23e6c593c536255507))

* speed ups for show_single_service as well.


## v0.6.0 (2026-03-25)

### Chores

- Restore code comments and python doc
  ([`1729199`](https://github.com/sadsfae/mozzo/commit/1729199e6c852ebdb32b578ddd482ac179d73fca))

### Features

- Add --days to --set-downtime, support float.
  ([`9947e9c`](https://github.com/sadsfae/mozzo/commit/9947e9cd5d0174bafe4bbd3d89c3a591ad85d437))

fixes: https://github.com/sadsfae/mozzo/issues/30

* Made --days a float * Support --days with --set-downtime e.g. --days 0.5 --days 2 * Add value
  "default_reporting_days" to set default uptime reports if no argument is passed.


## v0.5.0 (2026-02-27)

### Features

- Add features for status
  ([`53b37ca`](https://github.com/sadsfae/mozzo/commit/53b37cac4a0f098ccf2a943d07f4533c008bb4c2))

Allow for looking for a specific service across all hosts. e.g.

To list the status of DNS across all hosts:

mozzo --status --service "DNS"

You can also filter the results based on plugin status: 1 = PENDING; 2 = OK; 4 = WARNING; 8 =
  UNKNOWN; 16 = CRITICAL

mozzo --status --service "DNS" --filter 16

You can also directly see the results of the plugin output:

mozzo --status --service "DNS" --host foo.example.com --show-output

- Add features to list service across hosts
  ([`f984322`](https://github.com/sadsfae/mozzo/commit/f98432258f4913b8c992a161666673f023df6df7))

Allow for looking for a specific service across all hosts. e.g.

To list the status of DNS across all hosts:

mozzo --status --service "DNS"

You can also filter the results based on plugin status: 1 = PENDING; 2 = OK; 4 = WARNING; 8 =
  UNKNOWN; 16 = CRITICAL

mozzo --status --service "DNS" --filter 16

You can also directly see the results of the plugin output:

mozzo --status --service "DNS" --host foo.example.com --show-output

- Refactoring and add plugin output.
  ([`d4da3d1`](https://github.com/sadsfae/mozzo/commit/d4da3d1f39ad3705cff563f24cf19a1c85a203fe))

* refactor --output-filter to use a data structure filter_map.get() * use private helper method so
  any new changes to things like output columns only need to be updated in one place via
  _def_print_service_results * make --output-filter case insensitive * use fstrings to remove number
  of print lines


## v0.4.1 (2026-02-26)

### Bug Fixes

- Individual service status not working
  ([`460c097`](https://github.com/sadsfae/mozzo/commit/460c09708b17e6d59e9ac5860f8e2ddb2afbf504))

### Chores

- Update docs
  ([`160b172`](https://github.com/sadsfae/mozzo/commit/160b172c7e3abe20db834fa67c3a317c7e420596))


## v0.4.0 (2026-02-26)

### Chores

- Add mass ack one-liner to docs
  ([`213aa83`](https://github.com/sadsfae/mozzo/commit/213aa83e500a7598eebe1ce3900d25c12f8e3bea))

- Clean up debug comments
  ([`61c771a`](https://github.com/sadsfae/mozzo/commit/61c771a46dbc03807b3e296dd6c513c16b140149))

- Readme typo
  ([`42d1404`](https://github.com/sadsfae/mozzo/commit/42d140453815e749556e5e05374dd3699c6101fe))

- Readme update
  ([`b847437`](https://github.com/sadsfae/mozzo/commit/b8474374f3d8fd41590fd99bf32d645ddc3c282f))

### Features

- Add uptime and service reporting.
  ([`6e598ea`](https://github.com/sadsfae/mozzo/commit/6e598ea71a02cf6a8ce01534232550f73c4354e1))

* Add ability to query nagios archive CGI for host and service uptime. * Add ability to export
  format to JSON or CSV

fixes: https://github.com/sadsfae/mozzo/issues/23


## v0.3.0 (2026-02-25)

### Features

- Allow disable services per host or all.
  ([`5326d02`](https://github.com/sadsfae/mozzo/commit/5326d0224ce13cc3ebb6535f82b054595bb7d175))

fixes: https://github.com/sadsfae/mozzo/issues/18


## v0.2.2 (2026-02-25)

### Bug Fixes

- Bump ver and minor doc edit
  ([`1c31ffa`](https://github.com/sadsfae/mozzo/commit/1c31ffa06ff3781cc734e6d1849dd76e60801a83))

### Chores

- Add coc
  ([`89123dc`](https://github.com/sadsfae/mozzo/commit/89123dc7bad082527cf3e6e4b76f3fb492c32729))

- Align TOC
  ([`5d26d65`](https://github.com/sadsfae/mozzo/commit/5d26d65c3325aa3c77a4071c32daa2e38d6a88e6))

- Doc update
  ([`03a5cbd`](https://github.com/sadsfae/mozzo/commit/03a5cbd3541960c07eae960ec56f800be6d16e28))

- Doc updates
  ([`95c3101`](https://github.com/sadsfae/mozzo/commit/95c31012cc46a17bac8f829088f96cb78025bad9))

- Docs update
  ([`ea69015`](https://github.com/sadsfae/mozzo/commit/ea69015d2333e245eb2c0e3eed997d4f13ef565f))

- Use fury.io for badges
  ([`2c92546`](https://github.com/sadsfae/mozzo/commit/2c9254634bfdd4dfc9464d905d56e665aa365111))


## v0.2.1 (2026-02-25)

### Bug Fixes

- Correct status check.
  ([`8fb89c4`](https://github.com/sadsfae/mozzo/commit/8fb89c47bc6d47720455db2523c3e386fba7a2b2))

* We were referencing the wrong JSON keys so our --status call was incorrect.

fixes: https://github.com/sadsfae/mozzo/issues/6


## v0.2.0 (2026-02-25)

### Bug Fixes

- Root wrapper import for flake8
  ([`96fd19d`](https://github.com/sadsfae/mozzo/commit/96fd19dc78ecc875fe591657be90383831f10b91))

### Chores

- Docs
  ([`e113046`](https://github.com/sadsfae/mozzo/commit/e113046e9912566de78d3f86f12f41592462aa18))

- More doc updates
  ([`5970f92`](https://github.com/sadsfae/mozzo/commit/5970f92b6d84c146c18b8253badfd1995fec0082))

### Features

- Add ability for custom message on ack/downtime
  ([`af584cc`](https://github.com/sadsfae/mozzo/commit/af584cc82d2181806e4a825e48aa011353a851a7))

fixes: https://github.com/sadsfae/mozzo/issues/3


## v0.1.0 (2026-02-25)

### Features

- Minor but update pypi version and GH rel
  ([`75676fc`](https://github.com/sadsfae/mozzo/commit/75676fc4c92a639f7e7a65abed77f3ea9ce0ae31))


## v0.0.0 (2026-02-25)
