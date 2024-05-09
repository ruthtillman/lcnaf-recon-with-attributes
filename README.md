## LCNAF Recon With Attributes

This repository contains scripts to support the following processes:

1. Transform a full JSON-LD download of the LCNAF into a dataset consisting only of person name authorities into a much simpler syntax which can be used for comparison.
2. Search the LCNAF dataset for comparisons with a local set of records. This script is highly-specific to data coming from our local repository, but fields are named in a way that we hope will help others design/revise their own data. It is designed for faculty but tests may be altered or removed entirel.

Running the comparison will generate a JSON file outputting all possible matches for name matches with a threshold at 90 or higher and at least one matching characteristic. This file can be used in its entirety or processed into batches based on how many additional match characteristics are found, e.g. records with only affiliation match or records with affiliation AND education, etc.

## Transforming the LCNAF Download to JSON

Download the names.madsrdf.jsonld.gz file from https://id.loc.gov/download/authorities/names.madsrdf.jsonld.gz and unzip it in your working directory.

### Pre-processing

Use the split query to split the file based on line count. Because we had access to a Linux machine with significant processing power, we could split them in batches of 250,000 as below. This created 47 files at the time (2023).

```bash
split -l 250000 names.madsrdf.jsonld names_
```

Then rename or use the `mv` command to move them all from no filetype to .txt, e.g.

```bash
mv names_aa names_aa.txt
```

### Transformation Script

Once you have created text files files, run `transform_lc_to_working_json.py` to output batches of much smaller records

This script will retain only Personal Name records. If the data exists, resulting records will contain:

- id: partial, identifying URL for authority (all records)
- authorized_name: the authorized form of the person's name (all records)
- alt_names: a list of variant names (MARC 400)
- activity: a list of the person's activities (MARC 372)
- occupations: a list of the person's occupations (MARC 374)
- organizations: a list of the organizations from a person's affiliation field (MARC 373)
- citation_data: a list of fields from the citation (670). These may contain weird nesting (see `sample_lc.json`) if there us a |u in the field.


## Searching for Matches in the LCNAF

The script `search_all_lc_files.py` contains a series of functions which read a local record and compare it to records in the LCNAF files. Each is described briefly below. See our article for more information about the process. The output record will contain fields from both records and fields confirming or providing context for the matches found. Our article contains additional information about each tests and the choices we made. It may be useful to consult as well.

If the data exists, the resulting record will contain:

- id: from the local data
- local_name: name in common order from local data
- lc_name: the authorized form of the name from the LC record
- best_match: the score of the highest match value found during matching tests. Note, once these tests reach their minimum threshold, a higher match may not be recorded.
- url: full URL of the LC Name Authority
- affiliation: list containing information about where any affiliation matches were found.
- lc_organizations: a list of the organizations found in the LC record. These are present whether or not there is an organization or education match found, since they may be useful during review.
- occupation match: True if one is found.
- lc_occupations: from the LC record. These are present whether or not there is an occupation match found, since they may be useful during review.
- activity_match: list containing information about where any activity matches were found.
- lc_activity: field of activity data from the LC record.
- local_organization: the local department name.
- local_education: the local education data. List of educational institutions or null.
- education_match: list containing information about where any education matches were found.
- lc_citation_data: a list of the citation data fields copied from the LC record. These are present whether or not a match is found using them, since they may be useful during review.

Note: For occupation match, there is only a True/False answer. For other fields, the match results are an array which contains references to the field(s) where a match was found. This supports further scripted data analysis, e.g. creating a project to update 374 fields by identifying which matching records do not have affiliation matches in the organization field.

### Names

Based on the data we were working from file expects:

- an inverted name field without middle names or initials,
- a common-order name field containing any known names or initials, and
- an "access id" which consists of 2-3 letters and 1-4 numbers.

This function is the most complicated and we anticipate that others will need to reinvent the tests but can use ours as a model. Ultimately, names are so complex and varied that it is impossible to create fully standardized and accurate names for them. Ours works well for our data but has significant room for improvement.

### Affiliation

Affiliation check checks for substrings in LC organization and citation fields. We recommend creating different sets of substrings (short enough to identify your institution but not enough to limit possible variants) to identify different ways it may be represented.

Questions to ask:

- Are there Corporate Name Authorities for colleges or schools or departments or centers within your institution? 
- How has your institution been represented in citation data over time, particularly when brevity was prioritized?

### Occupation

This is hardcoded to search for anyone with any kind of "teacher" occupation (see our article), "University and college faculty members," and librarians. Your data may represent people in different occupations.

Note: Occupation matches are output to result files but records that match only on name >= 90 and occupation will not be output into your result set without adding `or data.get("occupation_match") is not None` to the set of tests near the end the file.

### Educational History

This expects a list of educational institutions. It will attempt to process human-entered variation for university names and output a cleaned up version which wil lbe tested with organizational affiliations. It will also create a set of abbreviations for any university names and test these with citation.

Note: While its marketing department promotes "The," Ohio State University's established heading does not contain the article and you should not worry about missing a match.

### Department and Activity

This test expects a single department name as a string. It then tests whether a potential matching LC record has any field of activity list and whether each field of activity (or segment, split on "--" if needed) is present in the department name. E.g. "Astronomy" in "Astronomy and Astrophysics."

It then tests whether the department name is present in the citation.
 
All fields are transformed into lowercase in order to avoid missing matches with inconsistent capitalizations.

Note: If your data contains "Department of" or "School of," it will be beneficial to batch replace these in order to improve the likelihood of match. For example, someone in the "Department of Sociology" may have the word "Sociology" in their LC citation referring to their PhD work.

## Sample Data

The sample directory contains two samples which can be used so that a person experimenting with this code does not have to generate their own test data. There is also a sample result .

The file `sample_local.json` comes from Penn State's Researcher Metadata Database. It contains two names, one with a full record and one where the educational history field is null.

The file `sample_lc.json` contains a sample of transformed LC name authorities produced by `transform_lc_to_working_json`. It includes matches for the two names in sample_local along with one name match that scores higher than 90 but does not match on any attributes and should not be included in the result. It also includes a few miscellaneous records.

The file `sample_result.json` contains two sample records produced by the `search_all_lc_files.py` function. These demonstrate ouput files. In both cases, the match are correct. In one case, educational history is missing because it was missing from the original data in sample_local.json.

## Future Work

Ed Summers's work on [idloc](https://inkdroid.org/2024/02/14/publishing-jsonld/) seems promising for handling data. If it's adopted by id.loc.gov, at minimum it would be productive to cut down on the export to only personal name authorities (if that's desired).

Because the idloc library is meant to support downloads vs. the entire dump, at this point it would require adapting the library to run as a transformation.