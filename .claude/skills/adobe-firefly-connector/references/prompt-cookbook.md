# Firefly Prompt Cookbook

Patterns proven to produce consistently usable Firefly output. Copy, adapt, vary.

## The base structure

`subject + composition + lighting + style + medium`

Order matters — Firefly weighs early tokens more heavily.

---

## Product photography

### Hero shot, white background
```
[Product] centered, three-quarter view, slight downward angle,
floating shadow beneath, pure white seamless background,
soft diffused studio lighting from upper left, fill light from right,
photoreal product photography, shot on 100mm macro lens at f/8
```

### Hero shot, contextual background
```
[Product] in [environment context], natural [time of day] lighting,
shallow depth of field background bokeh, [emotion/mood],
photoreal, shot on 50mm at f/2.8
```

### Lifestyle shot
```
[Person demographic] using [product] in [environment],
candid moment, natural light, warm color grading,
medium shot, shallow depth of field,
photoreal lifestyle photography
```

### Flat lay / knolling
```
[Product] arranged with [complementary items: notebook, coffee, plants],
overhead shot, 90-degree top-down, even soft daylight,
neutral background [linen/wood/marble texture],
flat lay photography style
```

---

## Backgrounds

### Minimalist gradient
```
Smooth color gradient from [color 1] at top to [color 2] at bottom,
subtle texture, no objects, no text, abstract background
```

### Texture / surface
```
Close-up of [material: marble / linen / wood / paper],
soft natural side-lighting, no objects, neutral tone, photoreal texture
```

### Atmospheric
```
[Environment: misty forest / sunlit window / city at dusk],
deep depth of field, atmospheric haze, no people, no text,
cinematic color grading
```

---

## People (Firefly avoids real recognizable individuals)

### Generic professional
```
[Age range] professional [field] in [setting], working at [activity],
candid expression, natural lighting, modern office context,
medium shot, shallow depth of field, photoreal portrait
```

### Lifestyle person
```
[Age range] [demographic descriptor] in [environment],
[action / mood], golden hour lighting, warm tones,
candid documentary style
```

Use prompt biases for ethnic / gender diversity controls when relevant.

---

## Illustrations

### Editorial illustration
```
[Concept] visualized, flat illustration style, [color palette],
geometric composition, modern editorial style,
clean lines, minimal shading
```

### 3D render
```
[Subject] in 3D render, isometric view,
[color palette], soft global illumination,
matte materials with subtle highlights, clean modern 3D illustration
```

### Hand-drawn
```
[Subject], hand-drawn ink illustration, line art with light watercolor,
loose confident strokes, white background, organic feel
```

---

## Common modifiers

### Lighting
- `soft diffused studio lighting` — clean product shots
- `golden hour natural light` — warm lifestyle
- `dramatic side lighting` — moody portraits
- `overhead noon sun` — flat lay, harsh shadows
- `window light from left` — natural portrait
- `cinematic three-point lighting` — controlled drama

### Composition
- `centered, symmetrical` — formal hero
- `rule of thirds, off-center` — editorial
- `flat lay, top-down` — knolling
- `close-up macro` — detail
- `wide environmental` — context-rich
- `over-the-shoulder POV` — first-person feel

### Mood
- `serene and calm` / `energetic and dynamic` / `intimate and warm`
- `sophisticated and refined` / `playful and casual`
- `documentary and candid` / `polished and commercial`

### Color treatment
- `warm tones, golden palette`
- `cool tones, blue-grey palette`
- `desaturated, muted earth tones`
- `vibrant, high saturation`
- `monochromatic [color]`
- `complementary [color] and [color] accents`

---

## What NOT to put in prompts

These tokens are noise in modern Firefly:
- "professional", "high quality", "ultra-detailed", "4K", "8K"
- "best quality", "masterpiece"
- "trending on artstation"
- "award-winning"

The model already aims for quality. Spend tokens on specifics instead.

---

## Negative prompts that actually help

- For photoreal: `cartoon, illustration, painting, anime`
- For people: `distorted features, extra limbs, deformed hands`
- For products: `text, watermark, logo, packaging text`
- For minimalism: `cluttered, busy, multiple objects`

Don't bother negating things Firefly doesn't generate (`no NSFW`, `not violent`).

---

## Reference image patterns

### Structure Match (lock layout, vary content)
Upload a reference image with the composition you want; Firefly will preserve layout while varying content per your text prompt.

Use case: brand-consistent ad layouts where you generate variants of a hero product shot, with the same composition structure but different products / colors.

### Style Match (lock aesthetic, vary subject)
Upload a reference for visual style (lighting / color / treatment); Firefly varies subject while preserving style.

Use case: maintaining brand visual treatment across diverse subject matter for a campaign.

### Combined
Structure Match for layout + Style Match for treatment + text prompt for subject = highly controlled generation.

Caveat: ensure rights to all reference images. Firefly doesn't audit them; user is liable.

---

## Variant prompt patterns

For systematic variation, hold most variables and change one:

### Background variation
```
Base: [Product], centered, white background, studio lighting, photoreal
V1: ...background variation: warm wood texture
V2: ...background variation: minimalist concrete
V3: ...background variation: lush greenery
```

### Lighting variation
```
Base: [Product], centered, white background, photoreal
V1: ...soft diffused studio lighting
V2: ...dramatic side lighting from left
V3: ...overhead noon sunlight, harsh shadows
V4: ...golden hour warm lighting
```

### Composition variation
```
Base: [Product], white background, soft lighting, photoreal
V1: ...centered hero, three-quarter view
V2: ...rule of thirds, side angle
V3: ...flat lay, top-down view
V4: ...close-up macro detail
```

Generate matrix; cull to top performers; A/B test.

---

## Custom Models

Train a Firefly Custom Model when:
- Brand needs visual consistency across many generations
- 10+ training images available with full commercial rights
- Long-term campaign / always-on creative need

Training set composition:
- 10–30 images (more = more stable)
- Consistent visual treatment across set
- Clear category focus (products / lifestyle / illustrations — pick one)
- Diverse within category (different angles, contexts, lighting variations)

Re-train when brand visual identity evolves significantly.

Custom Model is owned by your Adobe org; not portable.

---

## Tips for hands-on generation

- Generate 4 variants per prompt (n=4 in API; default in UI)
- Use seeds for reproducibility when iterating
- Use Style Match upload before fighting with words
- Cull aggressively — don't fall in love with first generation
- Color-correct in Photoshop after; Firefly outputs may not match brand color profile precisely
- For final brand surfaces, treat Firefly as starting point, not finished asset

---

## API quick reference

```python
{
  "prompt": "[full prompt]",
  "contentClass": "photo" | "art" | "graphic",
  "size": {"width": int, "height": int},
  "n": 1-4,
  "seeds": [int, ...],  # optional, for reproducibility
  "negativePrompt": "[negative]",
  "promptBiases": [...],  # diversity controls
  "styleReference": {...},  # Style Match
  "structureReference": {...}  # Structure Match
}
```

Verify v3 endpoint and current schema at https://developer.adobe.com/firefly-services/docs/firefly-api/

Auth via Adobe IMS server-to-server credentials. Rate limit / quota varies by plan.
