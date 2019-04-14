from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
import requests
from main.models import Teams, Polls, Votes
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from collections import defaultdict
import string
import random
from django.views.decorators.csrf import csrf_exempt
import os
import json
import math
import re

client_id = '64961225782.609226531318'
client_secret = os.environ.get('SLACK_OAUTH_TOKEN', '')

emoji = [
    ':zero:',
    ':one:',
    ':two:',
    ':three:',
    ':four:',
    ':five:',
    ':six:',
    ':seven:',
    ':eight:',
    ':nine:',
    ':keycap_ten:',
]


def add_poll(timestamp, channel, question, options):
    poll = Polls(timestamp=timestamp, channel=channel, question=question, options=json.dumps(options))
    poll.save()
    return poll


def latest_poll(channel):
    return Polls.objects.filter(channel=channel).latest('timestamp')


def timestamped_poll(timestamp):
    return Polls.objects.filter(timestamp=timestamp)[0]


def update_vote(poll, option, users):
    users = json.dumps(users)
    try:
        vote = Votes.objects.get(poll=poll, option=option)
        vote.users = users
    except ObjectDoesNotExist:
        vote = Votes(poll=poll, option=option, users=users)
    vote.save()
    return vote


def get_all_votes(poll):
    return Votes.objects.filter(poll=poll)


name_cache = {}


def parse_message(message):
    global name_cache
    #
    # parse the message into lines. lines[0] is the question, and the rest are the options
    lines = message['text'].split('\n')
    lines = [line for line in lines if line != '']

    question = ''
    options = []
    votes = defaultdict(list)
    for i, line in enumerate(lines):
        if i == 0:
            # get the question
            question = re.search(r'\*(.*?)\*', line).group(1).strip()
        else:
            #
            # parse the options to extract the option text and the voted users
            matches = re.search(r'(.*)`.*?`([^`]*?)$', line.lstrip(emoji[i - 1]))
            options.append(matches.group(1).strip())
            names = matches.group(2).strip().replace('<@', '').replace('>', '').split(',')
            vote_list = []
            for user_id in names:
                if user_id == '':
                    continue
                name = user_id.strip()
                if name in name_cache:
                    vote_list.append(name_cache[name])
                else:
                    method_url = 'https://slack.com/api/users.info'
                    method_params = {
                        "token": client_secret,
                        "user": name
                    }
                    response_data = requests.get(method_url, params=method_params)
                    response = response_data.json()
                    res = '@' + response["user"]["name"]
                    vote_list.append(res)
                    name_cache[name] = res
            votes[options[i - 1]] = vote_list
    return question, options, votes


def index(request):
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(36))
    context = {"state": state}
    return render(request, "main/index.html", context)


def oauthcallback(request):
    if "error" in request.GET:
        status = "Authentication failed, as the authentication process is aborted. Redirecting back to the homepage..."
        context = {"status": status}
        return render(request, "main/oauthcallback.html", context)

    code = request.GET["code"]

    url = "https://slack.com/api/oauth.access"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }

    r = requests.get(url, params=data)
    query_result = r.json()
    if query_result["ok"]:
        access_token = query_result["access_token"]
        team_name = query_result["team_name"]
        team_id = query_result["team_id"]

        try:
            team = Teams.objects.get(team_id=team_id)
        except ObjectDoesNotExist:
            # new Team (yay!)
            new_team = Teams(access_token=access_token, team_name=team_name, team_id=team_id,
                             last_changed=timezone.now())
            new_team.save()
        else:
            team.access_token = access_token
            team.team_name = team_name
            team.save()

    else:
        status = "Oauth authentication failed. Redirecting back to the homepage..."
        context = {"status": status}
        return render(request, "main/oauthcallback.html", context)

    status = "Oauth authentication successful! You can now start using /poll. Redirecting back to the homepage..."
    context = {"status": status}
    return render(request, "main/oauthcallback.html", context)


def check_token(request):
    verifier = os.environ.get('SLACK_VERIFICATION_TOKEN', '')
    if request.method != "POST":
        return HttpResponseBadRequest("400 Request should be of type POST.")
    if "token" in request.POST:
        sent_token = request.POST["token"]
    elif "payload" in request.POST and "token" in json.loads(request.POST["payload"]):
        sent_token = json.loads(request.POST["payload"])["token"]
    else:
        return HttpResponseBadRequest("400 Request is not signed!")

    if verifier != sent_token:
        return HttpResponseBadRequest("400 Request is not signed correctly!")
    return None


def format_text(question, options, votes):
    text = "*" + question + "*\n\n"

    for i, option in enumerate(options):
        to_add = emoji[i] + ' '
        to_add += option
        to_add += ' `' + str(len(votes[option])) + '`'
        to_add += ', '.join(votes[option])
        # Add count + condorcet score here
        text += (to_add + '\n')
    return text


def format_attachments(options):
    actions = []
    for i, option in enumerate(options):
        attach = {"name": "option", "text": emoji[i], "type": "button", "value": option}
        actions.append(attach)
    actions.append({"name": "addMore", "text": "Add option", "type": "button", "value": "Add option"})
    attachments = []
    for i in range(int(math.ceil(len(actions) / 5.0))):
        attachment = {"text": "", "callback_id": "options", "attachment_type": "default",
                      "actions": actions[5 * i: 5 * i + 5]}
        attachments.append(attachment)

    return json.dumps(attachments)


def create_dialog(payload):
    method_url = 'https://slack.com/api/dialog.open'
    method_params = {
        "token": client_secret,
        "trigger_id": payload['trigger_id'],
        "dialog": {
            "title": "Add an option",
            "state": payload['original_message']['ts'],
            "callback_id": "newOption",
            "elements": [{
                "type": "text",
                "label": "New Option",
                "name": "new_option"
            }]
        }
    }
    method_params['dialog'] = json.dumps(method_params['dialog'])
    requests.post(method_url, params=method_params)


@csrf_exempt
def interactive_button(request):
    error_code = check_token(request)
    if error_code is not None:
        return error_code
    payload = json.loads(request.POST['payload'])
    question = ""
    options = []
    votes = defaultdict(list)
    ts = ""
    if payload["callback_id"] == "newOption":
        ts = payload['state']
        poll = timestamped_poll(payload['state'])
        question = poll.question
        options = json.loads(poll.options)
        votes_obj = get_all_votes(poll)
        for vote in votes_obj:
            votes[vote.option] = json.loads(vote.users)
        options.append(payload['submission']['new_option'])
        poll.options = json.dumps(options)
        poll.save()
    elif payload["actions"][0]["name"] == "addMore":
        ts = payload['original_message']['ts']
        question, options, votes = parse_message(payload['original_message'])
        create_dialog(payload)
    elif payload['actions'][0]["name"] == "option":
        ts = payload['original_message']['ts']
        question, options, votes = parse_message(payload['original_message'])
        lst = votes[payload["actions"][0]["value"]]
        if "@" + payload['user']['name'] in lst:
            votes[payload["actions"][0]["value"]].remove("@" + payload['user']['name'])
        else:
            votes[payload['actions'][0]['value']].append("@" + payload["user"]["name"])
        poll = timestamped_poll(payload['original_message']['ts'])
        update_vote(poll, payload['actions'][0]['value'], votes[payload['actions'][0]['value']])
    text = format_text(question, options, votes)
    attachments = format_attachments(options)
    method_url = 'https://slack.com/api/chat.update'
    updated_message = {
        "token": client_secret,
        "channel": payload['channel']['id'],
        "ts": ts,
        "text": text,
        "attachments": attachments,
        "parse": "full"
    }
    requests.post(method_url, params=updated_message)
    return HttpResponse()


def send_error_message(channel, user, msg):
    post_message_url = "https://slack.com/api/chat.postEphemeral"
    post_message_params = {
        "token": client_secret,
        "text": msg,
        "channel": channel,
        "user": user,
    }
    requests.post(post_message_url, params=post_message_params)


def send_poll_message(channel, user, cmd, text, attachment):
    post_message_url = "https://slack.com/api/chat.postMessage"
    post_message_params = {
        "token": client_secret,
        "text": cmd,
        "channel": channel,
        "as_user": user
    }
    requests.post(post_message_url, params=post_message_params)
    post_message_params = {
        "token": client_secret,
        "text": text,
        "channel": channel,
        "icon_url": "https://sherlock-poll.tdf.ringier.ch/static/main/sherlockpolllogo-colors.png",
        "mrkdwn": 'true',
        "parse": 'full',
        "attachments": attachment
    }
    text_response = requests.post(post_message_url, params=post_message_params)
    return text_response.json()["ts"]  # return message timestamp


@csrf_exempt
def sherlock_poll(request):
    error_code = check_token(request)
    if error_code is not None:
        return error_code

    channel = request.POST["channel_id"]
    user = request.POST["user_id"]
    data = request.POST["text"]
    cmd = request.POST["command"] + ' ' + request.POST["text"]

    # replace the Slack auto-formatted “ ” to "
    data = data.replace(u'\u201C', '"')
    data = data.replace(u'\u201D', '"')

    items = data.split('"')

    if len(items) < 4:
        msg = "Darn - that I don't understand you. Please say: "
        msg += '`/sherlock-poll "Question" "Answer 1" "Answer 2"`'
        send_error_message(channel, user, msg)
    elif len(items) < 6:
        msg = "Darn - that normally we don't run a poll with only one option."
        send_error_message(channel, user, msg)
    elif len(items) > 23:
        msg = "Darn - that you gave too many options. Please, 10 options the most."
        send_error_message(channel, user, msg)
    else:
        question = items[1]
        options = []
        for i in range(1, len(items) + 1):
            if i % 2 == 0 and i > 2:
                options.append(items[i - 1])
        # all data ready for initial message at this point
        text = format_text(question, options, votes=defaultdict(list))
        attachment = format_attachments(options)
        timestamp = send_poll_message(channel, user, cmd, text, attachment)
        add_poll(timestamp, channel, question, options)

    return HttpResponse()  # Empty 200 HTTP response, to not display any additional content in Slack


def privacy_policy(request):
    return render(request, "main/privacy-policy.html")
