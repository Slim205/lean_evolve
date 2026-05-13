import os
from client.client import Lean4Client, batch_verify_proof

from lean_evolve.utils import get_verification_results


class LeanVerifier:

    def __init__(self, verif_batch=15, timeout=60):
        self.verif_batch = verif_batch
        self.timeout = timeout

    def compile(self, samples):
        client = Lean4Client(
            base_url=os.environ.get("Evaluation_url"),
            disable_cache=False,
        )

        CHUNK_SIZE = 1000
        compilation_results = []

        # Split samples into chunks of 1000
        for i in range(0, len(samples), CHUNK_SIZE):
            chunk = samples[i : i + CHUNK_SIZE]

            result = batch_verify_proof(
                samples=chunk,
                client=client,
                timeout=self.timeout,
                num_proc=self.verif_batch,
                batch_size=1,
            )

            for res in result:
                compilation_results.append(get_verification_results(res))

        return compilation_results
