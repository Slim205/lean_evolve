import os
import logging
from openai import OpenAI
import time

log = logging.getLogger(__name__)


class GlobalCallCounter:
    def __init__(self):
        self.reset()

    def increment(self):
        self.calls += 1

    def summary(self):
        return {"calls": self.calls}

    def reset(self, initial=0):
        self.calls = initial


GLOBAL_LLM_CALLS = GlobalCallCounter()

# import math

# def perplexity_from_chat_completion(response) -> float:
#     # tokens info lives here (per cookbook): response.choices[0].logprobs.content
#     items = response.choices[0].logprobs.content  # list of token objects
#     logps = [it.logprob for it in items if getattr(it, "logprob", None) is not None]

#     if not logps:
#         raise ValueError("No logprobs found. Ensure you set logprobs=True and the model supports it.")

#     avg_neg_logp = -sum(logps) / len(logps)  # logprobs are natural log
#     return math.exp(avg_neg_logp)

def completion(prompt: str, system_prompt: str = "", model: str = "gpt-5-mini", is_response : bool =False) -> str:
    # model = "gpt-5.2"
    # is_response= True
    if is_response : 
        return completion_response(prompt,system_prompt)
    if model != "gpt-5-mini":
        log.info(f"Using {model} for completion")
    try:
        api_key = os.environ.get("OPEN_AI_KEY")
        client = OpenAI(api_key=api_key)
        start = time.perf_counter()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "text"},
            # logprobs=True,
            # top_logprobs=0,       
        )        

        elapsed = time.perf_counter() - start
        log.info(f"[LLM] completion call took {elapsed:.3f} seconds")
        # ppl = perplexity_from_chat_completion(response)

        # log.info("Perplexity:", ppl)
        GLOBAL_LLM_CALLS.increment()

        return response.choices[0].message.content

    except Exception as e:
        log.error(f"Error calling LLM: {e}")
        return ""

def completion_response(prompt: str, system_prompt: str = "", model: str = "gpt-5-mini") -> str:
    model = "gpt-5.2"
    if model != "gpt-5-mini":
        log.info(f"Using {model} for completion")
    try:
        api_key = os.environ.get("OPEN_AI_KEY")
        client = OpenAI(api_key=api_key)
        start = time.perf_counter()

        response = client.responses.create(
            model=model,
            reasoning={"effort": "medium"},
            instructions=system_prompt,
            input=[               
                 {"role": "user", "content": prompt},
            ],
            text={"format": {"type": "text"}},

            max_output_tokens=25000,
        )
        print(response.usage)
        # print(response.output_text)
        # assert False
        if response.status == "incomplete" and response.incomplete_details.reason == "max_output_tokens":
            print("Ran out of tokens")
            if response.output_text:
                print("Partial output:", response.output_text)
            else: 
                print("Ran out of tokens during reasoning")

        elapsed = time.perf_counter() - start
        log.info(f"[LLM] completion call took {elapsed:.3f} seconds")

        GLOBAL_LLM_CALLS.increment()

        return response.output_text

    except Exception as e:
        log.error(f"Error calling LLM: {e}")
        return ""


def completion_msg(msg, model: str = "gpt-5-mini") -> str:
    # model = "gpt-5.2"
    if model != "gpt-5-mini":
        log.info(f"Using {model} for completion")
    try:
        api_key = os.environ.get("OPEN_AI_KEY")
        client = OpenAI(api_key=api_key)
        start = time.perf_counter()

        response = client.chat.completions.create(
            model=model,
            messages=msg,
            response_format={"type": "text"},
            # logprobs=True,
            # top_logprobs=0,       
        )        

        elapsed = time.perf_counter() - start
        log.info(f"[LLM] completion call took {elapsed:.3f} seconds")
        # ppl = perplexity_from_chat_completion(response)

        # log.info("Perplexity:", ppl)
        GLOBAL_LLM_CALLS.increment()

        return response.choices[0].message.content

    except Exception as e:
        log.error(f"Error calling LLM: {e}")
        return ""
