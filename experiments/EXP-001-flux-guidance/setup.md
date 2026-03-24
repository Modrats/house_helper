# EXP-001: FLUX.2-pro Guidance Parameter Experiment

**Date:** 2026-03-23  
**Author:** Kovacs (Tester/QA)  
**Status:** In Progress

---

## Hypothesis

> Higher guidance values (30-50) will better preserve room structure and spatial layout in FLUX.2-pro outputs, while lower values (5-10) will allow more creative deviation from the input.

---

## Background

The FLUX.2-pro model uses a guidance parameter to control how closely the output adheres to the input prompt/image. Finding the optimal guidance value for home staging imagineering is critical for balancing:
- **Structural fidelity** — walls, windows, and room layout remain consistent
- **Creative transformation** — furniture and decor styling can change appropriately  
- **Artifact avoidance** — minimizing distortions and visual glitches

This experiment systematically tests guidance values to establish baseline recommendations for House Helper's imagineering pipeline.

---

## Test Configuration

### Guidance Value Matrix

| Value | Category | Expected Behavior |
|-------|----------|-------------------|
| 5 | Low | High creativity, potential structural drift |
| 10 | Low-Medium | Moderate creativity, some deviation |
| 15 | Medium | Balanced (common default) |
| 20 | Medium-High | Increased adherence |
| 30 | High | Strong structural preservation |
| 50 | Very High | Maximum adherence, minimal deviation |

### Style Prompt (Constant)

```
Modern Scandinavian interior design, natural wood accents, neutral color palette 
with warm whites and soft grays, minimalist furniture, abundant natural light, 
cozy textiles, indoor plants
```

**Rationale:** Scandinavian style is versatile, works across room types, and has clear visual markers for evaluating transformation quality.

---

## Test Photos

### Source House
- **House:** `ikea_showroom`
- **Path:** `input_data/houses/ikea_showroom/`

### Selected Photos

| Room Type | Photo ID | Path | Selection Rationale |
|-----------|----------|------|---------------------|
| Kitchen | `052b2a2e` | `photos/052b2a2e-6694-41d4-8b0c-d3bf5485fd1c.jpeg` | IKEA showroom kitchen with appliances, cabinets, counters — high complexity |
| Bedroom | TBD | — | **⚠️ Needs sourcing** — no bedroom photo currently available |
| Living Room | `9563c53b` | `photos/9563c53b-4725-4e8a-92f1-3bdeb6dcbf9d.jpeg` | Contains seating and decor elements |

### ⚠️ Data Gap: Additional Test Photos Needed

The current `input_data/houses/` directory has limited samples. To complete this experiment:

1. **Bedroom photo needed:**
   - Should contain: bed, nightstands, closet/wardrobe, textiles (bedding, curtains)
   - Complexity: Medium
   
2. **Consider adding:**
   - Additional house listings for variety
   - Photos with different lighting conditions
   - Photos with challenging elements (mirrors, windows, outdoor views)

**Action item:** Source 1-2 additional test houses or request bedroom photo be added to ikea_showroom.

---

## Output Structure

```
experiments/EXP-001-flux-guidance/
├── setup.md              (this file)
├── analysis.md           (results analysis)
└── results/
    ├── kitchen/
    │   ├── guidance_05.png
    │   ├── guidance_10.png
    │   ├── guidance_15.png
    │   ├── guidance_20.png
    │   ├── guidance_30.png
    │   └── guidance_50.png
    ├── bedroom/
    │   └── (same structure, pending photo)
    └── living_room/
        └── (same structure)
```

### Naming Convention
- Format: `guidance_{value}.png`
- Example: `guidance_15.png` for guidance=15 result

---

## Evaluation Criteria

### Quantitative Metrics (per image)
- [ ] SSIM (Structural Similarity Index) vs original
- [ ] Edge preservation score (Canny edge comparison)
- [ ] Color histogram consistency

### Qualitative Assessment
- [ ] Room structure preserved (walls, windows, doors)
- [ ] Furniture placement logical
- [ ] No visual artifacts (floating objects, distorted geometry)
- [ ] Style prompt adherence

### Success Criteria
1. Identify guidance range that scores >0.7 SSIM while achieving style transformation
2. Document guidance values that cause structural degradation
3. Establish recommended default guidance value for production

---

## Execution Checklist

- [x] Create experiment folder structure
- [x] Define guidance test matrix
- [x] Define consistent style prompt
- [x] Document available test photos
- [ ] Source missing bedroom test photo
- [ ] Run experiment with kitchen photo
- [ ] Run experiment with living room photo
- [ ] Run experiment with bedroom photo
- [ ] Complete analysis.md with results
- [ ] Make recommendation for production guidance value

---

## Notes

- **Model:** FLUX.2-pro (via Replicate API)
- **Consistent seed:** Use same seed across all guidance values for fair comparison
- **Output resolution:** Match input resolution
