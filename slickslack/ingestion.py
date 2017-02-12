import os
import re
import json
import fnmatch
from datetime import datetime
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


def _slack_ts_str_to_epoch_sec(ts_str):
    assert type(ts_str == 'str')
    return int(ts_str.split('.')[0])


def _enrich_channel(chan):
    for m in chan['messages']:
        # add datetime to each message; retain 'ts' as it guarantees
        # uniqueness per https://github.com/slackhq/slack-api-docs/issues/7
        m[u'dt'] = datetime.utcfromtimestamp(
                        _slack_ts_str_to_epoch_sec(m['ts']))

        # add channel id
        m[u'ch_id'] = chan['channel_info']['id']


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

    chan_source = list_channels(export_root)

    chans = []
    chan_name_dict = {}
    for chan_name, chan_path in chan_source.iteritems():
        if not _name_satisfies_incl_excl(includes, excludes, chan_name):
            continue

        chan = _load_json(chan_path)
        if not include_mpim and chan['channel_info'].get('is_mpim'):
            continue

        _enrich_channel(chan)
        chans.append(chan)
        chan_name_dict[chan['channel_info']['id']] = chan['channel_info']['name']

    return chans, chan_name_dict


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


def iter_interactions(msgs):
    """
    :param msgs:
    :return:
    """

    # TODO: track last n messages we see, infer interaction
    #   from a 'chatty' conversation - e.g. recents = deque([], 3) etc

    for m in sorted(msgs, key=lambda x: x['ts']):
        def make_event(src, tgt, typ):
            return {u'src': src,
                    u'tgt': tgt,
                    u'ts': m['ts'],
                    u'dt': m['dt'],
                    u'ch_id': m['ch_id'],
                    u'type': typ}

        # count ats ("@')
        for at in extract_ats(m['text']):
            yield make_event(m['user'], at, 'at')

        # count reactions
        for r in m.get('reactions') or []:
            # r['name'] is the reaction, e.g. +1
            # note reactions don't carry a timestamp, so we use the one from the message
            for user in r['users']:
                yield make_event(user, m['user'], 'reaction')

        # explicit replies
        for r in m.get('replies') or []:
            yield make_event(r['user'], m['user'], 'reply')
