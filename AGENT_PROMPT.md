# Restyling brief — Torn Cashflow "Speakeasy Ledger"

Hand this to a coding agent (or follow it yourself) to restyle the Streamlit
**Torn Cashflow Dashboard** in an old-school gangster-noir, gold-and-black,
art-deco look. Visual reference: `Torn Cashflow Mafia.dc.html` (option **1a**).

---

## 1. The look in one paragraph

Torn City after dark, seen through a bootlegger's ledger. Warm near-black paper
(`#14100b`), brass-gold ink (`#c9a227`, highlight `#e4c258`), champagne body text
(`#e8dfc9`). Engraved **Cinzel** for every heading and KPI number; condensed
**Oswald**, uppercase and letter-spaced, for labels, buttons, table headers and
nav; **Archivo** for body copy. Square corners everywhere — no rounded pills.
Thin gold hairlines and small rotated-square (diamond) accents stand in for
art-deco ornament. Positive money reads olive-gold, losses read oxblood
(`#a33a2e`). Restrained and expensive, not neon.

## 2. Palette tokens

| Token | Hex | Use |
|---|---|---|
| ink | `#0a0806` | deepest black, input fields |
| canvas | `#14100b` | app background |
| panel | `#1d1710` | cards, sidebar, inputs |
| panel-2 | `#181209` | nested panels, alerts |
| line | `#2c2216` | hairline borders |
| line-lit | `#3a2e1e` | stronger borders |
| gold | `#c9a227` | primary accent, buttons, active state |
| gold-bright | `#e4c258` | KPI numbers, hover, highlights |
| text | `#e8dfc9` | body |
| text-mute | `#9a8e74` | labels |
| text-dim | `#7d7159` | captions |
| green | `#7f9a5b` | positive cashflow |
| red | `#a33a2e` | negative / danger |

## 3. Type

- Headings + big KPI values: **Cinzel** 700.
- Labels, buttons, nav, table headers, metric labels: **Oswald**, `text-transform:uppercase`, `letter-spacing:.12–.24em`.
- Body: **Archivo**.
- Loaded via `@import` at the top of `speakeasy.css` (Google Fonts).

## 4. How it's wired (already done for you)

Three files were added to the app:

1. **`.streamlit/config.toml`** — `[theme]` block sets base dark colors + primary gold. Streamlit reads this automatically.
2. **`speakeasy.css`** — all deep styling, targeting stable `[data-testid=...]` hooks.
3. **`theme.py`** — `inject_theme()` reads the CSS and injects it via `st.markdown(..., unsafe_allow_html=True)`.

**Remaining task:** add these two lines to the top of **every** page, immediately
after each file's `st.set_page_config(...)` call:

```python
import theme
theme.inject_theme()
```

Files to edit: `app.py`, `pages/1_Dashboard.py`, `pages/2_Sync.py`,
`pages/3_Checklist.py`, `pages/4_Settings.py`, `pages/5_Categories.py`.
(Config-only base colors apply without this, but the fonts, borders, KPI
brackets and deco accents need the CSS injection on each page.)

## 5. Plotly charts

`config.toml` doesn't reach Plotly. In `pages/1_Dashboard.py`, give each figure a
matching template so the charts read as gold-on-black panels rather than default
white. Apply to every `px.bar` / `px.line` before `st.plotly_chart`:

```python
fig.update_layout(
    paper_bgcolor="#181209", plot_bgcolor="#181209",
    font=dict(color="#cdbf9c", family="Oswald"),
    colorway=["#c9a227", "#e4c258", "#8a6d1a", "#a33a2e", "#7f9a5b"],
    xaxis=dict(gridcolor="#2c2216", zerolinecolor="#3a2e1e"),
    yaxis=dict(gridcolor="#2c2216", zerolinecolor="#3a2e1e"),
    margin=dict(l=10, r=10, t=10, b=10),
)
```

For the category breakdown bar, drop the rainbow `color="category"` and colour
by sign instead (gold for positive cashflow, oxblood for negative) so the chart
matches the KPI language.

## 6. Torn flavour (copy, optional)

Keep it subtle — a speakeasy accountant, not a caricature. Section eyebrows like
"THE BOOKS", "KEEPING IT STRAIGHT"; the API-key card as "THE COMBINATION";
War Mode chip glows oxblood when ON. Leave the actual data labels
(Cashflow, Networth, Energy, categories) untouched — they must stay accurate.

## 7. Verify

Run `streamlit run app.py`. Check: dark warm canvas, Cinzel headings, gold KPI
tiles with the top-left corner bracket, uppercase Oswald buttons/nav, square
corners, gold-tinted charts, oxblood on the Danger Zone / negative values. If a
Streamlit update renames a `data-testid`, fix the selector in `speakeasy.css` —
that's the only file that needs touching.
