# sphinx-ford — Design Plan

Sphinx domain for Fortran with a FORD bridge for automatic documentation.

## Decisions

- **Domain name:** `f` — if sphinx-fortran is also loaded, `setup()` detects the conflict and raises `ExtensionError` with a clear message
- **FORD dependency:** optional (domain works standalone, bridge requires FORD ≥ 6.1)
- **Build system:** setuptools
- **Case handling:** all Fortran identifiers are stored lowercase in the domain inventory; `resolve_xref()` normalizes lookup keys to lowercase; display names preserve original casing
- **Doc comment format:** FORD doc comments are Markdown; the bridge converts them to RST using a lightweight Markdown→RST converter (no external dependency — handle basic formatting, code blocks, and `[[entity]]` links; complex Markdown degrades gracefully)
- **Ignore** existing sphinx-fortran project

## Example Projects

Five FORD-using projects to validate against:

| Project | FORD file | Existing FORD docs | Complexity |
|---|---|---|---|
| [fortran-lang/stdlib](https://github.com/fortran-lang/stdlib) | `API-doc-FORD-file.md` | [stdlib.fortran-lang.org](https://stdlib.fortran-lang.org/) | Large — many modules, interfaces, fypp-generated types |
| [fortran-lang/fpm](https://github.com/fortran-lang/fpm) | `docs.md` | — | Medium — modules, derived types, procedures |
| [toml-f/toml-f](https://github.com/toml-f/toml-f) | `docs.md` | [toml-f.github.io/toml-f](https://toml-f.github.io/toml-f) | Medium — clean OOP design, type hierarchy |
| [cp2k/dbcsr](https://github.com/cp2k/dbcsr) | `DBCSR.md` (CMake-templated) | [cp2k.github.io/dbcsr](https://cp2k.github.io/dbcsr/) | Large — MPI/OpenMP parallel, CUDA/HIP, sparse matrix ops |
| [apes-suite/aotus](https://github.com/apes-suite/aotus) | `aot_mainpage.md` | [apes-suite.github.io/aotus](https://apes-suite.github.io/aotus/) | Small — Lua/Fortran interop, C-API wrapper |

These cover: large stdlib with generated interfaces, a build tool (fpm), a parser library (toml-f), a high-performance parallel linear algebra library (dbcsr), and a Lua scripting interface for Fortran (aotus).

## Architecture

```
sphinx-ford/
├── src/
│   └── sphinx_ford/
│       ├── __init__.py          # setup() entry point
│       ├── domain.py            # FortranDomain, all directives, roles, indices
│       ├── ford_bridge.py       # FORD bridge: load projects, automodule/autoproject
│       ├── _ford_compat.py      # FORD 6/7 API compatibility layer
│       ├── _md2rst.py           # Markdown → RST converter for FORD doc comments
│       └── ford_parser.py       # FORD JSON import, objects.inv, reverse export
├── tests/
│   ├── conftest.py              # Shared fixtures, tarball download, example project cache
│   ├── roots/                   # RST test fixtures (one subdir per test scenario)
│   │   ├── test-module/         # Module with nested functions, types, variables
│   │   ├── test-nesting/        # Module > type > bound procedure scoping
│   │   ├── test-xref/           # Cross-references between entities
│   │   ├── test-html/           # HTML build integration
│   │   └── test-ford-bridge/    # FORD bridge integration (dynamic config)
│   ├── test_domain.py           # Domain registration, data storage, xrefs, index
│   ├── test_nesting.py          # Nested scoping, procedure index, type index
│   ├── test_md2rst.py           # Markdown → RST converter
│   ├── test_ford_bridge.py      # FORD API bridge, module-to-RST, integration
│   ├── test_ford_parser.py      # FORD JSON import, objects.inv, reverse export
│   └── test_integration.py      # HTML builds, cross-references, objects.inv
├── docs/
│   ├── conf.py
│   ├── index.rst
│   ├── fetch_examples.py        # Tarball download + SHA256 verification + cache
│   ├── tutorials/
│   │   ├── getting-started.rst
│   │   └── ford-bridge.rst
│   ├── how-to/
│   │   ├── document-module.rst
│   │   ├── cross-reference.rst
│   │   └── intersphinx.rst
│   ├── reference/
│   │   ├── directives.rst
│   │   ├── roles.rst
│   │   └── configuration.rst
│   ├── explanation/
│   │   └── design.rst
│   └── examples/                # Auto-generated from FORD sources
│       ├── index.rst
│       ├── toml-f.rst
│       ├── fpm.rst
│       ├── stdlib.rst
│       ├── dbcsr.rst
│       └── aotus.rst
├── pyproject.toml
└── PLAN.md
```

## Domain Design

**Domain name:** `f`
**Namespace separator:** `.` (e.g., `module_name.type_name.component`)
**Case handling:** all identifiers stored lowercase; display names preserve original case

### Entity types and directives

| Fortran entity | Directive | Role | Notes |
|---|---|---|---|
| Module | `f:module::` | `:f:mod:` | Top-level container, tracks `use` dependencies |
| Submodule | `f:submodule::` | `:f:submod:` | Parent module/submodule reference |
| Program | `f:program::` | `:f:prog:` | |
| Function | `f:function::` | `:f:func:` | Signature with args + return type |
| Subroutine | `f:subroutine::` | `:f:subr:` | Signature with args |
| Derived type | `f:type::` | `:f:type:` | Tracks extends, components, bound procedures |
| Variable | `f:variable::` | `:f:var:` | Type, kind, intent, attributes |
| Interface | `f:interface::` | `:f:iface:` | Generic and abstract |
| Enum | `f:enum::` | `:f:enum:` | |
| Bound procedure | `f:boundproc::` | `:f:bp:` | Type-bound proc with deferred/generic |
| Block data | `f:blockdata::` | `:f:block:` | |
| Common block | `f:common::` | `:f:common:` | |
| Namelist | `f:namelist::` | `:f:nml:` | |
| Current module | `f:currentmodule::` | — | Context-setting directive (like `py:currentmodule`), no output |

**Name disambiguation:** Fortran allows a module and a type to share the same name. Domain objects are keyed by FQN string (lowercase). Modules store as bare names (e.g., ``toml_table``), while types store with a module prefix (e.g., ``toml_table.toml_table``), so they don't collide. Typed roles (`:f:mod:` vs `:f:type:`) resolve unambiguously; `resolve_any_xref()` returns all matches with priority (modules > types > procedures).

### Directive options (common)

- `:module:` — parent module context
- `:permission:` — `public` / `private` / `protected`
- `:noindex:` — suppress index entry
- `:noindexentry:` — suppress general index entry

### Procedure-specific fields (doc fields in body)

- `:param name:` / `:p name:` — argument description
- `:ftype name:` — argument type declaration (named `ftype` to avoid collision with Sphinx's built-in `:type:` field and the `f:type` directive)
- `:intent name:` — `in`, `out`, `inout`
- `:optional name:` — flag optional arguments
- `:returns:` — return value description (functions)
- `:rtype:` — return type

### Example usage

```rst
.. f:module:: toml_table
   :permission: public

   TOML table data structure.

   .. f:type:: toml_table
      :extends: toml_value

      Ordered key-value mapping.

      .. f:boundproc:: has_key
         :deferred:

         Check if key exists.

.. f:function:: toml_parse(config, table, error)

   Parse a TOML document.

   :param config: Input string
   :ftype config: character(len=*)
   :intent config: in
   :param table: Parsed table
   :ftype table: type(toml_table), allocatable
   :intent table: out
   :param error: Error info
   :ftype error: type(toml_error), allocatable
   :intent error: out
```

Cross-reference: ``:f:func:`toml_table.has_key``` or ``:f:mod:`toml_table```

## FORD Bridge

### Options evaluated

#### Option A: FORD internal API (recommended)

Use FORD's Python API directly: `ford.parse_arguments()` → `ford.fortran_project.Project()` → `project.correlate()`.

**How it works:**
1. Read the FORD project file (e.g., `docs.md`) as a string
2. Call `ford.parse_arguments(command_line_args={}, proj_docs=content, directory=base_dir)` — returns `(proj_data, proj_docs, md)` with all settings resolved, paths normalized, preprocessor validated
3. Call `ford.fortran_project.Project(proj_data)` — scans source dirs, parses all Fortran files, populates `project.modules`, `.procedures`, `.types`, `.submodules`, `.programs`, `.blockdata`, `.absinterfaces`
4. Walk the `Project` object tree and map entities into the Sphinx domain

Note: `project.correlate()` is **not** called — it crashes on FORD 6.1.15 (see M0 findings). All needed data is available from `Project()` alone. FORD 7 fixes this bug.

**Feasibility: HIGH**
- `ford.parse_arguments()` accepts a plain dict (no argparse needed), a string of project docs, and a base directory — perfect for programmatic use
- `Project.__init__()` only needs the `proj_data` dict (79 keys, all have defaults)
- `project.correlate()` is self-contained, no HTML/Markdown processing required for our purposes
- We skip `project.markdown()`, `project.make_links()`, and `ford.output` entirely — those produce HTML, which we don't need
- All entity attributes (name, doc comments, permission, args, types, kind, intent, extends) are directly accessible as Python attributes on the FORD objects

**Rich data model available post-correlate:**
- `FortranModule`: `.name`, `.doc`, `.permission`, `.functions`, `.subroutines`, `.types`, `.variables`, `.interfaces`, `.absinterfaces`, `.uses`, `.pub_procs`, `.pub_types`, `.pub_vars`
- `FortranFunction`/`FortranSubroutine`: `.name`, `.doc`, `.args` (list of `FortranVariable`), `.retvar`, `.proctype`, `.attribs`, `.permission`
- `FortranType`: `.name`, `.doc`, `.extends`, `.variables`, `.boundprocs`, `.finalprocs`, `.constructor`, `.permission`
- `FortranVariable`: `.name`, `.doc`, `.vartype`, `.kind`, `.strlen`, `.intent`, `.optional`, `.parameter`, `.attribs`, `.initial`, `.permission`
- `FortranInterface`: `.name`, `.generic`, `.abstract`, `.modprocs`, `.contents`
- `FortranBoundProcedure`: `.name`, `.doc`, `.deferred`, `.generic`, `.bindings`

**Risks and mitigations:**
- **No stable API:** FORD has no public API guarantees. Mitigated by: pinning to FORD ≥ 6.1 (current conda-forge version: 6.1.15); wrapping all FORD imports in a thin `_ford_compat.py` abstraction layer that can adapt to API changes; comprehensive bridge tests that run against the pinned FORD version in CI.
- **`correlate()` crash — FORD 6.1.15 bug (all Python versions):** FORD 6.1.15's `prune()` (called by `correlate()`) crashes with `AttributeError: 'FortranFunction' object has no attribute 'meta'`. **Verified on Python 3.12.13, 3.13.12, and 3.14.3** — this is a FORD bug, not Python-version-specific. **Finding from M0 spike:** `correlate()` is not needed for the primary use case — all module contents (functions, subroutines, types, variables, interfaces) with args, doc comments, types, intents, and permissions are available directly from `Project()` without calling `correlate()`. `correlate()` only resolves cross-module USE references and type inheritance links, which we can handle in the Sphinx domain via cross-reference resolution instead. **Decision: skip `correlate()` for now; add it back when FORD fixes the bug or when we need USE-graph data.**
- **stdout noise:** `Project()` and `correlate()` print progress to stdout. Mitigated by wrapping calls in `contextlib.redirect_stdout(io.StringIO())`.
- **`sys.exit()` in `parse_arguments()`:** FORD calls `sys.exit()` on preprocessor validation failure instead of raising. Mitigated by catching `SystemExit` in the bridge and converting to `sphinx.errors.ExtensionError` with the original message.
- **Preprocessor requirement:** sources with `fpp_extensions` need a C preprocessor. Mitigated by: adding a `ford_preprocess` config option (default `True`) to allow disabling preprocessing; documenting the requirement clearly.
- **I/O in `Project.__init__()`:** reads all source files synchronously during `builder-inited`, which can be slow for large projects (stdlib: ~200 files, dbcsr: ~300 files). Mitigated by: logging elapsed time; exploring pickle-based caching of the `Project` object keyed by source file mtimes in a future milestone.
- **CMake-templated project files:** DBCSR's `DBCSR.md` contains `@CMAKE_SOURCE_DIR@` placeholders. Mitigated by: adding a `ford_project_vars` config dict for variable substitution (e.g., `ford_project_vars = {"CMAKE_SOURCE_DIR": "/path/to/dbcsr"}`); the bridge replaces `@VAR@` patterns before passing to `parse_arguments()`.
- **Doc comment format:** FORD doc comments are Markdown stored as list of strings (lines), not HTML. Mitigated by: joining lines and converting via a lightweight `_md2rst.py` converter that handles: paragraphs, code blocks, inline code, bold/italic, lists, headings, and `[[entity]]` → `:f:func:\`entity\`` translation. Complex Markdown (tables, nested structures) passes through as literal blocks rather than crashing.

#### Option B: FORD JSON export (`modules.json`)

Load a pre-built `modules.json` from a FORD output directory.

**How it works:**
1. Point to an existing FORD output directory containing `modules.json`
2. Parse the JSON (list of module dicts with nested procedures, types, variables)
3. Map to domain objects

**Feasibility: HIGH but LIMITED**
- JSON only contains **public module-level** data — designed for cross-project linking, not full documentation
- Missing from JSON: docstrings, programs, block data, submodules, common blocks, namelists, procedure arguments/signatures, private entities
- Useful only for cross-project linking (like intersphinx), not for primary documentation generation

#### Option C: Run FORD as subprocess

Run `ford` as a CLI command, then scrape its output.

**Feasibility: LOW — not recommended**
- FORD produces HTML output, not structured data we can consume
- Would need to parse HTML or the `modules.json` (which is Option B)
- Extra overhead of subprocess management, temp directories, cleanup
- No advantage over Option A

### Decision

**Primary: Option A** (FORD internal API via `parse_arguments` + `Project`)
**Secondary: Option B** (JSON import for cross-project linking only)

### Implementation

- Sphinx config values:
  - `ford_project_file` — path to FORD project file (triggers Option A). This is the **primary and recommended** config.
  - `ford_project_files` — list of FORD project files (string or dict with `path`, `vars`, `preprocess` overrides). Modules from all projects are merged.
  - `ford_project_vars` — dict of `{"VAR": "value"}` for substituting `@VAR@` patterns in CMake-templated FORD project files (e.g., dbcsr)
  - `ford_preprocess` — bool (default `True`), set to `False` to skip preprocessing even if `fpp_extensions` is set in the FORD project file
  - `ford_export_modules_json` — bool (default `False`), export FORD-compatible `modules.json` to output dir after build
- The bridge runs at `builder-inited` event, populates the domain's object inventory
- Each FORD entity maps to the corresponding domain directive, generating RST-equivalent nodes
- FORD is imported lazily; missing FORD raises `ExtensionError` only when bridge features are used
- `SystemExit` from FORD is caught and converted to `ExtensionError`
- All FORD calls wrapped in `contextlib.redirect_stdout()` to suppress progress output
- `project.markdown()` and `project.make_links()` are **not** called — doc comments are converted from Markdown to RST by `_md2rst.py` and then processed by Sphinx

## Milestones

### M0 — Spike: validate domain design against real FORD output ✅ DONE
- Minimal FORD bridge prototype: load one example project (toml-f v0.5.0) via FORD API
- Dump entity tree to confirm attribute availability and naming
- Verify case handling, doc comment format, and scoping assumptions
- **Gate:** confirm the domain entity model before implementing M1

**M0 findings:**
- `ford.parse_arguments()` + `ford.fortran_project.Project()` works perfectly for programmatic use
- toml-f: 35 files, 35 modules parsed with full entity trees
- `project.correlate()` crashes on FORD 6.1.15 — **verified on Python 3.12, 3.13, and 3.14** (`AttributeError: 'FortranFunction' object has no attribute 'meta'` in `prune()`). This is a FORD bug, not Python-version-specific.
- **All needed data is available without `correlate()`**: module contents (functions, subroutines, types, variables, interfaces) with args, doc comments, types, intents, permissions, extends
- Doc comments are `list[str]` (lines of Markdown), not HTML
- Entity names preserve original case (lowercase normalization done by our domain)

### M1 — Domain skeleton ✅ DONE — tested on Python 3.12, 3.13, 3.14
- Package scaffolding (pyproject.toml, setuptools, src layout)
- `FortranDomain` with all 13 entity directives + `currentmodule`
- Case-insensitive name storage and lookup
- Cross-references and `resolve_xref()` with case normalization
- Module index
- Conflict detection with sphinx-fortran in `setup()`
- 21 tests passing (domain registration, data storage, cross-references, module index)

### M2 — Full entity coverage ✅ DONE
- All remaining entity types (interface, enum, bound procedure, submodule, etc.)
- Nested scoping (module → type → bound procedure) with context stacks
- Name disambiguation for same-name module/type
- Procedure index, type index

### M3 — FORD bridge (API mode) ✅ DONE
- `_ford_compat.py` abstraction layer over FORD 6.x and 7.x
- `_md2rst.py` Markdown→RST converter for doc comments
- Invoke FORD's parser on source files via `_load_ford_project()`
- Map FORD data model → domain objects via `_module_to_rst()`
- `f:automodule` and `f:autoproject` directives
- `SystemExit` handling, stdout redirection, CMake variable substitution
- Validated against toml-f with both FORD 6 and FORD 7

### M4 — FORD bridge (JSON mode) + intersphinx ✅ DONE
- Load `modules.json` via `ford_parser.parse_modules_json()`
- Generate `objects.inv` via `ford_parser.generate_objects_inv()`
- Reverse export domain → `modules.json` via `ford_parser.domain_to_ford_json()`
- `ford_export_modules_json` config: auto-export on `build-finished` event
- Use qualified names `module.entity` in inventory to avoid collisions
- Note: `ford_intersphinx_mapping` auto-fetch config is deferred to M6

### M5 — CI and documentation ✅ DONE
- GitHub Actions CI workflow with matrix testing ✅
- Diátaxis docs structure ✅
- Example project rendering ✅ (all 5 projects with auto-documentation)

## Documentation plan (Diátaxis framework)

The documentation follows the [Diátaxis framework](https://diataxis.fr/).

| Quadrant        | Orientation          | Purpose                        | Mode     |
|-----------------|----------------------|--------------------------------|----------|
| **Tutorials**   | Learning-oriented    | Acquire skills by doing        | Studying |
| **How-to**      | Task-oriented        | Solve a specific problem       | Working  |
| **Reference**   | Information-oriented | Look up facts about machinery  | Working  |
| **Explanation** | Understanding-oriented | Deepen conceptual knowledge  | Studying |

### Tutorials — "learning by doing under guidance"
- *We* language. "In this tutorial we will create..."
- Show concrete results early and often.
- Ruthlessly minimise explanation — link to explanation pages instead.
- Ignore options and alternatives — one happy path only.
- Aspire to perfect reliability (every step must produce the expected result).

### How-to guides — "recipes for the competent user"
- Addressed to a real-world problem the user already knows they have.
- Title: "How to ‹verb› ‹object›" — imperative, goal-oriented.
- Assume competence — the reader is not a beginner.
- No teaching, no digression, no reference listings inside the guide.
- Action-only: conditional imperatives ("If you need X, do Y").

### Reference — "the authoritative map"
- Austere, authoritative, complete.
- Structured to mirror the product (directives → roles → config).
- Provide minimal examples for illustration, not instruction.
- No explanation, no how-to guidance embedded.

### Explanation — "understanding around a topic"
- Discursive — permits reflection, context, opinion.
- Answers "why?" and "how does this relate to...?"
- Title phrasing: "About ‹topic›".
- Make connections to broader ecosystem (FORD, sphinx-fortran, C++ domain).
- Not read while working — read when thinking.

### Documentation structure

```
docs/
├── tutorials/
│   ├── getting-started.rst      # End-to-end: install → document → build → see result
│   └── ford-bridge.rst          # End-to-end: install FORD → configure → automodule → build
├── how-to/
│   ├── document-module.rst      # How to structure nested module documentation
│   ├── cross-reference.rst      # How to cross-reference Fortran entities
│   ├── intersphinx.rst          # How to set up cross-project linking
│   ├── ford-project.rst         # How to auto-document a FORD project
│   └── parameter-constants.rst  # How to document parameters and type members
├── reference/
│   ├── directives.rst           # All directives with options and examples
│   ├── roles.rst                # All roles with usage examples
│   └── configuration.rst        # All conf.py values
├── explanation/
│   ├── design.rst               # About the design of sphinx-ford
│   ├── ford-bridge.rst          # About the FORD bridge architecture
│   └── markdown-conversion.rst  # About Markdown-to-RST conversion
└── examples/                    # Showcase: auto-generated from real FORD projects
```

## Coverage Comparison: sphinx-ford vs Published FORD Docs

### Module-level coverage

| Project | Published FORD modules | sphinx-ford modules | Coverage | Gap reason |
|---|---|---|---|---|
| toml-f | 35 | 35 | **100%** | — |
| fpm | ~50 | 47 | **~94%** | 3 files with parse errors (FORD 6.1.15 bug) |
| aotus | ~15 | 37* | **100%+** | *includes C-binding modules not in published docs |
| stdlib | ~80 | 58 | **~73%** | fypp-only modules need preprocessing to produce .f90 |
| dbcsr | ~80 | 70 | **~88%** | .F files with CPP directives, some parse failures |

### Entity-level coverage (per rendered module)

For modules that load successfully, entity coverage is equivalent to FORD:
- ✅ Module doc comments (Markdown → RST)
- ✅ Module dependencies (uses)
- ✅ Functions with pure/elemental attributes, full parameter types/intents
- ✅ Subroutines with parameters
- ✅ Derived types with components (type, initial value, attributes)
- ✅ Interfaces (generic/abstract) with member procedures
- ✅ Bound procedures (deferred/generic)
- ✅ Type constructors
- ✅ Variables with type declarations

### Known discrepancies

1. **stdlib: fypp-generated modules missing** — stdlib_io, stdlib_string_type, stdlib_math etc. exist only as `.fypp` templates. FORD preprocesses them with `fypp` to produce `.f90` files that contain the actual Fortran. Our bridge uses fypp preprocessing (available in the environment) but some modules fail to parse due to FORD 6.1.15 bugs with the `_cleanup` method. Fypp macros like `MAXRANK` produce template-expanded code that FORD parses correctly when run standalone but fails through our bridge.

2. **dbcsr: dbcsr_api module missing** — The main public API module `dbcsr_api.F` uses extensive CPP preprocessor directives (`#if`, `#ifdef`) that FORD needs `cpp` to preprocess. Our bridge disables preprocessing for dbcsr (no `cpp` in docs environment) which means `.F` files are parsed as-is. The CPP directives confuse FORD's parser.

3. **No source file links** — FORD generates links to source files; sphinx-ford does not (Sphinx doesn't have this concept natively).

4. **No dependency graphs** — FORD generates module/type dependency graphs; sphinx-ford does not (requires `correlate()` which crashes on FORD 6.1.15).

5. **No page tree** — FORD supports a page tree (extra documentation pages); sphinx-ford uses Sphinx's native toctree instead.

### Future milestone: M6 — Full coverage

To achieve 100% coverage for all 5 projects:

- **Run fypp preprocessing as a separate step** before invoking FORD's parser. Add a `ford_preprocess_cmd` config that runs an external preprocessor on source files, writing `.f90` output to a temp directory, then pointing FORD at the temp directory. This decouples the FORD parser from the preprocessing.
- **Require FORD 7** for stdlib and dbcsr examples — FORD 7 fixes the `_cleanup` and `correlate()` bugs, and handles `.F` file preprocessing correctly.
- **Add `cpp` to docs dependencies** for dbcsr (or use `gcc -E` as the preprocessor).
- **Source file links** — add a `ford_source_url` config that generates links to GitHub source files from module/function metadata.
- **Dependency graphs** — use FORD 7's `correlate()` to build USE graphs, then render them via Sphinx's graphviz extension or Mermaid.

### CI test matrix (GitHub Actions)

| Python | Sphinx | FORD | Notes |
|---|---|---|---|
| 3.12 | 6.0 | 6.1 | Oldest supported combination |
| 3.12 | 7.x | 6.1 | Mid-range Sphinx |
| 3.13 | 9.x | 6.1 | Latest Sphinx + FORD 6 |
| 3.13 | 9.x | 7.x | Latest Sphinx + FORD 7 |
| 3.14 | 9.x | 6.1 | Bleeding edge Python |
| 3.14 | 9.x | 7.x | Bleeding edge Python + FORD 7 |

**Known limitations:**
- Sphinx 6.x test fixtures (`sphinx.testing`) are incompatible with Python 3.14 (`Path.copytree` missing). Domain and bridge code work, but `pytest.mark.sphinx` tests fail. CI marks this combination as `allow-failure`.
- FORD 6.1.15 `correlate()` crashes on all Python versions (FORD bug). Bridge works without `correlate()`.
- FORD 7 `correlate()` works on all Python versions.

**Workflow triggers:** push, pull_request, weekly schedule (to catch upstream breakage).

## Intersphinx

Three cross-linking scenarios to support:

### 1. sphinx-ford → sphinx-ford (native intersphinx)

Standard Sphinx intersphinx. sphinx-ford generates `objects.inv` automatically because the domain registers objects through `get_objects()`. No extra work beyond implementing the domain correctly.

**How it works:**
- Sphinx's built-in `sphinx.ext.intersphinx` reads `objects.inv` from remote sphinx-ford projects
- The `f` domain objects appear in the inventory with entries like `f:mod`, `f:func`, `f:type`, etc.
- Cross-references resolve via `:f:mod:\`tomlf\`` pointing to the remote sphinx-ford project

**Config (in downstream project's `conf.py`):**
```python
intersphinx_mapping = {
    "toml-f": ("https://toml-f.readthedocs.io/", None),
}
```

**No additional implementation needed** — this is free from implementing the Sphinx domain correctly.

### 2. sphinx-ford → FORD-generated pages (FORD inventory bridge)

Link from a sphinx-ford project to an existing FORD-generated site (e.g., link to stdlib's FORD docs at `stdlib.fortran-lang.org`).

**Challenge:** FORD does not produce `objects.inv`. FORD's URL scheme is:
- Modules: `{base}/module/{name}.html`
- Procedures: `{base}/proc/{name}.html`
- Types: `{base}/type/{name}.html`
- Interfaces: `{base}/interface/{name}.html`
- Programs: `{base}/program/{name}.html`
- Source files: `{base}/sourcefile/{name}.html`
- Variables/bound procs within types: `{base}/type/{type_name}.html#variable-{var_name}`

**Solution: Generate `objects.inv` from FORD's `modules.json`**

Provide a CLI tool or Sphinx extension that reads `modules.json` from a FORD project and produces a Sphinx-compatible `objects.inv` file. This can be:

1. **CLI tool** (`sphinx-ford-inventory`): Run offline to create `objects.inv` from a FORD output directory or remote `modules.json` URL. The generated inventory maps FORD entity names to their FORD HTML URLs using the URL scheme above.

2. **Sphinx config helper** (`ford_intersphinx_mapping`): A conf.py config value that takes FORD project URLs and auto-generates inventory entries at build time by fetching `modules.json`.

**Config:**
```python
# Option A: pre-generated inventory file
intersphinx_mapping = {
    "stdlib": ("https://stdlib.fortran-lang.org/", "stdlib-objects.inv"),
}

# Option B: auto-generate from FORD modules.json at build time
ford_intersphinx_mapping = {
    "stdlib": "https://stdlib.fortran-lang.org/",
    "toml-f": "https://toml-f.github.io/toml-f/",
}
```

**Inventory entry mapping:**

| FORD entity | `objects.inv` domain:type | Inventory key | URL pattern |
|---|---|---|---|
| Module | `f:mod` | `{name}` | `module/{name}.html` |
| Function | `f:func` | `{module}.{name}` | `proc/{name}.html` |
| Subroutine | `f:subr` | `{module}.{name}` | `proc/{name}.html` |
| Interface | `f:iface` | `{module}.{name}` | `interface/{name}.html` |
| Type | `f:type` | `{module}.{name}` | `type/{name}.html` |
| Variable (in type) | `f:var` | `{module}.{type}.{name}` | `type/{type}.html#variable-{name}` |
| Program | `f:prog` | `{name}` | `program/{name}.html` |

Inventory keys use qualified names (`module.entity`) to avoid collisions between same-named entities in different modules (e.g., two modules both having an `init` subroutine).

**Limitations:**
- `modules.json` only contains public module-level entities — private entities and programs won't be linkable
- Procedure argument details are not in the JSON, so only top-level name linking works
- This is best-effort: if FORD changes its URL scheme, the mapping needs updating

### 3. FORD → sphinx-ford (reverse direction)

Link from an existing FORD project to a sphinx-ford site.

**How it works:** FORD's `--external` / `external` config option loads `modules.json` from a URL. sphinx-ford can generate a FORD-compatible `modules.json` from its domain inventory, allowing FORD to link to sphinx-ford pages.

**Implementation:** A post-build hook (`build-finished` event) that writes `modules.json` to the output directory, mapping sphinx-ford domain objects to their Sphinx HTML URLs using FORD's expected JSON format. URLs are resolved from the builder's `get_target_uri()` method rather than hardcoded patterns, ensuring compatibility with different `html_file_suffix` settings and builder configurations.

This enables bidirectional linking: a FORD project can `use` a module documented by sphinx-ford and automatically get links to the sphinx-ford docs.

## Example source acquisition

The `docs/examples/` section requires Fortran source code from the 5 example projects. Strategy:

- **Tarball downloads** with SHA256 verification and local caching in `docs/_examples_src/` (gitignored). The `docs/fetch_examples.py` script downloads release tarballs on first build and caches them for subsequent builds.
- **Pinned versions:** each example project is pinned to a specific release tag (e.g., `stdlib@v0.8.1`, `toml-f@v0.5.0`) to ensure reproducible docs.
- **No external dependencies** beyond stdlib (`urllib`, `hashlib`, `tarfile`).
- **Licensing:** all example projects are open source (MIT, Apache-2.0, GPL-2.0, LGPL-3.0).

## Dependencies

- **Runtime:** sphinx ≥ 6.0
- **Optional:** ford ≥ 6.1 (for bridge modes)
- **Build:** setuptools
- **Test:** pytest ≥ 7.0
- **Docs:** sphinx-book-theme, ford ≥ 6.1, fypp

## Test Plan

78 tests across 6 test files. Tests use pytest with Sphinx's built-in test infrastructure (`sphinx.testing`).

### `test_domain.py` — Domain, directives, roles, index (21 tests)

- Domain registers with name `f` and all 13 object types
- All roles and directives registered correctly
- Objects populated after build with correct FQN keys
- Functions, subroutines, types, variables, interfaces get module-qualified names
- `get_objects()` yields correct tuples for intersphinx
- Case-insensitive storage (all FQNs lowercase)
- `clear_doc()` removes entries for a specific document
- Cross-reference resolution: by name, qualified name, case-insensitive, with module context
- `resolve_any_xref()` resolves `:any:` role references
- Missing target returns None
- Module index contains documented modules alphabetically

### `test_nesting.py` — Nested scoping, procedure/type indices (12 tests)

- Module > type > variable/boundproc nested FQNs
- Type context resets between types
- Module-level entities not inside type context
- Procedure index lists functions and subroutines with module context
- Type index lists derived types with module context

### `test_md2rst.py` — Markdown → RST converter (14 tests)

- None/empty input handling
- FORD `[[entity]]` → `:f:func:\`entity\`` cross-references
- Headings, code blocks, inline code (with role protection)
- Lists, bold/italic passthrough
- Real FORD doc comment from toml-f

### `test_ford_bridge.py` — FORD API bridge (6 tests)

- Load toml-f project via FORD API (tarball downloaded dynamically)
- Nonexistent file raises `ExtensionError`
- `@VAR@` substitution works
- Module-to-RST generation includes all entity types
- Integration test: `Sphinx()` with `confoverrides` builds and populates domain

### `test_ford_parser.py` — JSON import, objects.inv, reverse export (16 tests)

- Parse `modules.json` with correct objtypes and URLs
- Handle empty, malformed, null entries
- Generate `objects.inv` with zlib compression and correct format
- Domain → FORD `modules.json` export
- `ford_export_modules_json` config auto-exports on build-finished
- Default: no export unless explicitly enabled

### `test_integration.py` — HTML builds (6 tests)

- HTML build succeeds and produces `index.html`
- HTML contains module, function, type entities
- Cross-references produce `<a>` links
- `objects.inv` generated for intersphinx
