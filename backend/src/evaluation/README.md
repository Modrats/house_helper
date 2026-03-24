# Evaluation

This module contains the evaluation framework for the House Helper pipeline — ground truth datasets, evaluators, and metrics for each LLM-powered stage.

---

## Overview

The pipeline processes house listings through several LLM-driven stages:

```
RAW → FILTERED → CLASSIFIED → EVALUATED → IMAGINEERED → COMPLETE
```

Each stage that uses an LLM has its own ground truth dataset (input/expected output pairs modelled as Pydantic schemas), one or more evaluators, and defined success criteria that must be met before the system is considered production-ready.

---

## Evaluation Dimensions

Every pipeline component is measured across four dimensions:

| Dimension | Evaluator type | What it measures |
|-----------|----------------|-----------------|
| **Time** | Latency evaluator | Wall-clock seconds per item |
| **Cost** | Token evaluator | Token usage → estimated USD cost |
| **Quantitative** | Precision / Recall / Accuracy | Correctness against ground truth labels |
| **Qualitative** | LLM-as-judge | Semantic correctness, coherence, or visual quality |

---

## Pipeline Components

### 1. Text Filter

**Stage:** `RAW → FILTERED`

Filters listing text as pass/fail for each criterion priority tier (p1, p2, excluded). The current implementation is keyword-based (exact case-insensitive match). Metrics are tracked from day one so that if an LLM-powered variant is added later (e.g. for synonym expansion, where "garage" also catches "car port" or "private parking"), we can compare directly against the baseline.

**Ground truth schema:**

```python
class TextFilterSample(BaseModel):
    slug: str                           # house identifier
    listing_text: str                   # raw listing text
    expected: FilterResult              # p1/p2/excluded per criterion keyword
```

**Metrics:**

| Metric | Definition | Success criterion |
|--------|-----------|-------------------|
| Accuracy | Percentage of criterion keys with correct True/False verdict | ≥ 99% |
| False-negative rate | Houses incorrectly excluded (p1/excluded mismatch) | ≤ 1% |
| Latency | Seconds to filter a batch of 100 houses | ≤ 2 s |

> Cost and LLM-as-judge metrics are not applicable to the keyword implementation. They will be added when an LLM variant is introduced.

---

### 2. Photo Classifier (Room Classification)

**Stage:** `FILTERED → CLASSIFIED`

Given a photo, the LLM returns the `RoomType` and a confidence score. Ground truth labels a representative set of photos with their correct room type.

**Ground truth schema:**

```python
class PhotoClassificationSample(BaseModel):
    photo_path: str                     # path to the image
    expected_room_type: RoomType        # e.g. RoomType.KITCHEN
    expected_confidence_min: float      # minimum acceptable confidence
```

**Metrics:**

| Metric | Definition | Success criterion |
|--------|-----------|-------------------|
| Accuracy | % of photos assigned the correct `RoomType` | ≥ 70% |
| Precision (per class) | TP / (TP + FP) for each `RoomType` | ≥ 0.65 for common rooms |
| Recall (per class) | TP / (TP + FN) for each `RoomType` | ≥ 0.65 for common rooms |
| Confidence calibration | Mean predicted confidence on correct predictions | ≥ 0.70 |
| LLM-as-judge score | Judge rates classification plausibility 1–5 | Mean ≥ 3.5 |
| Latency | Seconds per photo (P95) | ≤ 10 s |
| Cost | Estimated USD per photo classified | ≤ $0.05 |

**Notes:** Common rooms are `LIVING_ROOM`, `BEDROOM`, `KITCHEN`, `BATHROOM`, `GARDEN`. Rare types (`LAUNDRY`, `BASEMENT`, `ATTIC`) are tracked separately and not gated by the above thresholds.

---

### 3. Criteria Evaluator

**Stage:** `CLASSIFIED → EVALUATED`

Given a classified house (photos + listing text) and the user's criteria, the LLM evaluates both photo-based and text-based criteria in a single call, returning a pass/fail verdict per criterion key. For example: "does this kitchen have a dishwasher?" is checked visually from the photo; "does this house have a south-facing garden?" may be checked from the listing text. Both are resolved together.

**Ground truth schema:**

```python
class CriteriaEvaluationSample(BaseModel):
    photos: list[str]                   # paths to house photos
    listing_text: str                   # full listing description
    photo_criteria: dict[str, str]      # {key: description} — checked from photos
    text_criteria: dict[str, str]       # {key: description} — checked from listing text
    expected: dict[str, bool]           # {key: True/False} for every criteria key
```

**Metrics:**

| Metric | Definition | Success criterion |
|--------|-----------|-------------------|
| Accuracy | % of criteria keys with correct verdict | ≥ 70% |
| False-negative rate | Requirements incorrectly marked as not met | ≤ 15% |
| LLM-as-judge score | Judge rates verdicts for plausibility given the evidence 1–5 | Mean ≥ 3.5 |
| Latency | Seconds per house (P95) | ≤ 15 s |
| Cost | Estimated USD per house evaluated | ≤ $0.10 |

---

### 4. Imagineering (AI Image Generation)

**Stage:** `EVALUATED → IMAGINEERED`

Given a source photo and a style prompt, the model generates a reimagined version of the room and writes it to `imagineered_path`. There is no single "correct" image, so quantitative metrics measure prompt adherence and quality.

**Ground truth schema:**

```python
class ImagineeredSample(BaseModel):
    photo_path: str
    room_type: RoomType
    style_prompt: str                   # prompt used for generation
    reference_features: list[str]       # features the output should exhibit
```

**Metrics:**

| Metric | Definition | Success criterion |
|--------|-----------|-------------------|
| LLM-as-judge score | Judge rates output image for style adherence and plausibility 1–5 | Mean ≥ 3.5 |
| Feature retention | % of original room's structural features visible in the output | ≥ 70% |
| Prompt alignment | Judge rates how well the output matches the style prompt 1–5 | Mean ≥ 3.5 |
| Latency | Wall-clock seconds per image (P95) | ≤ 60 s |
| Cost | Estimated USD per generated image | ≤ $0.50 |

---

## End-to-End (Pipeline) Metrics

In addition to per-component evaluation, the pipeline is measured end-to-end on a set of full house fixtures.

| Metric | Definition | Success criterion |
|--------|-----------|-------------------|
| Total wall-clock time | Time from `RAW` input to `COMPLETE` status per house | ≤ 5 min |
| Total cost per house | Cumulative token + generation cost per house | ≤ $1.00 |
| Pass-through rate | % of houses that reach `COMPLETE` without error | ≥ 95% |
| Overall pipeline accuracy | Weighted average across per-stage accuracy scores | ≥ 70% |

---

## Ground Truth Data

Ground truth samples are stored in `tests/fixtures/` alongside the tests that consume them. Each fixture file is a JSON array of samples matching the Pydantic schema for that stage.

| Stage | Fixture file |
|-------|-------------|
| Text Filter | `fixtures/text_filter_samples.json` |
| Photo Classifier | `fixtures/photo_classification_samples.json` |
| Criteria Evaluator | `fixtures/criteria_evaluation_samples.json` |
| Imagineering | `fixtures/imagineered_samples.json` |

Fixture schemas are defined as Pydantic models in this module so they can be imported by both the evaluation runners and the test suite.

---

## Running Evaluations

### Local

```bash
# Run all evaluators
make eval

# Run a single component
make eval COMPONENT=photo_classifier
```

### CI/CD

Evaluations run automatically on every PR via the CI pipeline. A PR that regresses any success criterion below threshold will fail.

---

## Leaderboard & Experimentation

Metrics are published to Azure ML (AML) experiments after each run. This allows:

- **Model swaps** — compare GPT-4o vs GPT-4-turbo on the same ground truth.
- **Prompt variants** — A/B test prompt changes without touching application code.
- **Dashboard** — live view of all per-component metrics across experiment runs.

Each experiment run records: `model_name`, `prompt_version`, `run_date`, and all metrics in the table above.

### Publishing API

Publishing is abstracted behind `IMetricsPublisher` (`backend/src/evaluation/publisher_interface.py`) so evaluation runners are decoupled from AML. The interface exposes two methods:

- `publish(report, experiment_name, run_tags)` — publishes one `EvaluationReport` as an AML run, returns the run ID.
- `publish_batch(reports, experiment_name, run_tags)` — publishes multiple reports, returns a list of run IDs.

The concrete implementation is `AMLPublisher` (`backend/src/evaluation/aml_publisher.py`), which uses **mlflow** with the AzureML tracking backend. It is lazily imported so the module remains importable without the package installed. Tests should inject a `NullPublisher` (implementing `IMetricsPublisher`) rather than touching AML.

`run_tags` must include at minimum: `model_name`, `prompt_version`, `stage`.

### Required environment variables

| Variable | Purpose |
|----------|---------|
| `AML_TRACKING_URI` | Full mlflow tracking URI for the AzureML workspace (preferred). |
| `AML_SUBSCRIPTION_ID` | Azure subscription ID (used to build the URI if `AML_TRACKING_URI` is not set). |
| `AML_RESOURCE_GROUP` | Azure resource group containing the AML workspace. |
| `AML_WORKSPACE_NAME` | Azure ML workspace name. |
| `AML_REGION` | Azure region slug, e.g. `westeurope` (used to build the URI). |

Per team policy, **no default values are provided** — missing variables raise `EnvironmentError` at construction time.

Install the optional dependency group to use `AMLPublisher`:

```bash
pip install 'house-helper-backend[aml]'
```

---

## Follow-up Work Items

0. **Define eval pipeline** — create an `IEvaluator` interface and typed `MetricResult` Pydantic models; implement one evaluator per component following CLEAN rules. Evaluation code must not import from `services/` — only `models/` and `interfaces/`.
1. **Define ground truth** — create fixture files for all stages listed above.
2. **Local & CI/CD eval pipeline** — wire `make eval` and the CI step.
3. **AML integration** — publish metrics to AML experiments and surface to the dashboard.
