---
name: adobe-firefly-connector
description: Activate when the user wants to generate marketing imagery, social creative, ad variants, or product visuals using Adobe Firefly (via Firefly Services API, Photoshop generative fill, Express, or the standalone web app). Produces Firefly-appropriate prompts, structured variation matrices for A/B testing, brand-locked generation workflows using Firefly Custom Models, and integration patterns with Creative Cloud. Refuses to recommend Firefly when the actual need is a different tool (Midjourney for stylized art, DALL-E inside ChatGPT for one-offs, Stable Diffusion for self-hosted control). Refuses to produce prompts designed to mimic copyrighted characters, real public figures, or competitor brand IP — Firefly's commercial-safety positioning is a feature, and skill respects that boundary rather than working around it.
---

# Adobe Firefly Connector

Firefly's defining property is commercial safety: Adobe trains on Adobe Stock, openly licensed content, and public domain — so output carries an indemnification posture that Midjourney/SD/DALL-E don't match. The skill treats that as the reason to choose Firefly, not a constraint to fight.

## Core principle

Choose Firefly when the deliverable will go on a paid ad, a brand asset, a client campaign, or anywhere legal exposure matters. Choose another model when the deliverable is moodboard, internal exploration, or stylized art Firefly's training set can't reach. The model selection is the most important call; everything downstream is prompt craft.

## When to use

| Situation | Activate? |
|---|---|
| Generating social ad creative for a brand campaign | Yes |
| Background variations for product photography | Yes |
| Generative fill / expand on existing brand photography | Yes |
| Brand-locked imagery via Firefly Custom Models | Yes |
| Creating a Firefly Services API integration in CI/asset pipeline | Yes |
| Ideation moodboards where commercial safety doesn't matter | Reconsider — Midjourney usually better aesthetic |
| Highly stylized illustration (anime, comic, painterly) | Reconsider — SDXL / Midjourney reach further |
| Imagery of real public figures, athletes, celebrities | Refuse — Firefly blocks; respect the block |
| Imagery imitating a specific living artist's style | Refuse — Adobe explicitly disallows |
| Lookalike of competitor brand mark / packaging | Refuse — IP risk |

## Workflow

### Step 1: Confirm the deliverable channel and constraints

Ask, if not specified:
1. Where does this run (paid social, OOH, web hero, email, internal deck)?
2. What's the aspect ratio / size requirement?
3. Is there a brand kit or Custom Model to use, or starting from scratch?
4. Single hero image, or a variation matrix for testing?
5. Photoreal, illustrated, 3D-rendered, or hybrid?

If it's internal/exploratory only, suggest the user might get further faster with Midjourney and skip Firefly. Don't push the tool when it's wrong for the job.

### Step 2: Construct the prompt

Firefly responds best to prompts structured as: **subject + composition + lighting + style + medium**. Stuff descriptors in roughly that order; Firefly weighs early tokens more heavily.

```
A modern white ceramic coffee mug, three-quarter view, warm steam rising,
shallow depth of field with bokeh background of a softly lit kitchen,
golden hour natural light from the left, photoreal product photography,
shot on 50mm lens at f/2.8
```

Versus the same idea poorly written:
```
Coffee cup, kitchen, nice lighting, professional
```

The first generates consistently usable output; the second is roulette.

### Step 3: Use the structural controls before retrying prompts

Firefly's web UI and API expose:
- **Content type**: Photo / Art / Graphic — fundamentally changes generation
- **Aspect ratio**: Square / Landscape / Portrait / Widescreen — set this, don't crop later
- **Visual intensity**: dial back if results look over-rendered
- **Color and tone palette**: lock specific hex via reference image upload
- **Lighting**: golden hour, dramatic, studio, harsh, etc.
- **Composition**: close-up, wide-angle, knolling, isometric, etc.
- **Reference image (Structure Match)**: lock layout to a reference; vary content
- **Reference image (Style Match)**: lock style to a reference; vary subject

Use these instead of fighting with text prompts. A reference image for structure or style is worth 50 prompt tokens.

### Step 4: Variation matrix for A/B testing

For paid ads, never generate one image. Generate a matrix:

```
Variants matrix: Product hero shot
- Backgrounds: minimalist white | warm wood texture | abstract gradient
- Lighting: soft diffused | dramatic side-light | overhead sun
- Compositions: centered hero | rule-of-thirds | flat lay
= 27 variants. Cull to 6-8. A/B test top performers.
```

Generate per cell. Don't try to encode all variation in one prompt.

### Step 5: Custom Models for brand consistency

For a brand running campaigns long-term: train a Firefly Custom Model on 10–30 brand-aligned images. The model learns brand-specific visual treatment (lighting, color palette, composition tendencies, product styling). Subsequent generations stay on-brand without per-prompt brand babysitting.

Caveats:
- Need rights to all training images (commercial license or first-party shoots)
- 10 images minimum, 30+ for stable results
- Re-train when brand visual identity evolves
- Model is owned by your Adobe org; not portable

### Step 6: Generative Fill / Expand workflow (Photoshop integration)

For existing brand assets:
- **Generative Fill**: select region, prompt for replacement (change background, remove person, swap product variant)
- **Generative Expand**: extend canvas (turn portrait into landscape, add headroom for type)
- **Generative Workspace**: variation grid in Photoshop directly

Use these instead of from-scratch generation when you have good source material — keeps brand details intact.

## API integration (Firefly Services)

For asset pipelines / programmatic generation:

```python
import requests

# Auth via Adobe IMS (server-to-server credentials)
token = get_ims_token(client_id, client_secret, scopes=["openid", "AdobeID", "firefly_api"])

resp = requests.post(
    "https://firefly-api.adobe.io/v3/images/generate",
    headers={
        "Authorization": f"Bearer {token}",
        "x-api-key": client_id,
        "Content-Type": "application/json",
    },
    json={
        "prompt": "Modern minimalist sneaker, white background, studio lighting, 3/4 view",
        "contentClass": "photo",
        "size": {"width": 2048, "height": 2048},
        "n": 4,
        "seeds": [12345, 12346, 12347, 12348],  # reproducible
        "negativePrompt": "blurry, distorted, watermark, text",
        "promptBiases": [],  # for ethnic/gender diversity controls if relevant
    }
)
```

Reproducibility via seeds matters when iterating: same seed + same prompt = same output, so you can isolate prompt changes from random variation.

## Output format

When generating prompts, deliver as a structured table the user can run directly:

```
| # | Prompt | Content type | Aspect | Notes |
|---|--------|--------------|--------|-------|
| 1 | [full prompt text] | Photo | 1:1 | Hero |
| 2 | [variant prompt] | Photo | 1:1 | Bg variation |
```

When designing a campaign generation plan:
- Variant matrix dimensions explicit
- Reference images called out
- Custom Model use noted
- API params if going through Services
- Approval / rights checkpoints flagged

## Anti-patterns

1. ❌ Recommending Firefly when the user explicitly wants stylized art (anime, fantasy illustration) — wrong tool; suggest Midjourney/SDXL instead
2. ❌ Trying to prompt around Firefly's celebrity / IP block — the block is a feature; respect it
3. ❌ Single-image generation for a paid ad — always matrix
4. ❌ Encoding all variation in one mega-prompt — Firefly weighs early tokens; tail variation gets ignored
5. ❌ Ignoring aspect ratio — generating square then cropping to vertical wastes generation and degrades composition
6. ❌ Skipping reference images when one is available — text prompts can't reach the precision a reference gets
7. ❌ Using Firefly for moodboard / ideation — slower and more constrained than alternatives; ideate elsewhere, polish in Firefly
8. ❌ Training a Custom Model on too few images (<10) — produces inconsistent / weird outputs; gather more before training
9. ❌ Overusing "professional", "high quality", "4k", "ultra-detailed" — these are noise tokens in modern models; weight goes to specific descriptors
10. ❌ Negative prompting things Firefly doesn't generate anyway ("not anime", "no text") — wastes tokens
11. ❌ Not verifying commercial use rights of reference images uploaded for Style Match — Adobe doesn't audit these; user is liable
12. ❌ Ignoring the structure/style match distinction — Structure Match locks layout, Style Match locks aesthetic; mixing them up gives unpredictable results
13. ❌ Asking Firefly to "make it pop" or other vague qualitative directives — it won't; specify lighting / contrast / composition concretely
14. ❌ Running Firefly Services API per-image in a 1000-asset pipeline without caching — burns through quota; cache by (prompt, seed) hash
15. ❌ Treating Firefly output as final without color/exposure correction in Photoshop — generated images often need 2-5 minutes of touch-up to match brand color profile

## Confidence calibration

- Prompt construction: high confidence — patterns are well-tested
- Specific Firefly API params: medium — Adobe's API evolves; verify v3 vs current at https://developer.adobe.com/firefly-services/docs/firefly-api/
- Custom Model output quality: low until measured — depends entirely on training image quality and quantity
- Cross-tool comparison (Firefly vs Midjourney vs SDXL): medium — relative strengths shift with each model release; recommend Adobe's commercial-safety story holds, aesthetic ranking changes quarterly
