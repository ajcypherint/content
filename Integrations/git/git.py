import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
''' IMPORTS '''

import json
import requests
from datetime import datetime, timedelta
from distutils.util import strtobool

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()

''' GLOBALS/PARAMS '''

USER = demisto.params().get('user')
TOKEN = demisto.params().get('token')
BASE_URL = demisto.params().get('url')
REP = demisto.params().get('repository')
USE_SSL = not demisto.params().get('insecure', False)
FETCH_TIME = demisto.params().get('fetch_time', '3 days')

USER_SUFFIX = "/repos/{}/{}".format(USER, REP)
ISSUE_SUFFIX = "/issues"
RELEASE_SUFFIX = "/releases"

# Headers to be sent in requests
HEADERS = {
    'Authorization': "Bearer " + TOKEN
}
# Remove proxy if not set to true in params
if not demisto.params().get('proxy'):
    del os.environ['HTTP_PROXY']
    del os.environ['HTTPS_PROXY']
    del os.environ['http_proxy']
    del os.environ['https_proxy']


''' HELPER FUNCTIONS '''


def http_request(method, url_suffix, params="", data=""):
    # A wrapper for requests lib to send our requests and handle requests and responses better
    res = requests.request(
        method,
        BASE_URL + url_suffix,
        verify=USE_SSL,
        params=params,
        data=json.dumps(data),
        headers=HEADERS
    )
    # Handle error responses gracefully
    if res.status_code >= 400:
        return_error('Error in API call to Example Integration [%d] - %s' % (res.status_code, res.reason))

    return res.json()


def data_fromating(title, body, milestone, labels, assignees, state):
    """This method creates a dictionary to be used as "data" field in an http request."""
    data = {}
    if (title is not None):
        data['title'] = title
    if (body is not None):
        data['body'] = body
    if (state is not None):
        data['state'] = state
    if (milestone is not None):
        data['milestone'] = int(milestone)
    if (labels is not None):
        data['labels'] = labels.split(',')
    if (assignees is not None):
        data['assignees'] = assignees.split(',')
    return data

def issue_format(issue, result_token=0):
    """ This method gets a HTTP response containing an issue and creates a dictionary with selected
    fields representing an issue in Demisto.

    :param issue:
        An HTTP response representing an issue, formatted as a dictionary
    :param result_token:
        A boolean argument controlling what the function returns

    :return:
        If result_token = 0: returns the dictionary representing the issue.
        If result_token = 1: sends the issue to create context and print it as a result in Demisto
    """
    form = {
        'Id': issue.get('number'),
        'Repository': issue.get('repository_url'),
        "Title": issue.get('title'),
        "Body": issue.get('body'),
        "State": issue.get('state')
    }
    if result_token:
        context_create_issue(issue , form)
    return form

def issue_table_create(issue_list, response):
    """
    This method gets an HTTP response and a list containing several issues, sends each issue
    to be reformatted.
    Finally sends the new issue list to create context and print it
    as a result in Demisto
    :param issue_list:
         A list of issues derived from the HTTP response
    :param response:
        A raw HTTP response sent for 'Contents' field in context
    """
    issuetable = []
    for issue in issue_list:
        issuetable.append(issue_format(issue))

    context_create_issue(response,issuetable)

def context_create_issue(response,issue):
    """
    This method creates GitHub.Issue EntryContext and results to be printed in Demisto
    :param response:
        The raw HTTP response to be inserted to the 'Contents' field
    :param issue:
        A dictionary or a list of dictionaries formatted for Demisto results
    """
    ec = {
        'GitHub.Issue(val.Repository == obj.Repository  && val.Id == obj.Id)': issue
    }
    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['markdown'],
        'Contents': response,
        'HumanReadable': tableToMarkdown("Issue Table", issue),
        'EntryContext': ec
    })


def context_create_release(release_list, response):
    """
    This method creates GitHub.Release EntryContext and results to be printed in Demisto
    :param release_list:
        A list of dictionaries representing GitHub.Release under the repository
    :param response:
        The raw HTTP response to be inserted to the 'Contents' field
    """
    ec = {
        'GitHub.Release( val.URL == obj.URL )': release_list
    }
    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['markdown'],
        'Contents': response,
        'HumanReadable': tableToMarkdown("Release Table", release_list),
        'EntryContext': ec
    })


''' REQUESTS FUNCTIONS '''

def create_issue(title, body="", milestone="", labels=[], assignees=[]):
    if (title==""):
        return_error("Error: No title given for created issue")
    data=data_fromating(title=title, body=body, milestone=milestone, labels=labels, assignees=assignees, state=None)
    response=http_request(method='POST',url_suffix=USER_SUFFIX+ISSUE_SUFFIX,data=data)
    return response

def close_issue(id):
    response=http_request(method='PATCH' , url_suffix=USER_SUFFIX+ISSUE_SUFFIX+"/"+id , data={'state':'closed'})
    return response

def update_issue(id, title, body, state, milestone, labels, assign):
    data=data_fromating(title=title , body=body , milestone=milestone , labels=labels , assignees=assign , state=state)
    response=http_request(method='PATCH',url_suffix=USER_SUFFIX+ISSUE_SUFFIX+"/"+id , data=data)
    if response.get('errors'):
        return_error(response.get('errors'))
    return response

def list_all_issue(only_open):
    params={}
    if (only_open==0):
        params={"state" : "all"}
    response = http_request(method='GET', url_suffix=USER_SUFFIX+ISSUE_SUFFIX, params=params)
    return response

def search_issue(query):
    response=http_request(method='GET', url_suffix='/search/issues', params={'q':query})
    if response.get('errors'):
        return_error(response.get('errors'))
    return response

def get_download_count():
    response = http_request(method='GET', url_suffix=USER_SUFFIX+RELEASE_SUFFIX)
    count_per_release=[]
    for release in response:
        total_download_count = 0
        for asset in release['assets']:
            total_download_count=total_download_count+asset['download_count']
        release_info={
            'URL': release.get('url'),
            'Download_count': total_download_count
        }
        count_per_release.append(release_info)
    context_create_release(release_list=count_per_release, response=response)


''' COMMANDS MANAGER / SWITCH PANEL '''

def create_command():
    args=demisto.args()
    response=create_issue(args.get('title'),args.get('body'),
                          args.get('milestone'),args.get('labels'),args.get('assignees'))
    issue_format(response,result_token=1)


def close_command():
    id=demisto.args().get('issue_number')
    response=close_issue(id)
    issue_format(response , result_token=1)

def update_command():
    args=demisto.args()
    response=update_issue(args['issue_number'],args.get('title'),args.get('body'),args.get('state'),
                          args.get('milestone'),args.get('labels'),args.get('assignees'))
    issue_format(response, result_token=1)

def list_all_command():
    only_open=demisto.args().get('open_or_all')
    response=list_all_issue(int(only_open))
    issue_table_create(response, response)

def search_command():
    q=demisto.args().get('query')
    response=search_issue(q)
    issue_table_create(response['items'], response)

def get_download_command():
    get_download_count()

def fetch_incidents_command():
    last_run = demisto.getLastRun()
    if last_run and last_run.has_key('start_time'):
        start_time = datetime.strptime(last_run.get('start_time'), '%Y-%m-%dT%H:%M:%SZ')
    else:
        start_time = datetime.now()
    last_time = start_time
    issue_list = http_request(method='GET', url_suffix=USER_SUFFIX+ISSUE_SUFFIX)
    incedents = []
    for issue in issue_list:
        updated_at=issue.get('updated_at')
        updated_at = datetime.strptime(updated_at, '%Y-%m-%dT%H:%M:%SZ')
        if updated_at>start_time:
            inc={
                'name': issue.get('url'),
                'occurred': updated_at,
                'rawJSON': json.dumps(issue)

            }
            incedents.append(inc)
            if updated_at>last_time:
                last_time = updated_at
    demisto.setLastRun({'start_time': datetime.strftime(last_time, '%Y-%m-%dT%H:%M:%SZ')})
    demisto.incidents(incedents)



'''EXECUTION'''
LOG('command is %s' % (demisto.command(),))
try:
    if demisto.command()=='create-issue':
        create_command()
    elif demisto.command()=='close-issue':
        close_command()
    elif demisto.command()=='update-issue':
        update_command()
    elif demisto.command()=='list-all-issues':
        list_all_command()
    elif demisto.command()=='search-issues':
        search_command()
    elif demisto.command()=='get-download-count':
        get_download_command()
    elif demisto.command()=='fetch-incidents':
        fetch_incidents_command()
    elif demisto.command()=='test-module':
        demisto.results("ok")
except Exception as e:
    LOG(e.message)
    LOG.print_log()
    raise
