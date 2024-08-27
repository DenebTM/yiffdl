# yiffdl

## Dependencies

- Python 3.10
- yippi
- faapi

You may use `pipenv` to install the appropriate Python version and dependencies
(`pipenv install`).

## Configuration

**General**: Optionally change the client name/version (sent via user agent) and
download base path in `config.json`.

**e621/e926**: Set your username in `config.json` as per e621 API etiquette.
Optionally set a list of blacklisted tags, in case you wish to sanitise a list
of URLs or an existing local collection. The `e6.api_key` field is currently
unused.

**FurAffinity**: Find your `a` and `b` session cookies for FurAffinity.net in
the "Storage" section of your browser's Developer Tools (F12 or Ctrl+Shift+I)
and copy them into their respective fields in `config.json`. This step is only
necessary for NSFW submissions, as well as those by users who restrict access to
their page to registered users.

## Usage

Run the script inside `pipenv shell`, or use `pipenv run python yiffdl.py
<URL_LIST_FILES>`

For `<URL_LIST_FILES>`, pass paths to text files containing e621/e926 and/or
FurAffinity URLs.

Downloaded posts will be organised by title-cased artist name(s) for e621/e926,
and title-cased uploader name (assumed to reflect artist name) for FurAffinity.
