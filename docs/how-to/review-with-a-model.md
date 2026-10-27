# Review outputs with a local model

Kind: how-to.

This optional step asks a second model to assess saved text against the partial reference.
It is not needed to run Nemotron Parse or calculate deterministic scores.
The judge sees text only, not the receipt image.

[Judgevet](https://github.com/Alberto-Codes/judgevet) defines the typed rubric and result.
[Typevet](https://github.com/Alberto-Codes/typevet) connects that rubric to a local Gemma model.
See the [provider bridge guide](https://alberto-codes.github.io/typevet/how-to/use-typevet-as-a-judgevet-provider/)
and [Judgevet documentation](https://alberto-codes.github.io/judgevet/).

## Prepare a separate judge server

1. Stop the experiment's parser container to release its GPU allocation.

   ```sh
   uv run inference-axi stop
   ```

2. Follow Typevet's [Gemma and llama.cpp setup guide](https://alberto-codes.github.io/typevet/how-to/run-gemma4-llamacpp/).
3. Start your supported Gemma model with the required template and judgment endpoints.
4. Read the model ID exposed by your server.

   ```sh
   curl --fail --max-time 10 http://127.0.0.1:8090/v1/models
   ```

Port 8090 is an example. Use your server's actual address.
Gemma weights and their memory requirements are separate from the parser setup.
Compatibility depends on the model template and server capabilities described by Typevet.
A generic chat endpoint alone does not establish judgment compatibility.

5. Configure the selected endpoint and model ID explicitly.

   ```sh
   export TYPEVET_BACKEND=llama_cpp
   export TYPEVET_LLAMA__BASE_URL=http://127.0.0.1:8090
   export TYPEVET_LLAMA__MULTIMODAL_MODEL='YOUR_SERVED_GEMMA_MODEL_ID'
   export TYPEVET_LLAMA__AUTOLOAD=false
   ```

The review script supports the llama.cpp bridge for this experiment.
It requires your model ID and defaults to disabled autoload.
Keep `TYPEVET_LLAMA__AUTOLOAD=false` to prevent automatic model loading.
Load your chosen model before running the review.

## Review the selected scores

Run from the inference-lab checkout after creating `scores.json`.

```sh
uv run --script scripts/review_receipts.py \
  --input runs/receipts-01/scores.json \
  --rubric evidence/cord-test-24/judgevet-review.json \
  --output runs/receipts-01/judgments.json
```

uv installs the script's pinned Judgevet 0.23.0 and Typevet 0.11.0 dependencies in isolation.
The dependencies come from the package registry.
The historical file supplies only the instruction and ordered criteria.
The script selects the three lowest-overlap cases from your supplied scores.
It records the resolved model, configured backend and each answer.
The file has `"status": "complete"` only after all three reviews finish.
If the review stops early, the file keeps `"status": "incomplete"`.
Delete that file or choose a new `--output` path before you try again.

A rubric score is an expected level index, not an accuracy percentage.
The recorded judge remained uncertain about separator changes despite an explicit matching rule.
Keep these suggestions separate from deterministic numeric comparisons.
