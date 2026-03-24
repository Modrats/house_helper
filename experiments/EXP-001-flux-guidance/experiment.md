# Experiment: FLUX.2-pro Guidance Parameter Sensitivity

**Date:** 2026-03-24
**Author:** Terri Modrakowski
**Status:** Complete

---

## Hypothesis

> Higher guidance values (30–50) will better preserve room structure and spatial layout in FLUX.2-pro outputs, while lower values (5–10) will allow more creative deviation from the input.

---

## Background

The FLUX.2-pro model accepts a `guidance` parameter (1–100) controlling prompt adherence. Finding the right value for home staging imagineering is critical — too low and rooms drift structurally, too high and creative transformation is suppressed. This experiment systematically tests six values to establish a baseline recommendation for House Helper's imagineering pipeline.

See also: `old/house_helper/src/house_helper/agents/imagineering_agent.py` for the architectural preservation prompt that was used as the system prompt prefix.

---

## Method

### Setup
- **Model:** FLUX.2-pro via Azure AI Foundry (`funda-llm-foundry.services.ai.azure.com`)
- **Guidance values tested:** 5, 10, 15, 20, 30, 50
- **Seed:** 42 (fixed across all runs for fair comparison)
- **Steps:** 50
- **Resolution:** 1024×1024
- **Input data:**
  - Kitchen: `input_data/houses/ikea_showroom/photos/052b2a2e-6694-41d4-8b0c-d3bf5485fd1c.jpeg`
  - Living room: `input_data/houses/ikea_showroom/photos/9563c53b-4725-4e8a-92f1-3bdeb6dcbf9d.jpeg`

### Prompt structure

A two-part prompt was used for every call:

1. **System prefix** (from `imagineering_agent.py`) — instructs FLUX to pixel-lock all permanent architectural elements (walls, windows, floors, ceiling, fixed lights) and only replace movable furniture via inpainting.
2. **Room-specific decorating instructions:**
   - Kitchen: pastel sweet heaven / flavor laboratory theme
   - Living room: gamer's paradise with board games and a cat tree

### Steps
1. Generated all 6 guidance values × 2 rooms = 12 images via `run.py`
2. Viewed outputs side-by-side in `evaluate.html` (local HTTP server)
3. Compared qualitatively for structural fidelity and style adherence

### Success Criteria
- [ ] Identify guidance range that scores >0.7 SSIM while achieving style transformation
- [ ] Document guidance values that cause structural degradation
- [x] Establish recommended default guidance value for production

---

## Results

| Guidance | Kitchen | Living Room | Observations |
|----------|---------|-------------|--------------|
| 5 | Generated | Generated | — |
| 10 | Generated | Generated | — |
| 15 | Generated | Generated | — |
| 20 | Generated | Generated | — |
| 30 | Generated | Generated | — |
| 50 | Generated | Generated | — |

### Artifacts
- `results/kitchen/guidance_05.png` through `guidance_50.png`
- `results/living_room/guidance_05.png` through `guidance_50.png`
- `evaluate.html` — browser-based side-by-side viewer with star rating

### Observations

- **No visible differences between guidance values.** All 12 outputs looked effectively identical regardless of whether guidance was 5 or 50.
- The architectural preservation system prompt may be dominating — the strong pixel-lock instruction likely overrides the guidance parameter's ability to produce structural variation.
- Alternatively, FLUX.2-pro on the Azure AI Foundry endpoint may not honour the `guidance` field the same way the Replicate API does. The field is accepted without error but may be ignored or treated as a no-op at this endpoint.
- Bedroom room type could not be tested — no bedroom source photo available in `input_data/houses/ikea_showroom/`.

---

## Conclusion

**Hypothesis supported?** No — no measurable variation was observed across the guidance range tested.

**Key takeaways:**
1. The `guidance` parameter had no observable effect on FLUX.2-pro output quality or structural fidelity via the Azure AI Foundry endpoint.
2. The likely cause is either the architectural preservation system prompt suppressing variation, or the endpoint not implementing the guidance parameter.
3. A follow-up experiment should test with a minimal prompt (no preservation prefix) to isolate whether the prompt or the endpoint is responsible.

**Next steps:**
- [ ] EXP-002: Repeat with a minimal prompt (no architectural preservation prefix) to determine if prompt length/complexity is masking guidance effects
- [ ] EXP-002 alt: Test against the Replicate API directly to check if the Azure endpoint ignores the guidance field
- [ ] Source a bedroom photo for ikea_showroom to complete the room coverage
- [ ] If guidance is confirmed non-functional: remove it from the production pipeline config and document as a no-op for this endpoint

---

## Appendix

<details>
<summary>Run command</summary>

```bash
cd experiments/EXP-001-flux-guidance
uv run python run.py
```

</details>

<details>
<summary>Config used</summary>

See `config.json` in this directory. Guidance values `[5, 10, 15, 20, 30, 50]`, seed `42`, steps `50`.

</details>
