from flask import Flask, jsonify, request
from opentelemetry import context
from opentelemetry.propagate import extract, set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.trace import SpanKind
from a_common import configure_meter, configure_tracer, set_span_attributes_from_flask
import time

tracer = configure_tracer("legacy-inventory", "0.9.1")
meter = configure_meter("legacy-inventory", "0.9.1")
app = Flask(__name__)
set_global_textmap(B3MultiFormat())

total_duration_histo = meter.create_histogram(
    name="duration",
    description="request duration",
    unit="ms",
)

@app.before_request
def before_request_func():
    token = context.attach(extract(request.headers))
    #request.environ["context_token"] = token
    request.environ["start_time"] = time.time_ns()

@app.after_request
def after_request_func(response):
    duration = (time.time_ns() - request.environ["start_time"])/1e6
    total_duration_histo.record(duration)
    return response

@app.teardown_request
def teardown_request_func(err):
    token = request.environ.get("context_token", None)
    if token:
        context.detach(token)

@app.route("/inventory")
@tracer.start_as_current_span("/inventory", kind=SpanKind.SERVER)
def inventory():
    set_span_attributes_from_flask()
    products = [
        {"name": "oranges", "quantity": "10"},
        {"name": "apples", "quantity": "20"},
    ]
    return jsonify(products)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
