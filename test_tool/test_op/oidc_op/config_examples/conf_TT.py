from sslconf import *

PORT = 60050
BASE = "http://localhost"
KEYS = [
    {"key": "../keys/enc.key", "type": "RSA", "use": ["enc"]},
    {"key": "../keys/sig.key", "type": "RSA", "use": ["sig"]},
    {"crv": "P-256", "type": "EC", "use": ["sig"]},
    {"crv": "P-256", "type": "EC", "use": ["enc"]}
]

TOOL = {
    "acr_values": "1 2",
    "claims_locales": "en",
    "instance_id": "60050",
    "login_hint": "foobar",
    "profile": "C.T.T.T.ns.",
    "ui_locales": "en",
    "webfinger_email": "foobar@localhost:8040",
    "webfinger_url": "https://localhost:8040/foobar",
    "issuer": "https://localhost:8040/"
}

CLIENT = {
    "behaviour": {
        "scope": ["openid", "profile", "email", "address", "phone"]
    },
    "preferences": {
        "default_max_age": 3600,
        "grant_types": [
            "authorization_code", "implicit", "refresh_token",
            "urn:ietf:params:oauth:grant-type:jwt-bearer:"],
        "id_token_signed_response_alg": [
            "RS256", "RS384", "RS512", "HS512", "HS384", "HS256"
        ],
        "request_object_signing_alg": [
            "RS256", "RS384", "RS512", "HS512", "HS384", "HS256"
        ],
        "require_auth_time": True,
        "response_types": [
            "code", "token", "id_token", "token id_token",
            "code id_token", "code token", "code token id_token"
        ],
        "subject_type": "public",
        "token_endpoint_auth_method": [
            "client_secret_basic", "client_secret_post",
            "client_secret_jwt", "private_key_jwt"
        ],
        "userinfo_signed_response_alg": [
            "RS256", "RS384", "RS512", "HS512", "HS384", "HS256"
        ],
    },
    "registration_info": {
        "application_name": "OIC test tool",
        "application_type": "web",
        "redirect_uris": ["{}/authz_cb"],
        "contacts": ["roland@example.com"],
        "post_logout_redirect_uris": ["{}/logout"]},
}
