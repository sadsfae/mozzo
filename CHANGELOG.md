# CHANGELOG


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
