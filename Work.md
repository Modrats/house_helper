# Workstreams.
## Priority 0
- Add key scanning and vuln scanning to repo.
- Think about pre-commit hook.

## Priority 1
### W1 - Frontend 
Implement the frontend in react.
Can list the houses from under outputs as options in a sidebar where you can scroll through all house names.
When clicked the user is directed to that house's home page, which has the screenshot image as the header, the distance information and a summary of the P1 and P2 criteria that it passed or failed. The user can click a button to continue to the gallery, where the sidebar now shows the rooms classified, and a sparkle emoji if that house has imagineered photos.
For a house with imagineered photos the original photo should be overlayed with the imagineered version, with a slidable bar widget to swap between them.

### W2 - Backend
Implement a backend pipeline, which takes each house from the input_data and in parallel/multiprocessing applies a pipeline which runs through services.
- Define a iFilter interface which promises that a filter will take in a list of houses and a criteria and return the houses which meet the criteria.
- A text filter service, which checks the house/listing.txt for specific criteria using an LLM.
- A Room Classifier which categorizies photos into rooms and writes room_classifications into outputs to reference which rooms are mapped to which photos.
- Photo Criteria Checker which checks each room for required visual items as defined in a user prompt. eg. a dishwasher in the kitchen room.
- Distance Calculator which calculates the travel time to a user defined location
- Imagineering which uses FLUX.2-pro to generate reimagined images of the rooms from the base rooms using the prompts provided.
- FastAPI serving processed data to the Frontend. eg. House details including listing information, distance, original photos, reimagined photos, original url, screenshot.
# W4 - Experiments.

### EXP-001: FLUX.2-pro Guidance Parameter Tuning

**Goal:** Find optimal `guidance` value balancing style adherence vs structure preservation.

**Setup:**
- Select 3 diverse rooms (kitchen, bedroom, living room) from different houses
- Apply same style template to each
- Generate at guidance values: `5, 10, 15, 20, 30, 50`

**Metrics:**
1. **Structure preservation** (manual 1-5): Do walls, windows, floor layout match?
2. **Style adherence** (manual 1-5): Are requested decorations/colors present?
3. **Realism** (manual 1-5): Does it look like a real room?

**Expected tradeoff:**
```
guidance=5  → Very close to original, minimal style changes
guidance=15 → Balanced (current default)
guidance=50 → Heavy style, may distort structure
```

**Output:** Recommended default guidance value + per-room-type adjustments if needed.

## Priority 2