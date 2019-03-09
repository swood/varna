#!/usr/bin/env python

import sys
import os
import json
from unidecode import unidecode
from string import lower
import string
import re
import argparse
import time
import calendar
import datetime
import dateutil.parser
import os.path
import random
from PIL import Image


parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("--type", action="store", dest="type", help="public_room_users; channels; history_rooms; users; direct_posts")
parser.add_argument("--team", action="store", dest="def_team", help="default team for all users")
parser.add_argument("--attachments", action="store", dest="attachments", help="to make an import with attachments or not, by default 1 (enabled)")
parser.add_argument("--increment", dest = "increment", action="store_true", help = "increment history import")
parser.add_argument("--new-import", action = "store", dest="new_folder", help = "path to new import, relative path from root of this script.")
args = parser.parse_args()

if args.type:
    type = args.type
else:
    print 'nothing to do without files type'
    sys.exit(1)
if args.def_team:
    def_team = args.def_team
else:
    print "you should specify a team"
    os.exit(1)
if args.attachments:
    attachments = int(args.attachments)
else:
    attachments = 1
if args.new_folder:
    new_import_folder = args.new_folder
else:
    new_import_folder = ""
if args.increment:
    increment = args.increment
else:
    increment = False


version = 1
source_rooms = 'rooms.json'
source_users = 'users.json'
source_user_name = 'real_users.json'
crowd_users = 'users_special.json'
default_team = def_team
default_container_path = "/mattermost/data/hipchat_export"
deleted_rooms = []
depth_days = 120
read_job_title = 1
read_deleted_rooms = 1
image_heigh_limit = 5000
image_width_limit = 5000

def update_password(password, char):
    replace_index = random.randrange(len(password))
    if (replace_index == 0):
        replace_index = 1
    return password[0:replace_index] + str(char) + password[replace_index+1:]

def pwgen():
    PASSWORD_LENGTH = 18
    password_chars = "abcdefghjkmnpqrstuvwxyzQWERTYUIOPLKJHGFDSAZXCVBNM1234567890"
    my_password = ""
    for i in range(PASSWORD_LENGTH):
        next_index = random.randrange(len(password_chars))
        if (random.randrange(10) > 5):
            my_password = my_password + password_chars[next_index].upper()
        else:
            my_password = my_password + password_chars[next_index]
    my_password = update_password(my_password, random.randrange(0, 9))
    return my_password

def isEnglish(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True

def write_data_to_file(text):
    writelines(json.dumps(text))
    writelines(",")

def email_to_id():
    email2id = {}
    if increment:
        all_users_ = all_new_users
    else:
        all_users_ = all_users

    for user_by_hipchat in all_users_:
        email = user_by_hipchat['User']['email']
        id_hipchat = user_by_hipchat['User']['id']
        email2id[email] = int(id_hipchat)
    return email2id

def id_to_nickname():
    id2nickname = {}
    if increment:
        all_users_ = all_new_users
    else:
        all_users_ = all_users

    for user_by_hipchat in all_users_:
        id_by_hipchat = int(user_by_hipchat['User']['id'])
        nickname = get_real_username(user_by_hipchat['User']['email'])
        id2nickname[id_by_hipchat] = nickname
    return id2nickname


def get_hipchat_id(email):
    id_hipchat = 0
    if increment:
        all_users_ = all_new_users
    else:
        all_users_ = all_users

    for user_by_hipchat in all_users_:
        email_by_hipchat = user_by_hipchat['User']['email']
        if email == email_by_hipchat:
            id_hipchat = user_by_hipchat['User']['id']
    return int(id_hipchat)

def get_hipchat_nickname(id):
    nickname = "null"
    if increment:
        all_users_ = all_new_users
    else:
        all_users_ = all_users

    for user_by_hipchat in all_users_:
        id_by_hipchat = user_by_hipchat['User']['id']
        if id == id_by_hipchat:
            email = user_by_hipchat['User']['email']
            nickname = get_real_username(email)
    return str(nickname)

def get_real_username(email):
    user_id = "null"

    for real_name in all_real_names['users']:
        real_email = real_name['email']
        if real_email == email:
            user_id = real_name['user']
    return str(user_id)

def room_id_to_name_dict():
    rooms = {}
    if increment:
        all_rooms_ = all_rooms_new_import
    else:
        all_rooms_ = all_rooms

    for room in all_rooms_:
        id = int(room['Room']['id'])
        if not isEnglish(room['Room']['name']):
            name = prepare_name(unidecode(u'%s' % room['Room']['name']))
        else:
            name = prepare_name(room['Room']['name'])
        rooms[id] = name
    return rooms

def get_room_name_by_id(id, all_rooms_dict):
    return all_rooms_dict[id]

def prepare_name(name):
    name = lower(name.replace("'", "").replace(" ", "").strip())
    name_id = re.sub('^\#\#\#\#\#$', '5_sharps', name)
    name_id = re.sub('^\~$', '5_tilda', name_id)
    name_id = re.sub('^\-$', '1_dash', name_id)
    name_id = re.sub('^\-\-$', '2_dashes', name_id)
    name_id = re.sub('^\-\-\-$', '3_dashes', name_id)
    name_id = re.sub('(.*)\.\.\.$', r'\g<1>_dotdotdot', name_id)
    name_id = re.sub('[^A-Za-z0-9]+', '_', name_id)
    name_id = re.sub('_$', '', name_id)
    name_id = re.sub('^_', '', name_id)
    name_id = re.sub('^1$', 'one_1', name_id)
    name_id = re.sub("'", '', name_id)
    return str(name_id.decode('UTF-8'))

def get_rooms_by_hipchat_id(hipchat_id, public_rooms, all_rooms_dict):
    rooms_by_user = dict()
    room_admin = list()
    room_member = list()
    if hipchat_id in public_rooms.keys():
        public_room = public_rooms[hipchat_id]
    else:
        public_room = []

    if increment:
        all_rooms_ = all_rooms_new_import
    else:
        all_rooms_ = all_rooms

    for room in all_rooms_:
        if len(room['Room']['room_admins']) > 0:
            if hipchat_id == room['Room']['room_admins'][0]:
                if not isEnglish(room['Room']['name']):
                    room_name = prepare_name(unidecode(u'%s' % room['Room']['name']))
                else:
                    room_name = prepare_name(room['Room']['name'])
                room_admin.append(room_name)
        if len(room['Room']['members']):
            try:
                room['Room']['members'].index(hipchat_id)
                if not isEnglish(room['Room']['name']):
                    room_name = prepare_name(unidecode(u'%s' % room['Room']['name']))
                else:
                    room_name = prepare_name(room['Room']['name'])
                room_member.append(room_name)
            except:
                pass
    if len(public_room) != 0:
        for p in public_room:
            room_member.append(get_room_name_by_id(p,all_rooms_dict))
    rooms_by_user['admin'] = room_admin
    rooms_by_user['member'] = room_member
    return rooms_by_user

def is_user_admin(user_is_admin, room_id):
    room_id = room_id.decode('UTF-8')
    try:
        user_is_admin.index(room_id)
        return True
    except:
        return False

def make_channels(who_is_user):
    """
    :param who_is_user: dict
    :return: dict
    """
    user_is_admin = []
    user_is_member = []
    notify_props = {}
    notify_props['desktop'] = 'mention'
    notify_props['mobile'] = 'mention'
    notify_props['mark_unread'] = 'mention'
    member_status = []
    for admin in who_is_user['admin']:
        user_is_admin.append(admin)
    for member in who_is_user['member']:
        user_is_member.append(member)
    member_in_two_roles = list(set(user_is_member) & set(user_is_admin))
    for room in user_is_member:
        status = dict()
        status['name'] = room
        if is_user_admin(user_is_admin, room):
            status['roles'] = 'channel_user channel_admin'
        else:
            status['roles'] = 'channel_user'
        status['notify_props'] = notify_props
        member_status.append(status)
    if len(member_in_two_roles) == 0:
        for room in user_is_admin:
            status = dict()
            status['name'] = room
            status['roles'] = 'channel_user channel_admin'
            status['notify_props'] = notify_props
            member_status.append(status)
    return member_status

def write_password_user(email, password):
    pwfile.writelines("%s\t%s" % (email, password))
    pwfile.writelines("\n")

def make_json(username, email, first_name, last_name, user_is):
    """
    :param username: str
    :param email: str
    :param first_name: str
    :param last_name: str
    :param user_is: str
    :return: dict
    """
    user = {}
    user_fields = {}
    user_teams = {}
    nickname = lower(username)
    where_is_user = make_channels(user_is)
    user_fields['username'] = lower(username)
    user_fields['email'] = email
    password = pwgen()
    user_fields['password'] = password
    write_password_user(email, password)
    user_fields['nickname'] = nickname
    user_fields['first_name'] = first_name
    user_fields['last_name'] = last_name
    user_fields['position'] = get_position(email)
    user_fields['roles'] = 'system_user'
    user_fields['locale'] = 'en'
    user_fields['tutorial_step'] = '999'
    user_fields['show_unread_section'] = 'false'
    user_fields['use_military_time'] = "true"
    user_teams['channels'] = where_is_user
    user_teams['name'] = default_team
    user_teams['roles'] = 'team_user'
    user_fields['teams'] = [user_teams]
    user['type'] = 'user'
    user['user'] = user_fields
    return user

def make_group_mattermost_json(room_name, room_type, room_header, display_name):
    room = {}
    room_channel = {}
    room_channel['team'] = default_team
    room_channel['name'] = room_name
    room_channel['display_name'] = u"%s" % display_name
    room_channel['type'] = room_type
    room_channel['header'] = u"%s" % room_header
    room['type'] = 'channel'
    room['channel'] = room_channel
    return json.dumps(room)

def timestamp_from_date(date):
    d = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ %f")
    return int(d.strftime("%s")) * 1000 + d.microsecond / 1000

def write_mattermost_json(json_object):
    result_mattermost_rooms.writelines(json_object)
    result_mattermost_rooms.writelines("\n")

def write_users_json(json_object):
    result_users_file.writelines(json_object)
    result_users_file.writelines("\n")

def write_room_history_json(file, json_object):
    file.writelines(json_object)
    file.writelines("\n")

def write_direct_post(json_object):
    result_direct_post_file.writelines(json_object)
    result_direct_post_file.writelines("\n")

def write_public_room_members(json_object):
    result_public_rooms.writelines(json_object)

def generate_post_json(type, room_name, room_id, sender, timestamp, result_room_file, message="", attachment_name="", attachment_path_ondisk=""):
    if type == 0:
        global_post = {}
        post = {}
        post['team'] = default_team
        post['channel'] = room_name
        post['user'] = sender
        post['message'] = message
        post['create_at'] = timestamp
        global_post['type'] = 'post'
        global_post['post'] = post
    else:
        global_post = {}
        post = {}
        post['team'] = default_team
        post['channel'] = room_name
        post['user'] = sender
        post['message'] = attachment_name
        post['create_at'] = timestamp
        attachments = {}
        if not increment:
            attachment_path_mattermost = "%s/rooms/%d/files/%s" % (default_container_path, room_id, attachment_path_ondisk)
        else:
            attachment_path_mattermost = "%s/%s/rooms/%d/files/%s" % (default_container_path, new_import_folder, room_id, attachment_path_ondisk)
        attachments['path'] = attachment_path_mattermost
        post['attachments'] = [attachments]
        global_post['type'] = 'post'
        global_post['post'] = post

    write_room_history_json(result_room_file, json.dumps(global_post))

def parse_room_mattermost(room_json, room_id, room_name, is_increment, last_imported_message_id=0):
    result_room_file = open("exported_rooms/%s.jsonl" % room_name, 'w')
    write_room_history_json(result_room_file, "{ \"type\": \"version\", \"version\": %d }" % version)
    for post in room_json:
        #check attach
        if 'UserMessage' in post.keys():
            if is_increment == 0:
                if str(post['UserMessage']['attachment_path']).decode('UTF-8') != 'None':
                    if attachments == 1:
                        is_attach = 1
                        attachment_name = post['UserMessage']['attachment']['name']
                        attachment_path_ondisk = post['UserMessage']['attachment_path']
                        message = ""
                        if not increment:
                            if not os.path.exists("rooms/%d/files/%s" % (room_id, attachment_path_ondisk)):
                                print "skip post %s" %  attachment_path_ondisk
                                continue
                            else:
                                image_file = "rooms/%d/files/%s" % (room_id, attachment_path_ondisk)
                                try:
                                    im = Image.open(image_file)
                                    heigh, width = im.size
                                except:
                                    heigh = 0
                                    width = 0
                                if heigh > image_heigh_limit or width > image_width_limit:
                                    continue
                        else:
                            if not os.path.exists("%s/rooms/%d/files/%s" % (new_import_folder, room_id, attachment_path_ondisk)):
                                print "skip post %s/rooms/%d/files/%s" %  (new_import_folder, room_id, attachment_path_ondisk)
                                continue
                            else:
                                image_file = "%s/rooms/%d/files/%s" % (new_import_folder, room_id, attachment_path_ondisk)
                                try:
                                    im = Image.open(image_file)
                                    heigh, width = im.size
                                except:
                                    heigh = 0
                                    width = 0
                                if heigh > image_heigh_limit or width > image_width_limit:
                                    continue
                    else:
                        is_attach = 0
                        attachment_name = ""
                        attachment_path_ondisk = ""
                        message = ""
                else:
                    is_attach = 0
                    attachment_name = ""
                    attachment_path_ondisk = ""
                    message = post['UserMessage']['message']
                    is_code = message[0:5]
                    is_quote = message[0:6]
                    if is_code == "/code":
                        message = "```\n%s\n```" % message[6:]
                    if is_quote == "/quote":
                        message = "> %s\n" % message[7:]

                sender_id = post['UserMessage']['sender']['id']
                sender_nickname = get_hipchat_nickname(sender_id)
                timestamp = timestamp_from_date(post['UserMessage']['timestamp'])
                if len(message) < 16383:
                    generate_post_json(is_attach, room_name, room_id, sender_nickname, timestamp, result_room_file, message, attachment_name, attachment_path_ondisk)
            else:
                if last_imported_message_id != post['UserMessage']['id']:
                    if str(post['UserMessage']['attachment_path']).decode('UTF-8') != 'None':
                        if attachments == 1:
                            is_attach = 1
                            attachment_name = post['UserMessage']['attachment']['name']
                            attachment_path_ondisk = post['UserMessage']['attachment_path']
                            message = ""
                            if not os.path.exists("%s/rooms/%d/files/%s" % (new_import_folder, room_id, attachment_path_ondisk)):
                                print "skip post %s/rooms/%d/files/%s" % (new_import_folder, room_id, attachment_path_ondisk)
                                continue
                            else:
                                image_file = "%s/rooms/%d/files/%s" % (new_import_folder, room_id, attachment_path_ondisk)
                                try:
                                    im = Image.open(image_file)
                                    heigh, width = im.size
                                except:
                                    heigh = 0
                                    width = 0
                                if heigh > image_heigh_limit or width > image_width_limit:
                                    continue
                        else:
                            is_attach = 0
                            attachment_name = ""
                            attachment_path_ondisk = ""
                            message = ""
                    else:
                        is_attach = 0
                        attachment_name = ""
                        attachment_path_ondisk = ""
                        message = post['UserMessage']['message']
                        is_code = message[0:5]
                        is_quote = message[0:6]
                        if is_code == "/code":
                            message = "```\n%s\n```" % message[6:]
                        if is_quote == "/quote":
                            message = "> %s\n" % message[7:]

                    sender_id = post['UserMessage']['sender']['id']
                    sender_nickname = get_hipchat_nickname(sender_id)
                    timestamp = timestamp_from_date(post['UserMessage']['timestamp'])
                    if len(message) < 16383:
                        generate_post_json(is_attach, room_name, room_id, sender_nickname, timestamp, result_room_file, message, attachment_name, attachment_path_ondisk)
                else:
                    break

def make_pairs(pairs):
    for pair in set(pairs):
        channel = {}
        direct_channel = {}
        direct_channel['members'] = str(pair).split(',')
        channel['type'] = 'direct_channel'
        channel['direct_channel'] = direct_channel
        write_direct_post(json.dumps(channel))

def make_direct_post(type, sender, receiver, timestamp, message, attachment_path="", attachment_name=""):
    """
    :param type: str
    :param sender: str
    :param receiver: str
    :param timestamp: datetime
    :param message: str
    :param attachment_path: str
    :param attachment_name: str
    :return:
    """
    post = {}
    post['type'] = 'direct_post'
    if type == 0:
        direct_post = {}
        channel_members = []
        channel_members.append(sender)
        channel_members.append(receiver)
        direct_post['channel_members'] = channel_members
        direct_post['user'] = sender
        direct_post['message'] = message
        direct_post['create_at'] = timestamp
        post['direct_post'] = direct_post
        write_direct_post(json.dumps(post))
    elif type == 1:
        direct_post = {}
        channel_members = []
        channel_members.append(sender)
        channel_members.append(receiver)
        direct_post['channel_members'] = channel_members
        attachments = {}
        if not increment:
            attachment_path_mattermost = "%s/users/files/%s" % (default_container_path, attachment_path)
        else:
            attachment_path_mattermost = "%s/%s/users/files/%s" % (default_container_path, new_import_folder, attachment_path)
        attachments['path'] = attachment_path_mattermost
        direct_post['attachments'] = [attachments]
        direct_post['user'] = sender
        direct_post['message'] = message
        direct_post['create_at'] = timestamp
        post['direct_post'] = direct_post
        write_direct_post(json.dumps(post))

def get_position(email):
    """
    :param email:
    :return: str
    """
    title = "Developer"
    if read_job_title == 1:
        for u in all_titles:
            if u["email"] == email:
                title = str(unidecode(u'%s' % u['title'])).strip()
    return title


def parse_direct_posts(user_id, type_export, id_to_nickname_dict, is_new_user):
    """
    :param user_id:
    :param type_export:
    :param id_to_nickname_dict:
    :return: run another function
    """

    if not increment:
        with open('users/%d/history.json' % user_id, 'r') as file_history:
            all_user_history = json.load(file_history)
    else:
        if new_import_folder != "":
            if is_new_user == 0:
                if os.path.getsize('users/%d/history.json' % user_id) < 36:
                    last_imported_id = ""
                else:
                    with open('users/%d/history.json' % user_id, 'r') as prev_file_history:
                        prev_all_user_history = json.load(prev_file_history)
                    last_imported_id = prev_all_user_history[0]['PrivateUserMessage']['id']
            else:
                last_imported_id = ""
            with open('%s/users/%d/history.json' % (new_import_folder, user_id), 'r') as file_history:
                all_user_history = json.load(file_history)
        else:
            return False

    #build chat pairs
    if type_export == 0:
        print "export pairs"
        pairs = []
        if not increment:
            for post in all_user_history:
                sender = id_to_nickname_dict[int(post['PrivateUserMessage']['sender']['id'])]
                receiver = id_to_nickname_dict[int(post['PrivateUserMessage']['receiver']['id'])]
                pairs.append("%s,%s" % (receiver, sender))
        else:
            print last_imported_id
            for post in all_user_history:
                if post['PrivateUserMessage']['id'] == last_imported_id:
                    break
                else:
                    sender = id_to_nickname_dict[int(post['PrivateUserMessage']['sender']['id'])]
                    receiver = id_to_nickname_dict[int(post['PrivateUserMessage']['receiver']['id'])]
                    pairs.append("%s,%s" % (receiver, sender))
        make_pairs(pairs)
    elif type_export == 1:
        print "export messages"
        for post in all_user_history:
            if increment:
                if post['PrivateUserMessage']['id'] == last_imported_id:
                    break
            sender = id_to_nickname_dict[int(post['PrivateUserMessage']['sender']['id'])]
            receiver = id_to_nickname_dict[int(post['PrivateUserMessage']['receiver']['id'])]
            timestamp = timestamp_from_date(post['PrivateUserMessage']['timestamp'])
            attach = u"%s" % post['PrivateUserMessage']['attachment_path']
            if attach == 'None':
                is_attach = 0
                attachment_name = ""
                attachment_path = ""
                message = post['PrivateUserMessage']['message']
                if len(message) > 16383:
                    continue
                is_code = message[0:5]
                is_quote = message[0:6]
                if is_code == "/code":
                    message = "```\n%s\n```" % message[6:]
                if is_quote == "/quote":
                    message = "> %s\n" % message[7:]
            else:
                if attachments == 1:
                    is_attach = 1
                    attachment_path = post['PrivateUserMessage']['attachment_path']
                    attachment_name = attachment_path.split("/")[1]
                    message = ""
                    if not increment:
                        if not os.path.exists("users/files/%s" % attachment_path):
                            print "skip post %s" %  attachment_path
                            continue
                        else:
                            image_file = "users/files/%s" % attachment_path
                            try:
                                im = Image.open(image_file)
                                heigh, width = im.size
                            except:
                                heigh = 0
                                width = 0
                            if heigh > image_heigh_limit or width > image_width_limit:
                                continue
                    else:
                        if not os.path.exists("%s/users/files/%s" % (new_import_folder, attachment_path)):
                            print "skip post %s/users/files/%s" %  (new_import_folder, attachment_path)
                            continue
                        else:
                            image_file = "%s/users/files/%s" % (new_import_folder, attachment_path)
                            try:
                                im = Image.open(image_file)
                                heigh, width = im.size
                            except:
                                heigh = 0
                                width = 0
                            if heigh > image_heigh_limit or width > image_width_limit:
                                continue
                else:
                    continue

            make_direct_post(is_attach, sender, receiver, timestamp, message, attachment_path, attachment_name)

def is_room_deleted(id):
    if read_deleted_rooms == 1:
        try:
            deleted_rooms.index(id)
            return 1
        except:
            return 0
    else:
        return 0

def read_all_rooms_to_dict():
    read_limit = depth_days * 60*60*24
    #end_date = timestamp_from_date("2018-11-13T06:05:02Z 778494") - read_limit
    end_date = 1539932091881
    rooms = {}
    if increment:
        all_rooms_ = all_rooms_new_import
    else:
        all_rooms_ = all_rooms

    for room in all_rooms_:
        room_id = int(room['Room']['id'])
        if increment:
            room_history_file = "%s/rooms/%d/history.json" % (new_import_folder, room_id)
        else:
            room_history_file = "rooms/%d/history.json" % room_id
        members = []
        member = []
        if is_room_deleted(room_id) == 0:
            with open("%s" % room_history_file, 'r') as room_history:
                history_room = json.load(room_history)
            room_size = len(history_room)
            print "room_id => %d and size => %d" % (room_id, room_size)

            for h in history_room:
                if 'UserMessage' in h.keys():
                    timestamp = timestamp_from_date(h['UserMessage']['timestamp'])
                    if room_size < 1000:
                        if timestamp >= end_date:
                            sender = int(h['UserMessage']['sender']['id'])
                            member.append(sender)
                    else:
                        sender = int(h['UserMessage']['sender']['id'])
                        member.append(sender)
            if len(member) != 0:
                for m in set(member):
                    members.append(m)
                rooms['%d' % room_id] = members
    return rooms


def get_rooms_by_userid(user_id, all_rooms_dict):
    print "collecting rooms for user %d" % user_id
    user_object = {}
    user_member_is = []
    for room in all_rooms_dict:
        if is_room_deleted(room) == 0:
            try:
                all_rooms_dict[room].index(user_id)
                user_member_is.append(int(room))
            except:
                continue
    if len(user_member_is) != 0:
        user_object['user'] = user_id
        user_object['member'] = user_member_is
        return user_object
    else:
        return 0

def diff(first, second):
        second = set(second)
        return [item for item in first if item not in second]

# let's read all users
if not increment:
    with open(source_users, 'r') as users:
        all_users = json.load(users)
else:
    if new_import_folder != "":
        with open(source_users, 'r') as old_import_users:
            all_old_users = json.load(old_import_users)
        with open("%s/%s" % (new_import_folder, source_users), 'r') as new_import_users:
            all_new_users = json.load(new_import_users)


if not increment:
    with open(crowd_users, 'r') as crowd_users:
        users_from_crowd = json.load(crowd_users)
else:
    with open("%s/%s" % (new_import_folder, crowd_users), 'r') as new_crowd_users:
        users_from_crowd_new_import = json.load(new_crowd_users)
    with open(crowd_users, 'r') as old_crowd_users:
        users_from_crowd_old_import = json.load(old_crowd_users)


if not increment:
    with open(source_rooms, 'r') as rooms:
        all_rooms = json.load(rooms)
else:
    if new_import_folder != "":
        with open(source_rooms, 'r') as old_import_rooms:
            all_rooms_old_import = json.load(old_import_rooms)
        with open("%s/%s" % (new_import_folder, source_rooms), 'r') as new_import_rooms:
            all_rooms_new_import = json.load(new_import_rooms)

with open(source_user_name, 'r') as real_name_users:
    all_real_names = json.load(real_name_users)

if read_deleted_rooms == 1:
    with open("deleted_room.txt", 'r') as deleted_room_file:
        content = deleted_room_file.readlines()
        for line in content:
            deleted_rooms.append(int(line.strip()))

if read_job_title == 1:
    with open("job_title.json", 'r') as file_job_titles:
        all_titles = json.load(file_job_titles)


if type == "users":
    print "generate users file for mattermost"
    result_users_file = open('exported_special_files/users.jsonl', 'w')
    pwfile = open('exported_special_files/passwords.txt', 'w')
    write_users_json("{ \"type\": \"version\", \"version\": %d }" % version)

    with open('exported_special_files/public_room_members.json', 'r') as public_rooms_file:
        public_rooms = json.load(public_rooms_file)

    all_rooms_dict = room_id_to_name_dict()
    public_rooms_dict = {}
    for public_room in public_rooms:
        user = public_room['user']
        member = public_room['member']
        public_rooms_dict[user] = member

    if not increment:
        for user in users_from_crowd:
            email = user['user']['email']
            id = get_hipchat_id(email)
            first_name = user['user']['first_name']
            last_name = user['user']['last_name']
            real_user_name = get_real_username(email)
            if real_user_name == "null":
                real_user_name = user['user']['username']

            room_by_user = get_rooms_by_hipchat_id(id, public_rooms_dict, all_rooms_dict)
            json_data = make_json(real_user_name, email, first_name, last_name, room_by_user)
            write_users_json(json.dumps(json_data))
    else:
        old_user_emails = list()
        new_user_emails = list()
        for old_user in users_from_crowd_old_import:
            old_user_emails.append(str(old_user['user']['email']))
        for new_user in users_from_crowd_new_import:
            new_user_emails.append(str(new_user['user']['email']))

        diff_list = diff(new_user_emails, old_user_emails)
        for user in users_from_crowd_new_import:
            try:
                diff_list.index(user['user']['email'])
                email = user['user']['email']
                id = get_hipchat_id(email)
                first_name = user['user']['first_name']
                last_name = user['user']['last_name']
                real_user_name = get_real_username(email)
                if real_user_name == "null":
                    real_user_name = user['user']['username']

                room_by_user = get_rooms_by_hipchat_id(id, public_rooms_dict, all_rooms_dict)
                json_data = make_json(real_user_name, email, first_name, last_name, room_by_user)
                write_users_json(json.dumps(json_data))
            except:
                continue


elif type == "channels":
    print "generate rooms file for mattermost"
    result_mattermost_rooms = open('exported_special_files/mattermost_rooms.jsonl', 'w')
    write_mattermost_json("{ \"type\": \"version\", \"version\": %d }" % version)
    if not increment:
        for room in all_rooms:
            if not isEnglish(room['Room']['name']):
                room_name = prepare_name(unidecode(u'%s' % room['Room']['name']))
            else:
                room_name = prepare_name(room['Room']['name'])
            header = room['Room']['topic']
            display_name = room['Room']['name']
            privacy = room['Room']['privacy']
            if privacy == "private":
                room_type = "P"
            elif privacy == "public":
                room_type = "O"
            write_mattermost_json(make_group_mattermost_json(room_name, room_type, header, display_name))
    else:
        if new_import_folder != "":
            print "read new HipChat export and find a new rooms..."
            old_rooms_ids = list()
            new_rooms_ids = list()
            for old_room in all_rooms_old_import:
                old_rooms_ids.append(int(old_room['Room']['id']))
            for new_room in all_rooms_new_import:
                new_rooms_ids.append(int(new_room['Room']['id']))
            diff_list = diff(new_rooms_ids, old_rooms_ids)

            for room in all_rooms_new_import:
                try:
                    diff_list.index(room['Room']['id'])
                    print room['Room']['id']
                    if not isEnglish(room['Room']['name']):
                        room_name = prepare_name(unidecode(u'%s' % room['Room']['name']))
                    else:
                        room_name = prepare_name(room['Room']['name'])
                    header = room['Room']['topic']
                    display_name = room['Room']['name']
                    privacy = room['Room']['privacy']
                    if privacy == "private":
                        room_type = "P"
                    elif privacy == "public":
                        room_type = "O"
                    write_mattermost_json(make_group_mattermost_json(room_name, room_type, header, display_name))
                except:
                    continue

elif type == "history_rooms":
    print "export hipchat room history to mattermost json"
    if not increment:
        for room in all_rooms:
            if not isEnglish(room['Room']['name']):
                room_name = prepare_name(unidecode(u'%s' % room['Room']['name']))
            else:
                room_name = prepare_name(room['Room']['name'])
            id = int(room['Room']['id'])
            if read_deleted_rooms == 1:
                if is_room_deleted(id) == 0:
                    with open("rooms/%d/history.json" % id, 'r') as room_json:
                        room_history = json.load(room_json)
                    parse_room_mattermost(room_history, id, room_name, 0,0)
            else:
                with open("rooms/%d/history.json" % id, 'r') as room_json:
                    room_history = json.load(room_json)
                parse_room_mattermost(room_history, id, room_name,0,0)
    else:
        old_rooms_ids = list()
        new_rooms_ids = list()
        for old_room in all_rooms_old_import:
            old_rooms_ids.append(int(old_room['Room']['id']))
        for new_room in all_rooms_new_import:
            new_rooms_ids.append(int(new_room['Room']['id']))
        diff_list = diff(new_rooms_ids, old_rooms_ids)

        for room in all_rooms_new_import:
            if not isEnglish(room['Room']['name']):
                room_name = prepare_name(unidecode(u'%s' % room['Room']['name']))
            else:
                room_name = prepare_name(room['Room']['name'])
            id = int(room['Room']['id'])
            if id == 2130:
                continue
            try:
                if_new_group = diff_list.index(id)
            except:
                if_new_group = 0

            if if_new_group != 0:
                print "this is new room %d" % id
                if is_room_deleted(id) == 0:
                    with open("%s/rooms/%d/history.json" % (new_import_folder, id), 'r') as room_json:
                        room_history = json.load(room_json)
                    parse_room_mattermost(room_history, id, room_name, 0, 0)
            else:
                if is_room_deleted(id) == 0:
                    if os.path.isfile("rooms/%d/history.json" % id):
                        with open("rooms/%d/history.json" % id, 'r') as old_room_json:
                            room_history_old_history = json.load(old_room_json)
                    else:
                        room_history_old_history = ""
                    try:
                        last_imported_message_id = room_history_old_history[0]['UserMessage']['id']
                    except:
                        try:
                            last_imported_message_id = room_history_old_history[1]['UserMessage']['id']
                        except:
                            continue

                    print "last_imported_message_id for room %d is %s" % (id, last_imported_message_id)

                    with open("%s/rooms/%d/history.json" % (new_import_folder, id), 'r') as room_json:
                        room_history = json.load(room_json)
                    parse_room_mattermost(room_history, id, room_name, 1, last_imported_message_id)



elif type == "direct_posts":
    print "export hipchat private chat history to mattermost json"
    file_dirs = []
    id_to_nickname_dict = id_to_nickname()
    if increment:
        basedir = "%s/%s" % (new_import_folder, "users")

        all_old_ids = list()
        all_new_ids = list()
        for u in all_old_users:
            all_old_ids.append(int(u['User']['id']))
        for u in all_new_users:
            all_new_ids.append(int(u['User']['id']))
        diff_list = diff(all_new_ids, all_old_ids)
    else:
        basedir = "files"

    for dirname in os.listdir(basedir):
        if dirname != "files":
            try:
                diff_list.index(int(dirname))
                is_new_user = 1
            except:
                is_new_user = 0
            result_direct_post_file = open('exported_user_history/%d_direct_post.jsonl' % int(dirname), 'w')
            write_direct_post("{ \"type\": \"version\", \"version\": %d }" % version)
            for t in range(0,2):
                print "stage is %d for user %d" % (t,int(dirname))
                parse_direct_posts(int(dirname), t, id_to_nickname_dict, is_new_user)


elif type == "public_room_users":
    print "export user in public rooms"
    result_public_rooms = open('exported_special_files/public_room_members.json', 'w', 0)
    write_public_room_members("[")
    dict_all_rooms_senders = read_all_rooms_to_dict()
    email_to_id_dict = email_to_id()
    if increment:
        users_from_crowd_ = users_from_crowd_new_import
    else:
        users_from_crowd_ = users_from_crowd

    count = len(users_from_crowd_)
    for user in users_from_crowd_:
        current_idx = users_from_crowd_.index(user)
        list_end = count - current_idx
        email = user['user']['email']
        try:
            id = email_to_id_dict[email]
        except:
            id = 0
        if id != 0:
            users_public_rooms = get_rooms_by_userid(id, dict_all_rooms_senders)
            if users_public_rooms != 0:
                if current_idx == 1:
                    next_idx = current_idx + 1
                    write_public_room_members(json.dumps(users_public_rooms))
                else:
                    write_public_room_members(",")
                    write_public_room_members(json.dumps(users_public_rooms))
    write_public_room_members("]")


else:
    print "nothing to do"