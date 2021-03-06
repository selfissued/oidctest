import json
import logging
import os
import shutil

from future.backports.urllib.parse import urlparse

from oic.oauth2.provider import error_response

from oic.utils.http_util import extract_from_request, SeeOther
from oic.utils.http_util import Response
from oic.utils.http_util import Unauthorized
from oic.utils.http_util import NotFound
from oic.utils.http_util import ServiceError
from oic.utils.http_util import BadRequest
from oic.utils.keyio import key_summary
from oic.utils.webfinger import OIC_ISSUER
from oic.utils.webfinger import WebFinger
# All endpoints the OpenID Connect Provider should answer on
from oic.oic.provider import AuthorizationEndpoint
from oic.oic.provider import EndSessionEndpoint
from oic.oic.provider import TokenEndpoint
from oic.oic.provider import UserinfoEndpoint
from oic.oic.provider import RegistrationEndpoint

from otest import resp2json
from otest.events import EV_EXCEPTION
from otest.events import EV_FAULT
from otest.events import EV_REQUEST
from otest.events import EV_REQUEST_ARGS
from otest.events import EV_RESPONSE
from otest.events import layout
from otest.events import Operation

from oidctest.utils import create_rp_tar_archive

__author__ = 'roland'

logger = logging.getLogger(__name__)

HEADER = "---------- %s ----------"


def dump_log(session_info, events):
    try:
        file_name = os.path.join("log", session_info["oper_id"],
                                 session_info["test_id"])
        _dir = os.path.join("log", session_info["oper_id"])
    except KeyError:
        file_name = os.path.join("log", session_info["addr"],
                                 session_info["test_id"])
        _dir = os.path.join("log", session_info["addr"])

    try:
        fp = open(file_name, "a+")
    except IOError:
        try:
            os.makedirs(_dir)
        except OSError:
            pass

        try:
            fp = open(file_name, "w")
        except Exception as err:
            logging.error(
                "Couldn't dump to log file {} reason: {}").format(
                file_name, err)
            raise

    _elem = [layout(0, ev) for ev in events]
    fp.write("\n".join(_elem))
    fp.write("\n\n")
    fp.close()


def find_identifier(uri):
    if uri.startswith("http"):
        p = urlparse(uri)
        return p.path[1:]  # Skip leading "/"
    elif uri.startswith("acct:"):
        a = uri[5:]
        l, d = a.split("@")
        return l


def wsgi_wrapper(environ, start_response, func, session_info, events, jlog):
    kwargs = extract_from_request(environ)

    kwargs['test_cnf'] = session_info['test_conf']
    try:
        oos = kwargs['test_cnf']['out_of_scope']
    except KeyError:
        pass
    else:
        if func.__name__ in oos:
            resp = error_response(
                error='incorrect_behavior',
                descr='You should not talk to this endpoint in this test')
            return resp(environ, start_response)

    events.store(EV_REQUEST_ARGS, kwargs["request"])
    jlog.info({'operation': func.__name__, 'kwargs': kwargs})
    args = func(**kwargs)

    try:
        resp, state = args
        jlog.info({'response_from': func.__name__, 'response': resp2json(resp),
                   'state': state})
        events.store(EV_RESPONSE, resp.message)
        dump_log(session_info, events)
        return resp(environ, start_response)
    except TypeError:
        resp = args
        jlog.info({'response_from': func.__name__, 'response': resp2json(resp)})
        events.store(EV_RESPONSE, resp.message)
        dump_log(session_info, events)
        return resp(environ, start_response)
    except Exception as err:
        jlog.error({'response_from': func.__name__, 'err': err})
        events.store(EV_EXCEPTION, err)
        dump_log(session_info, events)
        raise


# noinspection PyUnusedLocal
def token(environ, start_response, session_info, events, jlog, **kwargs):
    events.store(EV_REQUEST, Operation("AccessToken"))
    _op = session_info["op"]
    logger.info('OP keys:{}'.format(key_summary(_op.keyjar, '')))
    return wsgi_wrapper(environ, start_response, _op.token_endpoint,
                        session_info, events, jlog)


# noinspection PyUnusedLocal
def authorization(environ, start_response, session_info, events, jlog,
                  **kwargs):
    events.store(EV_REQUEST, Operation("Authorization"))
    _op = session_info["op"]
    logger.info('OP keys:{}'.format(key_summary(_op.keyjar, '')))
    return wsgi_wrapper(environ, start_response, _op.authorization_endpoint,
                        session_info, events, jlog)


# noinspection PyUnusedLocal
def userinfo(environ, start_response, session_info, events, jlog, **kwargs):
    events.store(EV_REQUEST, Operation("UserInfo"))
    _op = session_info["op"]
    logger.info('OP keys:{}'.format(key_summary(_op.keyjar, '')))
    return wsgi_wrapper(environ, start_response, _op.userinfo_endpoint,
                        session_info, events, jlog)


# noinspection PyUnusedLocal
def op_info(environ, start_response, session_info, events, jlog, **kwargs):
    _ev = Operation("ProviderConfiguration", path = environ["PATH_INFO"])
    try:
        _ev.query = environ["QUERY_STRING"]
    except KeyError:
        pass
    events.store(EV_REQUEST, _ev)
    _op = session_info["op"]
    logger.info('OP keys:{}'.format(key_summary(_op.keyjar, '')))
    return wsgi_wrapper(environ, start_response, _op.providerinfo_endpoint,
                        session_info, events, jlog)


# noinspection PyUnusedLocal
def registration(environ, start_response, session_info, events, jlog, **kwargs):
    events.store(EV_REQUEST, Operation("ClientRegistration"))
    _op = session_info["op"]

    if environ["REQUEST_METHOD"] == "POST":
        return wsgi_wrapper(environ, start_response, _op.registration_endpoint,
                            session_info, events, jlog)
    elif environ["REQUEST_METHOD"] == "GET":
        return wsgi_wrapper(environ, start_response, _op.read_registration,
                            session_info, events, jlog)
    else:
        resp = ServiceError("Method not supported")
        return resp(environ, start_response)


# noinspection PyUnusedLocal
def check_id(environ, start_response, session_info, events, jlog, **kwargs):
    _op = session_info["op"]

    return wsgi_wrapper(environ, start_response, _op.check_id_endpoint,
                        session_info, events, jlog)


# noinspection PyUnusedLocal
def endsession(environ, start_response, session_info, events, jlog, **kwargs):
    _op = session_info["op"]
    return wsgi_wrapper(environ, start_response, _op.endsession_endpoint,
                        session_info=session_info, events=events, jlog=jlog)


def webfinger(environ, start_response, session_info, events, jlog, **kwargs):
    _query = session_info['parameters']
    events.store(EV_REQUEST, Operation("WebFinger", _query))

    try:
        assert _query["rel"] == [OIC_ISSUER]
        resource = _query["resource"][0]
    except AssertionError:
        errmsg = "Wrong 'rel' value: %s" % _query["rel"][0]
        events.store(EV_FAULT, errmsg)
        resp = BadRequest(errmsg)
    except KeyError:
        errmsg = "Missing 'rel' parameter in request"
        events.store(EV_FAULT, errmsg)
        resp = BadRequest(errmsg)
    else:
        wf = WebFinger()

        _url = os.path.join(kwargs["op_arg"]["baseurl"],
                            session_info['oper_id'],
                            session_info["test_id"])

        _mesg = wf.response(subject=resource, base=_url)
        if session_info['test_id'] == 'rp-discovery-webfinger-http-href':
            _msg = json.loads(_mesg)
            _msg['links'][0]['href'] = _msg['links'][0]['href'].replace(
                'https', 'http')
            _mesg = json.dumps(_msg)
        elif session_info['test_id'] == 'rp-discovery-webfinger-unknown-member':
            _msg = json.loads(_mesg)
            _msg['dummy'] = 'foobar'
            _mesg = json.dumps(_msg)

        resp = Response(_mesg,
                        content="application/jrd+json")

        events.store(EV_RESPONSE, resp.message)

    jlog.info(resp2json(resp))

    dump_log(session_info, events)
    return resp(environ, start_response)


# noinspection PyUnusedLocal
def verify(environ, start_response, session_info, events, jlog, **kwargs):
    _op = session_info["op"]
    return wsgi_wrapper(environ, start_response, _op.verify_endpoint,
                        session_info, events, jlog)


def static_file(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


# noinspection PyUnresolvedReferences
def static(environ, start_response, path):
    logger.info("[static]sending: %s" % (path,))

    try:
        text = open(path).read()
        if path.endswith(".ico"):
            start_response('200 OK', [('Content-Type', "image/x-icon")])
        elif path.endswith(".html"):
            start_response('200 OK', [('Content-Type', 'text/html')])
        elif path.endswith(".json"):
            start_response('200 OK', [('Content-Type', 'application/json')])
        elif path.endswith(".txt"):
            start_response('200 OK', [('Content-Type', 'text/plain')])
        elif path.endswith(".css"):
            start_response('200 OK', [('Content-Type', 'text/css')])
        elif path.endswith(".tar"):
            start_response('200 OK', [('Content-Type', 'application/x-tar')])
        else:
            start_response('200 OK', [('Content-Type', 'text/plain')])
        try:
            return [text.encode('utf8')]
        except ValueError:
            return [text]
    except IOError:
        resp = NotFound()
        return resp(environ, start_response)


# noinspection PyUnusedLocal
def safe(environ, start_response):
    _op = environ["oic.oas"]
    _srv = _op.server
    _log_info = _op.logger.info

    _log_info("- safe -")
    # _log_info("env: %s" % environ)
    # _log_info("handle: %s" % (handle,))

    try:
        _authz = environ["HTTP_AUTHORIZATION"]
        (_typ, code) = _authz.split(" ")
        assert _typ == "Bearer"
    except KeyError:
        resp = BadRequest("Missing authorization information")
        return resp(environ, start_response)

    try:
        _sinfo = _srv.sdb[code]
    except KeyError:
        resp = Unauthorized("Not authorized")
        return resp(environ, start_response)

    _info = "'%s' secrets" % _sinfo["sub"]
    resp = Response(_info)
    return resp(environ, start_response)


# noinspection PyUnusedLocal
def css(environ, start_response):
    try:
        _info = open(environ["PATH_INFO"]).read()
        resp = Response(_info)
    except (OSError, IOError):
        resp = NotFound(environ["PATH_INFO"])

    return resp(environ, start_response)


# ----------------------------------------------------------------------------

def clear_log(path, environ, start_response, lookup):
    # verify that the path is reasonable
    head, tail = os.path.split(path)
    if head != 'clear':  # don't do anything
        resp = NotFound(environ["PATH_INFO"])
        return resp(environ, start_response)

    wd = os.getcwd()
    _dir = os.path.join(wd, 'log', tail)
    if os.path.isdir(_dir):
        create_rp_tar_archive(tail, True)
        shutil.rmtree(_dir)
    else:
        resp = NotFound('No logfile by the name "{}"'.format(tail))
        return resp(environ, start_response)

    resp = SeeOther('/log')
    return resp(environ, start_response)


def make_tar(path, environ, start_response, lookup):
    # verify that the path is reasonable
    head, tail = os.path.split(path)
    if head != 'mktar' and head != 'mktar/tar':  # don't do anything
        resp = NotFound(environ["PATH_INFO"])
        return resp(environ, start_response)

    resp = create_rp_tar_archive(tail)
    return resp(environ, start_response)


def display_log(path, environ, start_response, lookup):
    """
    path = 'log' or path = 'log/tester_id' or path = 'log/tester_id/test_id

    :param environ:
    :param start_response:
    :param lookup:
    :return:
    """
    if path == "logs":
        path = "log"

    while path.endswith('/'):
        path = path[:-1]

    if os.path.isfile(path):
        return static(environ, start_response, path)
    elif os.path.isdir(path):
        if '/' in path:
            p = path.split('/')
            tester_id = '/' + p[1]
        else:
            tester_id = ''

        item = []
        for (dirpath, dirnames, filenames) in os.walk(path):
            if dirnames:
                # item = [(fn, os.path.join(path, fn)) for fn in dirnames]
                item = [(fn, fn) for fn in dirnames]
                break
            if filenames:
                # item = [(fn, os.path.join(path, fn)) for fn in filenames]
                item = [(fn, fn) for fn in filenames]
                break

        item.sort()
        resp = Response(mako_template="logs.mako",
                        template_lookup=lookup,
                        headers=[])
        argv = {"logs": item, 'testid': tester_id}

        return resp(environ, start_response, **argv)
    else:
        resp = Response("No saved logs")
        return resp(environ, start_response)


ENDPOINTS = [
    AuthorizationEndpoint(authorization),
    TokenEndpoint(token),
    UserinfoEndpoint(userinfo),
    RegistrationEndpoint(registration),
    EndSessionEndpoint(endsession),
]

URLS = [
    (r'^verify', verify),
    (r'.well-known/openid-configuration', op_info),
    (r'.well-known/webfinger', webfinger),
    (r'.+\.css$', css),
    (r'safe', safe),
    (r'log', display_log)
]


def add_endpoints(extra):
    global URLS

    for endp in extra:
        URLS.append(("^%s" % endp.etype, endp.func))
