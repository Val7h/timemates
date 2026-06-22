# TimeMates — Brand Guidelines

> *Quem ainda lembra de você?*
>
> A reconnection app, not a network. A doorway back to people who knew you before the title, before the algorithm, before the noise.

---

## 1. Logomark Concept

### Primary recommendation: **Hourglass-T with amber glow**

A serif capital **T** whose horizontal crossbar narrows into the pinched waist of an hourglass. The lower bulb glows amber (#d4a853), as if sand is catching late-afternoon light. The top bulb is empty — time has already fallen through. Set in Crimson Text or a compatible serif so the terminals (the small flares at the ends of strokes) feel handwritten, not machined.

**Why this one wins:**
- It says *time* without a clock face (clocks feel transactional; hourglasses feel patient).
- The amber glow inside the glyph carries our entire color story in a single shape.
- Works as a single character favicon (the T alone, glowing).
- It's never been used by a social network — there is no visual collision with the anti-brands.

### Secondary variants (acceptable for sub-applications, never primary)

**Variant B — "TM" monogram in Crimson Text**
Two letters set tight, the M's middle valley dipping below the baseline so it cradles the T. Use only for stationery, footer marks, or contexts where the hourglass-T would be too small to read.

**Variant C — Polaroid frame containing lowercase "tm"**
A 4:5 polaroid silhouette tilted -3°, with "tm" handwritten inside in warm white. Reserved for editorial moments (e.g., the "About" page, a t-shirt, an email header). Not for product chrome.

### Logo do-not list
- Do not place the logomark on pure white. It needs warmth around it — either #0a0a0a, #fff8e7, or a sepia photograph.
- Do not rotate beyond ±4°. We tilt polaroids, not the brand.
- Do not animate the sand falling. The hourglass is paused on purpose; time is the subject, not the spectacle.

---

## 2. Color System

| Role | Token | Hex / Value | Notes |
|---|---|---|---|
| **Primary** | `--tm-amber` | `#d4a853` | Saudade dusk. The single accent that earns every appearance. |
| **Secondary** | `--tm-paper` | `#fff8e7` | Warm white — old photo paper, never sterile white. |
| **Background** | `--tm-black` | `#0a0a0a` | Cinematic black. Slightly off true black so it feels filmed, not printed. |
| **Sunset gradient (start)** | `--tm-sunset-1` | `#ff7e5f` | Use sparingly — for emotional crescendos (a successful reconnect, a "welcome back" hero). |
| **Sunset gradient (end)** | `--tm-sunset-2` | `#feb47b` | Pair only with `--tm-sunset-1`. Linear, 135°. |
| **Muted text** | `--tm-muted` | `rgba(255, 248, 231, 0.55)` | Secondary body text, timestamps, captions. |
| **Error / warning** | `--tm-rose-dust` | `#ff6666` | Rose dust — a faded rose, not an alarm. |
| **Success** | `--tm-garden` | `#16a766` | Telha verde de jardim — the green of a tile roof seen through leaves. |

### Usage ratios (60 / 30 / 8 / 2)
- **60% black** — surfaces, backgrounds, breathing room
- **30% paper / muted** — body copy, secondary UI
- **8% amber** — one focus per screen (primary CTA, the heart of a memory)
- **2% sunset/rose/garden** — emotional accents only

### Color do-not list
- No cold blues. No neon anything. No pure #FFFFFF or #000000.
- Never use amber as a background. It is light, not surface.
- Sunset gradient is not a default — it is a moment.

---

## 3. Typography

### Families
- **Display — Crimson Text** (humanist serif). Used for headlines, the tagline, quotations, and any moment of emotional weight. Italic is allowed for whispers ("você lembra?").
- **Body — system sans-serif** (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`). For interface labels, forms, body copy.
- **Mono — `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`**. Reserved for developer-facing surfaces only. **Never inline mono in user-facing copy** — it breaks the warmth.

### Size scale (rem)
| Token | rem | Use |
|---|---|---|
| `--tm-text-xs` | 0.875 | captions, timestamps, metadata |
| `--tm-text-sm` | 1 | body |
| `--tm-text-md` | 1.125 | lead paragraphs |
| `--tm-text-lg` | 1.5 | sub-headings |
| `--tm-text-xl` | 2 | section heads |
| `--tm-text-2xl` | 3 | page heroes |
| `--tm-text-3xl` | 4 | the tagline, once per page maximum |

### Type rules
- Line-height on Crimson Text: 1.25 for display, 1.5 for body.
- Letter-spacing: never tight on serif. Slightly looser (+0.01em) on small caps if used.
- No all-caps headlines. We don't shout. Sentence case for everything except proper nouns.

---

## 4. Voice & Tone

We sound like a friend texting you at 2am — present, gentle, a little bit sad in a good way.

### Five voice attributes

**1. Saudoso (longing, never kitsch)**
Saudade is a feeling, not a costume. We don't say "the good old days." We say "aquele verão." Specific beats sentimental.

**2. Brotherly / sisterly (warm 2am friend)**
"Tô aqui, ó." Not "Estamos disponíveis 24/7." We speak like someone who knows your name and remembers your story.

**3. Bittersweet (joy with a lump in the throat)**
Reconnection is wonderful and also a little bit painful — because time passed. Don't sand the edge off that. The lump is the feature.

**4. Brazilian intimate**
Use **vocês**, **gente**, **galera**. Use diminutives sparingly but lovingly ("um cafezinho", "uma mensagenzinha"). Never **vós**. Never staff-speak ("nossa equipe", "nossos colaboradores", "atendimento ao cliente").

**5. Specific, never abstract**
"Aquele banco da praça em frente ao colégio" > "lugares memoráveis". Concrete nouns are saudade currency.

### Forbidden vocabulary
The following words are **banned** from user-facing copy unless used as a negation (i.e., "isso aqui não é uma rede de *networking*"):

- networking, network, networkar
- engagement, engajamento (as a metric goal)
- performance (as a verb/metric — "performar")
- conexões profissionais
- ROI, KPI, métrica
- usuário (use "pessoa", "alguém", "você")
- plataforma (use "lugar", "espaço", "casa")
- comunidade (overused; if needed, prefer "turma", "galera", "quem te conhece")
- match, swipe, like
- conteúdo (use "lembrança", "história", "foto", "mensagem")
- monetizar, monetização

### Tone examples

| Don't say | Say instead |
|---|---|
| Bem-vindo à plataforma TimeMates! | Você voltou. A gente guardou seu lugar. |
| Crie sua conta para começar a fazer networking | Conta pra gente quem você foi — a gente te ajuda a encontrar quem ainda lembra. |
| 3 novos usuários querem se conectar com você | Três pessoas digitaram seu nome essa semana. |
| Falha no login. Tente novamente. | A senha não bateu. Tudo bem, acontece — tenta de novo? |
| Pagamento processado com sucesso | Pronto. Obrigado por sustentar esse lugar. |

---

## 5. Visual Elements

### The grammar of warmth

**Polaroid frames** — Every memory artifact is framed as a polaroid. Width:height ratio 4:5. Bottom caption area ~18% of the frame, room for one handwritten line. Slight rotation: random between **-4° and +4°**, never 0°. A perfectly straight polaroid feels like a stock photo.

**Soft drop shadow** —
```
box-shadow: 0 8px 24px rgba(212, 168, 83, 0.12), 0 2px 6px rgba(0, 0, 0, 0.4);
```
A whisper of amber warmth under every elevated surface, plus a deeper black to anchor.

**Amber glow gradients** — Radial, centered on the focal point, fading to transparent black:
```
background: radial-gradient(circle at center, rgba(212, 168, 83, 0.18) 0%, transparent 70%);
```
Used behind hero text, behind the logomark, behind a featured memory.

**Vinyl crackle pattern** — A subtle noise texture, 4% opacity, screen-blended over large dark surfaces. Suggests an LP, a cassette, time itself. Never animated.

**Hand-drawn pencil annotations** — For emphasis: an underline that wobbles, a circle around a name, an arrow pointing to a photograph. SVG, single stroke, slightly imperfect. Use sparingly — once or twice per page, never as a system pattern.

**Super-8 grain** — 8% opacity film grain layered over hero images and the landing page background. Animated only at a very slow loop (one cycle ≥ 8s), or static. Never strobing.

### Visual do-not list
- **No neon.** No glow that screams.
- **No cold blue.** Not in icons, not in shadows, not in gradients.
- **No sharp 90° corners** on cards or buttons. Border-radius minimum 6px, prefer 12–16px on cards.
- **No iconography sets that look like Material or Fluent.** Prefer line icons with slight imperfections, or no icons at all (a serif label is often warmer than a glyph).
- **No skeletons that pulse blue.** Loading states are amber-tinted, slow.
- **No emoji explosions.** One emoji per message, maximum, and only when the writer would actually use one.

---

## 6. Anti-Brand — O que NÃO somos

We define ourselves against the five companies that have shaped how Brazilians think about being online together. We are explicitly not them.

### Não somos o Facebook
Facebook turns acquaintances into a feed. We are not a feed. There is no infinite scroll, no algorithmic ranking, no "people you may know" based on cookie graphs. **Reconnection is intentional, slow, and private.**

### Não somos o LinkedIn
LinkedIn measures a person by job title. We measure no one. There are no titles on a TimeMates profile by default — there are years, schools, neighborhoods, and a question: *do you remember me?* **Worth is not a job description.**

### Não somos o Tinder
Tinder is a marketplace of bodies optimized for desire. We are the opposite: a quiet room for people who already mattered to you. **No swiping. No matching. No "compatibility."** If two people reconnect on TimeMates, it's because they shared a real chapter, not because an algorithm guessed.

### Não somos o Instagram
Instagram is filtered performance — the best angle, the best vacation, the best life. TimeMates shows polaroids on purpose: imperfect, dated, intimate. **No filters that improve. No metrics on a profile. No flexing.**

### Não somos o WhatsApp
WhatsApp is the layer where Brazilian life already happens — once you have someone's number. We are the layer *before* WhatsApp: the layer that helps you find the number again, or decide it's okay not to. **When two people are reconnected, our job is done. We hand them off and step back.**

---

## 7. Applications

### Favicon (32×32, 16×16)
Amber "T" (hourglass-T mark, no wordmark) on `#0a0a0a` background. Square, no padding inside. Export as `.ico` and `.png`.

### Apple touch icon (180×180)
Same amber "T" on `#0a0a0a`, but inside iOS's automatic rounded-square mask. Add 14% safe padding around the glyph so the rounded mask doesn't clip the terminals of the serif.

### Open Graph image (1200×630)
- Background: `#0a0a0a` with a faint radial amber glow centered slightly left of center
- Tagline: **"Quem ainda lembra de você?"** in Crimson Text Italic, color `#d4a853`, set at ~96px
- Bottom-right: small polaroid frame (≈ 180px wide) tilted -3°, containing a soft sepia photo (or a placeholder sepia rectangle for the template), with the wordmark "TimeMates" handwritten beneath in `#fff8e7`
- Super-8 grain 8% opacity over the whole image
- 64px margin on all edges

### Browser title (HTML `<title>`)
Pattern: `{Page} — TimeMates`
- Home: `TimeMates — quem ainda lembra de você?`
- Profile: `Mariana, 1998 — TimeMates`
- Avoid pipes (`|`). The em-dash is part of our voice.

### Email signature (transactional and human emails)
```
—
TimeMates — feito no Brasil com saudade
{email-specific link, if any}
```
No logos in signature. No social icons. The dash, the line, nothing more.

### App store / play store short description
"Reencontre quem te conheceu antes de tudo isso."
(120 characters, no buzzwords, ends with a period because we don't yell.)

### Push notifications
Maximum 14 words. Use someone's name when possible. Examples:
- "Mariana lembrou de você essa semana."
- "Três pessoas digitaram seu nome. Quer ver quem?"
- "Hoje faz 20 anos que vocês estavam na mesma sala."

Never: "Você tem 3 novas notificações." We don't count, we don't batch.

---

## 8. Quick reference — the brand in one breath

> TimeMates is the warm room you walk back into. Black walls, amber lamp, an old photo on the table, someone you used to know saying *"caramba, quanto tempo."*
>
> If a design decision doesn't fit that room, it doesn't belong to us.

— *feito no Brasil com saudade*
