import os
import json
from openai import OpenAIError
import time
import random
from threading import Thread
from opentelemetry import trace
from opentelemetry.trace import set_span_in_context
from azure.ai.evaluation import RelevanceEvaluator, GroundednessEvaluator, FluencyEvaluator, CoherenceEvaluator, ContentSafetyEvaluator


class ArticleEvaluator:
    def __init__(self, model_config):
        self.evaluators = [
            RelevanceEvaluator(model_config),
            FluencyEvaluator(model_config),
            CoherenceEvaluator(model_config),
            GroundednessEvaluator(model_config),
            ContentSafetyEvaluator(model_config)
        ]

    def __call__(self, *, query: str, context: str, response: str, **kwargs):
        output = {}
        for evaluator in self.evaluators:
            result = evaluator(
                query=query,
                context=context,
                response=response,
            )
            output.update(result)
        return output

def evaluate_article(data, trace_context):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("run_evaluators", context=trace_context) as span:
        span.set_attribute("inputs", json.dumps(data))
        configuration = {
        "subscription_id": os.environ["AZURE_SUBSCRIPTION_ID"],   
        "resource_group_name": os.environ["AZURE_RESOURCE_GROUP"],
        "project_name": os.environ["AZURE_PROJECT_NAME"],
    }
        evaluator = ArticleEvaluator(configuration)
        results = evaluator(query=data['query'], context=data['context'], response=data['response'])
        resultsJson = json.dumps(results)
        span.set_attribute("output", resultsJson)

        print("results: ", resultsJson)

def evaluate_article_in_background(research_context, product_context, assignment_context, research, products, article):
    eval_data = {
        "query": json.dumps({
            "research_context": research_context,
            "product_context": product_context,
            "assignment_context": assignment_context
        }),
        "context": json.dumps({
            "research": research,
            "products": products,
        }),
        "response": json.dumps(article)
    }

    # propagate trace context to the new thread
    span = trace.get_current_span()
    trace_context = set_span_in_context(span)
    # thread = Thread(target=evaluate_article, args=(eval_data, trace_context,))
    evaluate_article(eval_data, trace_context)
    # thread.start()