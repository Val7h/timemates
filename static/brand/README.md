# TimeMates — Brand Assets

This folder holds the canonical brand assets wired into every HTML page in `static/`.

## Files

| File | Purpose | Where it's used |
|------|---------|-----------------|
| `logo.svg` | Primary logo — Hourglass-T with amber glow (serif capital T whose crossbar narrows into an hourglass waist; lower bulb glows amber `#d4a853`). | In-product headers, marketing surfaces. Reference via `/static/brand/logo.svg`. |
| `favicon.svg` | Browser tab icon (scales from 16px up — pure vector). | `<link rel="icon" type="image/svg+xml" href="/static/brand/favicon.svg">` on every page. |
| `apple-touch-icon.svg` | iOS home-screen icon. | `<link rel="apple-touch-icon" href="/static/brand/apple-touch-icon.svg">` on every page. |
| `og-image.svg` | Social share card (1200×630) for WhatsApp / Twitter / Facebook / iMessage previews. | `og:image` and `twitter:image` meta tags on every page. |
| `design-tokens.css` | CSS custom properties for the full color palette + typography. Loaded globally so every page shares the same vocabulary. | `<link rel="stylesheet" href="/static/brand/design-tokens.css">` on every page. |

## Palette (8 colors, defined in design-tokens.css)

The brand lives in the late-afternoon end of the day — warm blacks, amber catching the last light, sunset orange. Anti-brand: no cold blues, no neon, no flat gray.

Primary: `#d4a853` (amber), `#0a0604` (warm black), `#fff8e7` (cream text).

See `BRAND_GUIDELINES.md` at the repo root for the full strategy doc (positioning, voice, anti-brand, usage rules).

## Serving

All files are served via FastAPI's `/static` mount in `main.py`:

```python
app.mount("/static", StaticFiles(directory="static"), name="static_files")
```

So `static/brand/logo.svg` → `https://timemates.onrender.com/static/brand/logo.svg`.

## When updating

1. Edit the SVG / CSS directly here.
2. If you change `og-image.svg`, also bump a cache-buster query in the meta tags (`?v=2`) — WhatsApp aggressively caches OG images.
3. Keep `design-tokens.css` the single source of truth for color values; don't fork the palette into per-page `<style>` blocks.
