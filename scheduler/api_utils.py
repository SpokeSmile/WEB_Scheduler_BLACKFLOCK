import json


def parse_body(request):
    if not request.body:
        return {}

    try:
        return json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return None


def form_errors_payload(form):
    return {
        field: [error['message'] for error in errors]
        for field, errors in form.errors.get_json_data().items()
    }
