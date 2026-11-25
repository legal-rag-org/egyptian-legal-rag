from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


def setup_tracing(
    service_name: str = "egyptian-legal-rag",
    otlp_endpoint: str = "http://jaeger:4318/v1/traces",
):

    resource = Resource.create({
        "service.name": service_name
    })

    tracer_provider = TracerProvider(
        resource=resource
    )

    exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint
    )

    span_processor = BatchSpanProcessor(
        exporter
    )

    tracer_provider.add_span_processor(
        span_processor
    )

    trace.set_tracer_provider(
        tracer_provider
    )

    return trace.get_tracer(__name__)
