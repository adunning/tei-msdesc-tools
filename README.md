# TEI manuscript description tools

Tools for working with a [TEI catalogue of manuscript descriptions](https://www.tei-c.org/release/doc/tei-p5-doc/en/html/MS.html) (using `<msDesc>`).

Designed for use with [Medieval Manuscripts in Oxford Libraries](https://medieval.bodleian.ox.ac.uk).

Requires Python 3.11 or later.

## Scripts

- `add_work_subjects.py`: Add work subjects to a TEI file.

- `create_viaf.py`: Encode VIAF data into TEI format.

- `date_bindings.py`: Add binding dates to a TEI manuscript descriptions.

- `manage_entities.py`: Validate entities in a TEI file and add missing records from VIAF.

## Usage

Usage information is available by running the scripts with the `--help` or `-h` flag. For example:

```bash
python3 create_viaf.py --help
```
