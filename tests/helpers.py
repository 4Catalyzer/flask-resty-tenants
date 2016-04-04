import inspect
import itertools
import json


def request(client, method, path, data, **kwargs):
    return client.open(
        path,
        method=method,
        content_type='application/json',
        data=json.dumps({'data': data}),
        **kwargs
    )


def get_body(response):
    assert response.mimetype == 'application/json'
    return json.loads(response.get_data(as_text=True))


def get_data(response):
    return get_body(response)['data']


def get_errors(response):
    return get_body(response)['errors']


def get_subclasses(module, sup_cls):
    return [cls for name, cls in inspect.getmembers(module)
            if inspect.isclass(cls) and issubclass(cls, sup_cls) and
            inspect.getmodule(cls) == module]


def assert_value(actual, expected):
    if isinstance(expected, dict):
        for k, v in expected.items():
            assert_value(actual.get(k, None), v)
    elif isinstance(expected, list):
        for a, e in itertools.izip_longest(actual, expected):
            assert_value(a, e)
    else:
        assert actual == expected


def assert_response(response, expected_status=200, expected_data=None):
    """check the results of a response. The data is checked against either the
    data or the errors in the body, depending on the expected status. It is
    allowed for the data to have more keys than the one specified"""
    assert response.status_code == expected_status

    if not expected_data:
        return

    if 200 <= response.status_code < 300:
        response_data = get_data(response)
    else:
        response_data = get_errors(response)

    assert_value(response_data, expected_data)
