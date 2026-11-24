# Building the docs

The documentation is MkDocs with the Material theme. There is one site per package plus a landing site, all built
by one script and deployed together to GitHub Pages.

| Site | Config | Pages | Served at |
|---|---|---|---|
| Landing | [`mkdocs.yml`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/mkdocs.yml) | `docs/` | `https://pnnl-cim-tools.github.io/CIMHub/` |
| cimhub-core | [`cimhub_core/mkdocs.yml`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/mkdocs.yml) | `cimhub_core/docs/` | `.../CIMHub/core/` |

Every site starts from
[`mkdocs.base.yml`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/mkdocs.base.yml), which holds the theme,
the Markdown extensions, the plugins and the `validation` settings. A site's own file begins with
`INHERIT: ../mkdocs.base.yml` (`INHERIT: mkdocs.base.yml` for the root one) and sets only `site_name`, `site_url`,
`site_description`, `edit_uri`, `extra.social` and its `nav`.

## Building

```bash
scripts/build-docs.sh               # every site, --strict: what CI runs
scripts/build-docs.sh core          # one package's site, into site/core/
scripts/build-docs.sh core --serve  # preview one site at http://127.0.0.1:8000
```

[`scripts/build-docs.sh`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/scripts/build-docs.sh) runs MkDocs
through `uvx` with the pinned tools in `docs/requirements.txt` (`mkdocs-material`, `mkdocs-jupyter`), so the docs
tools never touch the workspace's `uv.lock`. With no argument it deletes `site/`, builds the landing site into
`site/`, then builds each package in `SITES` into `site/<pkg>/`. That layout is what GitHub Pages serves. `--strict`
turns warnings into failures, so a broken link or a missing heading anchor fails the build. `site/` is git-ignored.

To check one site while another writer is editing, build to a scratch directory:

```bash
NO_MKDOCS_2_WARNING=1 uvx --python 3.13 --with-requirements docs/requirements.txt \
    mkdocs build --strict -f cimhub_core/mkdocs.yml -d /tmp/core-site
```

## CI and deployment

[`.github/workflows/docs.yml`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.github/workflows/docs.yml)
runs `scripts/build-docs.sh` on a pull request or push that touches `docs/`, `mkdocs*.yml`, `cimhub_*/docs/`,
`cimhub_*/mkdocs.yml`, a spoke's `schema/` directory or the script itself. A push to `develop` also uploads `site/` and
deploys it to GitHub Pages. The job does not install the packages, so nothing in the docs build can import them.

## Shared theme

The theme is [`docs/stylesheets/extra.css`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/docs/stylesheets/extra.css),
written against Material's CSS variables only, and the favicon is in `docs/assets/`. Each package site reaches them
through symlinks, because MkDocs only serves files under a site's own `docs/`:

```
cimhub_core/docs/stylesheets -> ../../docs/stylesheets
cimhub_core/docs/assets      -> ../../docs/assets
```

`mkdocs.base.yml` sets `extra_css: stylesheets/extra.css` and `favicon: assets/favicon.svg`. Change the theme once
in `docs/` and every site follows.

## Notebooks

Notebooks are pages (`nav` lists `guide/quickstart.ipynb`) and are stored with their outputs. The build does not run
them (`execute: false` in the `mkdocs-jupyter` plugin), which is why CI needs no packages. After changing a notebook,
or the behaviour it shows, re-run it in place and commit the result:

```bash
cd cimhub_core/docs/guide && uv run --with jupyter --with ipykernel jupyter nbconvert --to notebook --execute --inplace quickstart.ipynb
```

A notebook's input files (`.cimtbl` or other fixtures it reads) live beside it in `guide/`. List them under
`not_in_nav` in the site's `mkdocs.yml`, as the core site does for `guide/*.cimtbl`, so MkDocs does not report them as
pages missing from the nav.

## The schema reference

A spoke's page set includes an API reference of its native LinkML schema. It is generated at build time with
`gen-doc` and never committed. In `scripts/build-docs.sh`, the `SCHEMA` table maps a package to its root schema file,
relative to `cimhub_<pkg>/` (the table is empty today; an entry looks like this):

```bash
declare -A SCHEMA=(
    [opendss]=src/cimhub_opendss/schema/linkml/opendss.yaml
)
```

Before building a package, `generate_schema_reference` deletes `cimhub_<pkg>/docs/schema/` and runs
`uvx --python 3.13 --from linkml gen-doc -d cimhub_<pkg>/docs/schema <root schema>`. A package with no entry is
skipped, and the table is empty today because only the core site has moved to this template. `.gitignore` lists
`cimhub_*/docs/schema/`. The site's `nav` points at `schema/index.md`, which exists only after generation, so
preview a spoke with `scripts/build-docs.sh <pkg> --serve` (which generates first) rather than bare `mkdocs serve`.
The generated pages that are not in the nav are reported at info level, not as warnings. The `schema/**` path in the
workflow's triggers means a schema change rebuilds the docs.

The schema's `description` fields are the page text, so the reference is only as good as the
[LinkML schema](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/linkml-native-schema/SKILL.md).

## Adding a package site

1. Write `cimhub_<pkg>/mkdocs.yml`. Start it with `INHERIT: ../mkdocs.base.yml`, then `site_name`, `site_url`
   (`https://pnnl-cim-tools.github.io/CIMHub/<pkg>/`), `site_description`, `edit_uri`
   (`edit/develop/cimhub_<pkg>/docs/`), `extra.social` and a `nav`. Copy
   [`cimhub_core/mkdocs.yml`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/mkdocs.yml).
2. Link the shared theme from inside `cimhub_<pkg>/docs/`:

    ```bash
    cd cimhub_<pkg>/docs
    ln -s ../../docs/stylesheets stylesheets
    ln -s ../../docs/assets assets
    ```

3. Add the package to `SITES` in `scripts/build-docs.sh`, and to `SCHEMA` if it has a LinkML schema reference.
4. Add a card for it on the landing page, `docs/index.md`.
5. Run `scripts/build-docs.sh <pkg>`, then `scripts/build-docs.sh` for the whole set.

Retire a package's old, standalone `mkdocs.yml` when its site moves to the template; the script builds only the
packages listed in `SITES`.

## Conventions

- Pages inside a site link to each other with relative `.md` links. Anything outside the site's `docs/` is an
  absolute GitHub URL (`https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/<path>` for a file, `.../tree/develop/<path>`
  for a directory), because the build cannot resolve it.
- `validation.anchors: warn` means a link to a heading that does not exist fails `--strict`. Link to a page, not an
  anchor, unless you wrote the anchor.
- User-guide and reference pages stay on the site's own pages and the public documentation of the libraries. Only
  developer pages point at the repository's skills and plans.
- Python examples are run from the repository root with `uv run python` before they go in a page, inside
  `cimhub_core.cimtbl_testing.cim_scope()` when they load `.cimtbl`.
