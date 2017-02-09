import os
import re
import json
import fnmatch
#from collections import deque


def list_channels(export_root='.', includes=r'(private_)?channels\S+.json$'):
    res = {}
    for root, dirs, files in os.walk(export_root):
        for fi in files:
            file_path = os.path.join(root, fi)
            if not re.search(includes, file_path):
                continue
            chan_name = fi.split('.json')[0]
            res[chan_name] = file_path
    return res


def load_channels(export_root='.', includes=None, excludes=None, include_mpim=False):
    """Schema - see also https://api.slack.com/types
    {
        channel_info:
            { name, previous_names, id, purpose, topic,
                members, is_general, is_channel, is_open, is_mpim, is_group,
                created, is_archived, creator, topic, purpose, ... },
         messages:
         [
             { attachments, bot_id, channel, comment, display_as_bot,
                edited, file, inviter, is_intro, item, item_type,
                name, no_notifications, old_name, parent_user_id,
                pinned_to, purpose, reactions, replies, reply_count,
                room, subscribed, subtype, text, thread_ts, ts, type,
                upload, user, username, ...
            }, ...
         ]
     }
    """
    if isinstance(includes, str): includes = [includes]
    if isinstance(excludes, str): excludes = [excludes]
    if includes: includes = map(fnmatch.translate, includes)
    if excludes: excludes = map(fnmatch.translate, excludes)

    chans = list_channels(export_root)

    res =[]
    for chan_name, chan_path in chans.iteritems():
        if not _name_satisfies_incl_excl(includes, excludes, chan_name):
            continue

        chan = _load_json(chan_path)
        if not include_mpim and chan['channel_info'].get('is_mpim'):
            continue

        res.append(chan)
    return res


def load_user_dict(export_root='.', file_name='metadata.json'):
    file_path = os.path.join(export_root, file_name)
    return _load_json(file_path)['users']


def _name_satisfies_incl_excl(includes, excludes, s):
    def is_in_s(x):
        return re.match(x, s)
    if includes and not any(map(is_in_s, includes)):
        return False
    if excludes and any(map(is_in_s, excludes)):
        return False
    return True


def _load_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def extract_ats(text):
    at_re = re.compile(r'<@(\w+)>')
    return [m.group(1) for m in at_re.finditer(text)]


def iter_connections(msgs):
    """
    :param msgs:
    :return:
    """

    # TODO: track last n messages we see, infer interaction
    #   from a 'chatty' conversation - e.g. recents = deque([], 3) etc

    for m in sorted(msgs, key=lambda x: x['ts']):
        ts = m['ts']

        # count ats
        for at in extract_ats(m['text']):
            yield {'s': m['user'], 't': at, 'ts': ts}

        for r in m.get('reactions') or []:
            # r['name'] is the reaction, e.g. +1
            for user in r['users']:
                yield {'s': user, 't': m['user'], 'ts': ts}

        for r in m.get('replies') or []:
            yield {'s': r['user'], 't': m['user'], 'ts': ts}
