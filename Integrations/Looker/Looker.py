import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
''' IMPORTS '''

import requests
import traceback

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()

''' GLOBALS/PARAMS '''
DEFAULT_RESULTS_LIMIT = 50
MAX_TIMEOUT_MINUTES = 5
SESSION_VALIDITY_THRESHOLD = timedelta(minutes=MAX_TIMEOUT_MINUTES)
CLIENT_ID = demisto.params().get('client_id')
CLIENT_SECRET = demisto.params().get('client_secret')
# Remove trailing slash to prevent wrong URL path to service
SERVER = demisto.params()['url'][:-1] if (demisto.params()['url']
                                          and demisto.params()['url'].endswith('/')) else demisto.params()['url']
# Should we use SSL
USE_SSL = not demisto.params().get('unsecure', False)
# How many time before the first fetch to retrieve incidents
FETCH_TIME = demisto.params().get('fetch_time', '3 days')
# Service base URL
BASE_URL = SERVER + '/api/3.0'
# Request headers (preparation)
HEADERS = {}


''' HELPER FUNCTIONS '''


def verify_url(url):
    # validate url parameter format, extract port
    try:
        server, port = url.rsplit(':', 1)
        assert 0 < int(port) < 65536

    except (ValueError, AssertionError):
        return_error("Incorrect URL format. Use the following format: https://example.looker.com:19999\n"
                     "The default port for Looker API is 19999.")


def http_request(method, url_suffix, params=None, data=None, response_type='json'):
    # A wrapper for requests lib to send our requests and handle requests and responses better
    res = requests.request(
        method,
        BASE_URL + url_suffix,
        verify=USE_SSL,
        params=params,
        data=data,
        headers=HEADERS
    )
    # Handle error responses gracefully
    if res.status_code not in {200}:
        raise requests.exceptions.HTTPError('Error in API call to Looker [%d] - %s' % (res.status_code, res.reason))

    return res.json() if response_type == 'json' else res.content


def get_new_token():
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response_json = http_request('POST', '/login', data=data)

    return {
        'token': response_json['access_token'],
        'expires': datetime.utcnow().timestamp() + response_json['expires_in']
    }


def get_session_token():
    global HEADERS
    ic = demisto.getIntegrationContext()

    if CLIENT_ID not in ic or 'expires' not in ic[CLIENT_ID] \
            or datetime.fromtimestamp(ic[CLIENT_ID]['expires']) < datetime.utcnow() + SESSION_VALIDITY_THRESHOLD:
        ic[CLIENT_ID] = get_new_token()
        if demisto.command() != 'test-module':
            demisto.setIntegrationContext(ic)

    HEADERS['Authorization'] = 'token {}'.format(ic[CLIENT_ID]['token'])


def get_limit():
    try:
        limit = int(demisto.args().get('limit', DEFAULT_RESULTS_LIMIT))
        return None if limit == 0 else limit

    except ValueError:
        return_error("limit must be a number")


def get_look_id_from_name(name):

    looks = search_looks_request({'title': name})

    if len(looks) < 1:
        raise Exception(f'No Look found with the name {name}.')

    if len(looks) > 1:
        raise Exception(f'There is more than one Look with the name {name}.'
                        f"Use look ID instead - It can be found in the Look's URL or by running looker-search-looks")

    return looks[0]['ID']


def full_path_headers(src_data, base_path):
    def to_full_path(k):
        return f"{base_path}.{k}"

    def full_path_headers_for_dict(src):
        if not isinstance(src, dict):
            return src

        return {to_full_path(k): v for k, v in src.items()}

    if not isinstance(src_data, list):
        src_data = [src_data]

    return [full_path_headers_for_dict(x) for x in src_data]


''' COMMANDS + REQUESTS FUNCTIONS '''


def test_module():
    """
    Performs basic get request to check connectivity and authentication
    """
    http_request('GET', '/user')


def run_look_command():
    look_id = demisto.args().get('id')
    look_name = demisto.args().get('name')
    if not any((look_id, look_name)):
        raise Exception(f'Provide Look id or name.')
    if look_name and not look_id:
        look_id = get_look_id_from_name(look_name)

    result_format = demisto.args()['result_format']
    limit = get_limit()
    fields = argToList(demisto.args().get('result_format'))

    contents = run_look_request(look_id, result_format, limit, fields)

    if result_format == 'json':
        camelized = camelize(contents, delim='_')  # TODO: Replace . with _
        formatted_contents = [{k.replace('.', '_'): v for k, v in d.items()} for d in camelized]
        if not isinstance(formatted_contents, list):
            formatted_contents = [formatted_contents]
        context = {
            'LookerResults(val.LookID && val.LookID === obj.LookID)': {
                'LookID': int(look_id),
                'Results': formatted_contents
            }
        }

        full_path_header_content = full_path_headers(formatted_contents, 'LookerResults.Results')

        demisto.results({
            'Type': entryTypes['note'],
            'ContentsFormat': formats['json'],
            'Contents': contents,
            'ReadableContentsFormat': formats['markdown'],
            'HumanReadable': tableToMarkdown(f'Results for look #{look_id}', full_path_header_content, removeNull=True),
            'EntryContext': context
        })

        if contents:
            demisto.results('This command has dynamic output keys.\nTo access them in the context, '
                            'copy the key\'s path from the column header in the results table.')

    elif result_format == 'csv':
        demisto.results(fileResult('look_result.csv', contents, entryTypes['entryInfoFile']))


def run_look_request(look_id, result_format, limit, fields):
    endpoint_url = f'/looks/{look_id}/run/{result_format}'
    params = {}
    if limit:
        params['limit'] = limit
    if fields:
        params['fields'] = fields
    return http_request('GET', endpoint_url, params=params, response_type=result_format)


def search_looks_command():
    command_args = ('space_id', 'user_id')  # Possible command arguments
    args_dict = {k: demisto.args()[k] for k in command_args if k in demisto.args()}  # Get args that were passed

    # Arguments with special logic
    args_dict['limit'] = get_limit()
    if 'name' in demisto.args():
        args_dict['title'] = demisto.args()['name']

    contents = search_looks_request(args_dict)
    context = {f'Looker.Look(val.ID && val.ID === {look["ID"]})': look for look in contents}

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(f'Look search results', contents, removeNull=True),
        'EntryContext': context
    })


def search_looks_request(args):
    endpoint_url = '/looks/search'
    params = {k: v for k, v in args.items() if v}
    params['fields'] = 'id, title, space, updated_at'
    response = http_request('GET', endpoint_url, params=params)

    if not isinstance(response, list):
        response = [response]

    return [
        {
            'ID': look['id'],
            'Name': look['title'],
            'SpaceID': look['space']['id'],
            'SpaceName': look['space']['name'],
            'LastUpdated': look['updated_at'].replace('+00:00', 'Z')
        } for look in response
    ]


''' COMMANDS MANAGER / SWITCH PANEL '''

LOG('Command being called is %s' % (demisto.command()))
try:
    handle_proxy()
    verify_url(SERVER)
    get_session_token()

    if demisto.command() == 'test-module':
        test_module()
        demisto.results('ok')
    elif demisto.command() == 'looker-run-look':
        run_look_command()
    elif demisto.command() == 'looker-search-looks':
        search_looks_command()

# Log exceptions
except Exception as e:
    LOG(e)
    LOG(traceback.format_exc())
    LOG.print_log()
    raise
