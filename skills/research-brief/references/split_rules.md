# Split rules

1. **Assignment by salted hash.**
   - Compute `sha256("<salt>:<item_id>")`, sort by it, and assign fixed rank ranges to dev, selection, sealed and final.
   - Record the salt and the ranges in the brief.
   - This makes splits reproducible and impossible to tune.

2. **Group before splitting.**
   - Group near-duplicates (perceptual hash or embedding distance below a threshold fixed in advance) and same-source items (same scene, sequence, lot, patient, wafer, author, capture session).
   - Assign whole groups.
   - Do this before looking at any performance number.

3. **Check pretrained overlap.**
   - List the training and validation data of every pretrained weight.
   - Remove overlapping items from every evaluation pool, or choose another pool.
   - Common case: "validation" images inside an official training split.

4. **Seal.**
   - Sealed-pilot and final sets live outside anything the executor (person or agent) can read.
   - Only the auditor opens them: once, after the selection is frozen.

5. **Time and versioning.** Record dataset versions and download dates. For temporal data, split by time, not at random.

6. **Size for power.** Choose the sealed-set size so that the minimum effect is detectable with the chosen CI. Otherwise the expected outcome is INCONCLUSIVE, and the brief should say so up front.
