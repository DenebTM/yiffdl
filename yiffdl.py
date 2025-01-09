import os
import hashlib
import sys
from types import SimpleNamespace

import requests
import json
import faapi
from yippi import YippiClient


def main():
    config_filename = 'config.json'
    for i, arg in enumerate(sys.argv):
        if arg == '-c':
            config_filename = sys.argv[i+1]
            sys.argv.pop(i)
            sys.argv.pop(i)

    config = json.load(
        open(config_filename, 'r'),
        object_hook=lambda d: SimpleNamespace(**d),
    )
    config.headers = {
        'User-Agent': f'{config.client_name}/{config.client_version}'
    }

    url_lists = sys.argv[1:]
    if len(url_lists) == 0:
        print(f'Usage: {sys.argv[0]} URL_LIST_FILE [additional URL lists)')
        exit()

    # read all e6 and FA urls from files specified via command-line arguments
    e6_ids = []
    fa_ids = []
    for filename in url_lists:
        file_e6, file_fa = gather_post_ids(filename)
        e6_ids.extend(file_e6)
        fa_ids.extend(file_fa)

    # sort and remove duplicates, then display a summary
    e6_ids = sorted(list(set(e6_ids)))
    fa_ids = sorted(list(set(fa_ids)))

    dl_total = len(e6_ids) + len(fa_ids)
    dl_done = 0

    print(f'{len(e6_ids):>7} e6 posts')
    print(f'{len(fa_ids):>7} FA posts')
    print(f'{dl_total:>7} total\n')

    # set up e6 API
    # session = requests.Session()
    e6_client = YippiClient(
        config.client_name, config.client_version, config.e6.username
    )

    for post_id in e6_ids:
        dl_done += 1
        print(f'{dl_done:>{len(str(dl_total))}} / {dl_total}: ',
              end='', flush=True)
        result = e6_download(post_id, e6_client, config)
        print(result)

    # set up FA API with session cookies from browser
    cookies = [
        {'name': 'a', 'value': config.fa.cookie_a},
        {'name': 'b', 'value': config.fa.cookie_b},
    ]
    fa_client = faapi.FAAPI(cookies)

    for sub_id in fa_ids:
        dl_done += 1
        print(f'{dl_done:>{len(str(dl_total))}} / {dl_total}: ',
              end='', flush=True)
        result = fa_download(sub_id, fa_client, config)
        print(result)


def gather_post_ids(filename):
    e6_ids = []
    fa_ids = []
    with open(filename, 'r') as f:
        lines = f.read().splitlines()
        for line in lines:
            if (
                'e621.net/post/show' in line
                or 'e621.net/posts/' in line
                or 'e926.net/post/show' in line
                or 'e926.net/posts/' in line
            ):
                # truncate first the left, then the right part of the URL
                try:
                    postID = int(line.rsplit('/', 1)[1].split('?')[0])

                # old URL format with '/[truncated tags]' at the end
                except Exception as _:
                    postID = int(line.rsplit('/', 2)[1].split('/')[0])

                e6_ids.append(postID)

            elif (
                  'furaffinity.net/view/' in line
                  or 'furaffinity.net/full/' in line
            ):
                # truncate first the left, then the right part of the URL,
                # slightly differently depending on whether it ends in a slash
                # or not
                if line.endswith('/'):
                    postID = int(line.rsplit('/', 2)[1].split('/')[0])
                else:
                    postID = int(line.rsplit('/', 1)[1])

                fa_ids.append(postID)

    return e6_ids, fa_ids


def e6_download(post_id, client, config):
    post = client.post(post_id)

    url = post.file['url']
    # media has been deleted; ignore
    if url is None:
        return 'not found'

    id = str(post.id)
    ext = post.file['ext']
    post_md5 = post.file['md5']
    artists = filter(
        lambda a: a not in ['conditional_dnp', 'avoid_posting'],
        post.tags['artist']
    )

    # canonicalise author(s)
    filename = canonicalise(f'{id}.{ext}', config)
    subdir = canonicalise(
        ', '.join(
            [
                artist.replace('_', ' ')
                .replace(' (artist)', '')
                .replace(' (fa)', '')
                .title()
                for artist in artists
            ]
        ),
        config,
    )

    # set download location
    dl_path = f'{config.dl_base}/{subdir}'
    dl_file = f'{dl_path}/{filename}'
    print(f'{dl_file:<70}', end='', flush=True)

    # skip blacklisted posts; remove if already present
    for tag in config.e6.blacklist:
        for category in post.tags:
            if tag in post.tags[category]:
                if os.path.exists(dl_file):
                    os.remove(dl_file)
                    return 'removed (blacklist)'
                else:
                    return 'skipped (blacklist)'

    # check if file already exists
    if os.path.exists(dl_file):
        file_md5 = hashlib.md5()
        with open(dl_file, 'rb') as f:
            while chunk := f.read(8192):
                file_md5.update(chunk)

        file_md5 = file_md5.hexdigest()
        if file_md5 == post_md5:
            return 'already exists'

    # finally, download the file
    if not os.path.exists(dl_path):
        os.makedirs(dl_path)
    with open(dl_file, 'wb') as f:
        f.write(requests.get(url, headers=config.headers).content)

    return 'done'


def canonicalise(string, config):
    for char in config.invalid_chars:
        string = string.replace(char, '_')

    return string


def fa_download(sub_id, client, config):
    try:
        sub, _ = client.submission(sub_id, get_file=False)
    except Exception as e:
        return f'Error getting submission {sub_id}: {repr(e)}'

    id = str(sub.id)
    author = sub.author
    url = sub.file_url
    ext = url.rsplit('.', 1)[1]

    # canonicalise author and filename
    filename = canonicalise(f'{id} - {sub.title}.{ext}', config)
    subdir = canonicalise(author.name.lower().title(), config)

    # set download location
    dl_path = f'{config.dl_base}/{subdir}'
    dl_file = f'{dl_path}/{filename}'
    print(f'{dl_file:<70}', end='', flush=True)

    # finally, download the file
    if os.path.exists(dl_file):
        return 'already exists'

    if not os.path.exists(dl_path):
        os.makedirs(dl_path)
    with open(dl_file, 'wb') as f:
        f.write(requests.get(url, headers=config.headers).content)

    return 'done'


if __name__ == '__main__':
    main()
