# Phase 3 — Structured AI Assistance: Setup and Review Guide

## What this phase does

Phase 3 adds one optional cloud-AI adapter behind a strict interface. The adapter can help with ambiguous email classification and incomplete or unclear document extraction. It does not decide whether the SI and BL mismatch. The deterministic normalizers and comparison engine remain the final decision authority.

The provider response must be JSON that matches a strict schema. Malformed JSON, unsupported categories, missing required properties, invalid confidence values, or missing evidence are rejected. When the provider is unavailable or its response is rejected, the Phase 2 deterministic path continues and the output records that fallback was active.

The selected provider is Google Gemini through its OpenAI-compatible endpoint. The default model is `gemini-3.8-flash`, which Google currently lists with Free Tier input and output pricing [5]. Free-tier availability and rate limits are project- and model-specific [6][9], so verify the active tier in Google AI Studio before making requests. The project uses strict JSON output plus application-side validation.

## What changed

| File | Purpose |
|---|---|
| `src/cargoclarity/ai_schemas.py` | Strict classification and extraction schemas |
| `src/cargoclarity/ai_adapter.py` | One provider adapter, validation, timeout, metadata, and safe errors |
| `src/cargoclarity/pipeline.py` | Optional AI classification/extraction with deterministic fallback |
| `src/cargoclarity/models.py` | Optional classification explanation field |
| `src/cargoclarity/cli.py` | `--use-ai` and `ai-check` commands |
| `tests/test_phase3_ai.py` | Mocked provider, schema rejection, and fallback tests |
| `.env.example` | Phase 3 environment variable names and defaults |

## Step 1 — Open the project

Open Terminal and run:

```bash
cd "/Users/abdulhakimshaon/Desktop/Averis/CargoClarity/CargoClarity"
```

Confirm the location:

```bash
pwd
```

The path should end with:

```text
/Averis/CargoClarity/CargoClarity
```

## Step 2 — Activate the existing environment

Run:

```bash
source .venv/bin/activate
```

If the environment does not exist, create it and install the Phase 3 dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,ai]'
```

If the environment already exists, refresh the package after pulling or receiving the Phase 3 files:

```bash
python -m pip install -e '.[test,ai]'
```

The `ai` extra installs the OpenAI-compatible Python client. The base package also installs `python-dotenv`, so the local `.env` file is loaded automatically. Mocked schema tests do not need a provider key.

## Step 3 — Run every automated test

Run:

```bash
pytest
```

Expected result:

```text
23 passed
```

The Phase 3 tests verify that the adapter sends strict JSON Schema requests, validates valid responses, rejects non-null values without evidence, rejects unsupported categories, records provider/model/prompt metadata, and preserves a deterministic result when an AI response is malformed.

If this command fails, stop and provide the complete failure output. Do not enable a live provider until the tests pass.

## Step 4 — Run the original Phase 2 regression fixtures

Run:

```bash
cargoclarity fixtures
```

Expected result:

```text
7/7 fixtures passed
```

Phase 3 must not change the Phase 2 comparison outcomes. The AI adapter is an assistant, not a replacement for the deterministic core.

## Step 5 — Verify fallback with no API key

This command explicitly bypasses the local `.env` file and removes common API-key variables for this one invocation:

```bash
CARGOCLARITY_DISABLE_DOTENV=1 env -u GEMINI_API_KEY -u AI_API_KEY -u OPENAI_API_KEY -u AI_API_BASE -u OPENAI_API_BASE \
  cargoclarity ai-check
```

Expected output contains:

```json
{
  "enabled": false,
  "message": "AI is not configured; deterministic fallback is active."
}
```

Now verify that a normal email remains processable when the AI flag is requested but no provider is configured:

```bash
CARGOCLARITY_DISABLE_DOTENV=1 env -u GEMINI_API_KEY -u AI_API_KEY -u OPENAI_API_KEY -u AI_API_BASE -u OPENAI_API_BASE \
  cargoclarity email email_001 --use-ai \
  | jq '{category, comparison: .comparison.status, ai_processing}'
```

The comparison should still be `OK`. `ai_processing.fallback_active` should be `true` because the requested provider is unavailable.

## Step 6 — Create a Gemini Free Tier key

This is the only step that requires an account outside the repository. Open the official [Google AI Studio API-key page](https://aistudio.google.com/apikey), sign in, and create an API key in a project that is shown as **Free Tier**. Google documents that new accounts begin on the Free Tier for eligible models, but the available models and request limits vary by project. Do not click **Set up billing**, add a payment method, or upgrade the project if you want this test to remain no-cost. If AI Studio only offers a paid project or asks you to enable billing, stop and do not continue.

After copying the key, the project’s local `.env` file is ready. Open it in the macOS text editor:

```bash
open -e .env
```

Replace only the empty value after `GEMINI_API_KEY=` with your key; do not include spaces around the equals sign. The active settings should look like this:

```bash
AI_PROVIDER=gemini
AI_MODEL=gemini-3.8-flash
AI_API_BASE=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_API_KEY=PASTE_YOUR_GEMINI_KEY_HERE
```

Save and close the file. CargoClarity now loads `.env` automatically when you run a command. You should not put the real key into `.env.example`. The adapter also accepts `AI_API_KEY`, but `GEMINI_API_KEY` is clearer and takes priority for Gemini.

Google’s official documentation says Gemini supports this OpenAI-compatible endpoint and structured JSON output [7][8]. The free tier is limited: requests are subject to model-specific RPM, TPM, and RPD limits, and the free-tier terms say prompts and responses may be used to improve Google products [5]. Use only the provided synthetic participant data for this test.

When you finish testing, remove the key from `.env` or replace the line with `GEMINI_API_KEY=`. You can also clear any variables from the current shell:

```bash
unset GEMINI_API_KEY AI_API_BASE AI_MODEL AI_PROVIDER
```

The key is not required to review the implementation because the automated tests use a mock transport. It is required only for the one live Gemini check in the next step.

## Step 7 — Install the optional live-provider client

Only if you are going to make a live AI call, run:

```bash
python -m pip install -e '.[test,ai]'
```

Do not run a live call against a provider until you have configured the environment variables in Step 6.

## Step 8 — Make one bounded live Gemini check

After setting the variables, run:

```bash
cargoclarity ai-check
```

This makes one small classification request. It does not process the 520-email dataset and does not run a batch job.

A successful response should contain:

```json
{
  "enabled": true,
  "result": {
    "category": "...",
    "confidence": 0.0,
    "signals": [],
    "explanation": "..."
  },
  "calls": [
    {
      "operation": "classification",
      "provider": "gemini",
      "model": "gemini-3.8-flash",
      "validation_status": "VALIDATED"
    }
  ]
}
```

The exact category is not a scoring result. The important checks are that the call succeeds, the response is schema-valid, the explanation is present, and `validation_status` is `VALIDATED`.

If the provider rejects the request, times out, or returns malformed JSON, the command prints an error and call metadata. That is a safe failure; it must not be treated as a comparison decision.

If the error says `HTTP 402` and `prepayment credits are depleted`, the API key is valid but its Google project is on a paid/prepaid tier with no remaining credits. Do not add money if you want a no-cost setup. Create or select a separate project shown as **Free Tier** in AI Studio, create a new key for that project, and replace only `GEMINI_API_KEY` in the local `.env`. Google documents that API keys inherit their project’s billing status and that unlinking billing can return a project to Free Tier [6].

## Step 9 — Run the normal pipeline with AI enabled

Run this low-confidence sample:

```bash
cargoclarity email email_016 --use-ai
```

`email_016` has a deterministic classification confidence below the Phase 3 AI threshold, so it is suitable for seeing a Gemini classification call. The pipeline uses deterministic classification first and calls Gemini only when confidence is low. A strong deterministic example may show no AI call even when `--use-ai` is present. This is intentional and avoids unnecessary provider cost.

For document extraction, AI is only used when the deterministic document role is unknown or a required field is still missing. Existing deterministic values and evidence are not overwritten by AI output.

Inspect the following output properties:

- `classification.decided_by` is either `RULE` or `AI`.
- `classification.explanation` is populated when AI supplies the classification.
- `ai_processing.calls` lists operation, provider, model, prompt version, latency, and validation status.
- `ai_processing.fallback_active` is `true` if the provider was unavailable or a call failed.
- `comparison.status` still comes from the deterministic comparison engine.

## Step 10 — Confirm malformed responses cannot create false mismatches

The mocked test covers this automatically. To see the relevant test alone, run:

```bash
pytest tests/test_phase3_ai.py -q
```

The test named `test_pipeline_keeps_deterministic_result_when_ai_response_is_malformed` confirms that an invalid AI classification leaves the rule-based category in place and marks fallback as active.

The extraction contract also requires an evidence excerpt for every non-null AI value. A value without evidence is rejected before it can reach normalization or comparison.

## Step 11 — Run the full participant smoke test

Run:

```bash
python tools/run_phase2_smoke.py
```

This remains a deterministic smoke test and does not use AI. The final line must be:

```text
failures=[]
```

Do not run AI over all 520 records in this phase. The guide intentionally limits live usage to one bounded health check because Phase 3 is about the adapter contract and fallback behavior, not batch tuning.

## Step 12 — Check repository safety

Run:

```bash
find . -type f \
  \( -iname '*ground*truth*' -o -iname '*answer*key*' -o -iname '*score_cli*' \) \
  -not -path './.git/*'
```

The command should print nothing.

Check for likely secret patterns:

```bash
grep -RIlE \
  '(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY)' \
  --exclude-dir=.git --exclude-dir=.venv .
```

It should print nothing. A populated `.env` must not exist in the repository.

## Step 13 — Review the Phase 3 design

Confirm these design rules in the source:

1. There is one provider adapter in `src/cargoclarity/ai_adapter.py`.
2. The provider receives bounded subject, body, attachment names, or document text only.
3. The prompts treat document text as untrusted data.
4. The provider must return strict JSON Schema output.
5. Every non-null extracted value must have evidence.
6. AI extraction is normalized by the same deterministic functions as rule extraction.
7. The comparison engine remains deterministic.
8. A provider failure returns to the deterministic result.
9. Provider, model, prompt version, latency, and validation status are recorded.
10. No API key is present in source code, fixtures, logs, or output.

## Step 14 — Approve Phase 3

Approve this phase only when:

- `pytest` reports 23 passing tests.
- `cargoclarity fixtures` reports 7/7 passing fixtures.
- The no-key fallback check succeeds.
- `cargoclarity ai-check` behaves as expected for your configured or unconfigured environment.
- The full deterministic smoke test ends with `failures=[]`.
- The repository safety searches return no forbidden files or secrets.
- You understand that Phase 3 does not yet add a web UI, API, database, review actions, or deployment.

Then reply:

```text
Phase 3 approved. Move to Phase 4.
```

## What comes next

Phase 4 will build the smallest backend workflow around the existing core: list emails, retrieve one email, process an email, inspect job status, return a comparison, preview evidence safely, submit a review, retry processing, and export evaluation JSON. It will not duplicate the deterministic or AI business logic in route handlers.

## References

[1]: ../.env.example "CargoClarity environment variable template"
[2]: ./PHASE2_GUIDE.md "CargoClarity Phase 2 review and operation guide"
[3]: ./CargoClarity — API Specification.md "CargoClarity API Specification"
[4]: ./CargoClarity — Security & Privacy.md "CargoClarity Security and Privacy"
[5]: https://ai.google.dev/gemini-api/docs/pricing "Google Gemini API pricing and Free Tier"
[6]: https://ai.google.dev/gemini-api/docs/billing "Google Gemini API billing and usage tiers"
[7]: https://ai.google.dev/gemini-api/docs/openai "Google Gemini OpenAI compatibility"
[8]: https://ai.google.dev/gemini-api/docs/structured-output "Google Gemini structured output"
[9]: https://ai.google.dev/gemini-api/docs/rate-limits "Google Gemini API rate limits"
