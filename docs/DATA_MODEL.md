# Data model

## Paper record

`data/papers.json`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | Unique, `p` followed by digits |
| `title` | string | yes | |
| `authors` | list of string | yes | Non-empty, no placeholder-looking names |
| `authors_truncated` | bool | no | True when the published list is longer |
| `organisation` | string | yes | |
| `org_type` | enum | yes | `institution`, `company`, `independent` |
| `year` | int | yes | 1900 to 2100 |
| `venue` | string | yes | |
| `doi` | string | conditional | Matches `10.NNNN/...`, or null |
| `arxiv` | string | conditional | `YYMM.NNNNN`, `archive/YYMMNNN`, optional version, or null |
| `abstract` | string | yes | |
| `tags` | list of string | yes | Non-empty, lower-cased on load |
| `difficulty` | enum | yes | `introductory`, `intermediate`, `advanced`, `research` |
| `algorithm_family` | string | yes | |
| `hardware_platform` | string | yes | |

At least one of `doi` or `arxiv` must be present, so every record is
traceable to a source.

### Organisation types

| Value | Meaning | Examples in the dataset |
| --- | --- | --- |
| `institution` | University or research institute | MIT, Caltech, Yale, NIST, RIKEN, Waterloo, Barcelona |
| `company` | Commercial research organisation | Google Quantum AI, IBM Research, Microsoft Research, AT&T Bell Labs, Bell Labs |
| `independent` | No institutional affiliation recorded | Author-led preprints |

### Editorial fields

`difficulty` and `hardware_platform` are classifications made by this project,
not claims made by the papers. They are labelled as such wherever they appear.

---

## Project record

`data/projects.json`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | Unique, `j` followed by digits |
| `title` | string | yes | |
| `category` | string | yes | |
| `difficulty` | enum | yes | Same four levels as papers |
| `implemented` | bool | yes | True when the code is in this repository |
| `module` | string | if implemented | Must import, and expose `entry_point` |
| `test_module` | string | no | Must exist as a file |
| `entry_point` | string | no | Must be an attribute of `module` |
| `correctness_evidence` | string | if implemented | How the work is verified |
| `url` | string | if external | Must start with `http` |
| `organisation` | string | no | For external projects |
| `org_type` | string | no | For external projects |
| `description` | string | yes | |
| `why_hard` | string | yes | The actual difficulty, not a label |
| `tags` | list of string | yes | Non-empty |

The `implemented` flag drives validation. An implemented project must name a
module and state its correctness evidence; an external project must supply an
HTTP URL. A test asserts every implemented project's module imports and its
entry point exists, which keeps the catalogue honest.

---

## Validation rules

The loader runs on import and raises `DatasetError` or `ProjectDataError` on:

- a missing required field
- a non-string or blank author name
- an author matching `^(?:[A-Z]\.\s*)+(?:S\.\s*)+$`, the signature of a
  placeholder that was never replaced with a real name
- an unknown organisation type or difficulty
- a year outside 1900 to 2100
- a malformed DOI or arXiv identifier
- a record with neither a DOI nor an arXiv identifier
- duplicate ids
- a JSON file that is unparseable or missing its top-level list

Failing fast at import means a bad dataset stops the app with one clear
message, rather than producing a confusing error inside a request handler.

---

## Provenance and honesty

- Bibliographic fields were compiled from the published record. **Check the
  linked DOI or arXiv identifier before citing anything here.**
- **Citation counts are deliberately omitted.** They change over time and
  reporting them accurately requires a live bibliographic source.
- The dataset is a small teaching sample, not a complete bibliography.
- `difficulty` and `hardware_platform` are editorial classifications.
- Star counts and other popularity metrics are omitted from project records for
  the same reason citation counts are omitted.

---

## Adding a paper

1. Append a record to `data/papers.json` with the next free `id`.
2. Run `python verify_requirements.py`.
3. Run `python -m pytest tests/test_repository.py -q`.

The new record must satisfy every validation rule above, and the tests check
that all three organisation types remain represented.

## Adding a project

1. Append a record to `data/projects.json` with the next free `id`.
2. For an implemented project, make sure `module` and `entry_point` resolve and
   that `test_module` exists.
3. Run `python -m pytest tests/test_repository.py -q`.

The integrity test will fail if the catalogue claims a module or entry point
that does not exist.
