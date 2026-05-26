# Store Template Field Guide

This project is a reusable Flask ecommerce store template. For each new store, copy the folder, add the store images, then edit environment values instead of editing templates directly.

Use [store_profile.example.env](store_profile.example.env) as the copyable checklist.

## Fast Setup For A New Store

1. Copy this folder and rename it for the store.
2. Copy `store_profile.example.env` to your real environment file or hosting variables.
3. Replace the identity fields first: `STORE_NAME`, `STORE_EMAIL`, `STORE_PHONE`, logos, and hero image.
4. Configure `CHECKOUT_SHIPPING_ZONES` and payment toggles.
5. Add products/categories from the admin panel.
6. Run the app and check home, product, checkout, receipt email, and policy pages.

## Store Identity

These control the visible brand/contact info across navbar, footer, contact page, emails, shipping pickup, and SEO defaults.

| Field | What to edit |
| --- | --- |
| `STORE_NAME` | Public store name shown in title/footer/emails. |
| `STORE_LEGAL_NAME` | Legal/company name if different from public name. |
| `STORE_COUNTRY` | Default country text. |
| `STORE_LOCATION_TEXT` | Footer/contact location text, e.g. `Online store`. |
| `STORE_EMAIL` | Main public email. |
| `STORE_SUPPORT_EMAIL` | Support email shown in account/contact/email receipt. |
| `ADMIN_MAIL` | Where admin order notifications go. |
| `STORE_PHONE` | Raw phone link value, e.g. `+00000000000`. |
| `STORE_PHONE_DISPLAY` | Human-readable phone text. |
| `STORE_PHONE_COUNTRY_CODE` | Default phone code in checkout. |
| `STORE_WHATSAPP_URL` | WhatsApp link. Leave blank to hide. |
| `STORE_INSTAGRAM_URL` | Instagram link. Leave blank to hide. |
| `STORE_INSTAGRAM_HANDLE` | Instagram account text shown to customers, e.g. `@mq.cars`. |
| `STORE_TIKTOK_URL` | TikTok link. Leave blank to hide. |

## Images

Put images inside `app/static/`, then point these fields to them.

| Field | What it controls |
| --- | --- |
| `STORE_LOGO` | Navbar logo. |
| `STORE_SECONDARY_LOGO` | Homepage feature logo/image. |
| `STORE_HERO_IMAGE` | Main homepage hero image. |
| `SEO_OG_IMAGE` | Link preview image. |
| `SEO_WHATSAPP_IMAGE` | WhatsApp/social preview image. |

Example:

```bash
STORE_LOGO="/static/my-logo.png"
STORE_HERO_IMAGE="/static/my-hero.jpg"
```

## Theme

These control the visual style without touching HTML/CSS.

| Field | What it controls |
| --- | --- |
| `STORE_PRIMARY_COLOR` | Main black/dark brand color. |
| `STORE_ACCENT_COLOR` | Buttons, borders, highlights. |
| `STORE_BACKGROUND_COLOR` | Page background. |
| `STORE_SURFACE_COLOR` | Light sections/cards. |
| `STORE_TEXT_COLOR` | Main text color. |
| `STORE_MUTED_TEXT_COLOR` | Secondary text color. |
| `STORE_FONT` | Body font from Google Fonts. |
| `STORE_HEADING_FONT` | Heading font from Google Fonts. |
| `STORE_ARABIC_FONT` | Arabic font from Google Fonts. |
| `STORE_BUTTON_RADIUS` | Button rounding, e.g. `0px`, `6px`, `999px`. |
| `STORE_CARD_RADIUS` | Card rounding. |
| `STORE_LOGO_WIDTH` | Navbar logo width. |
| `STORE_LOGO_HEIGHT` | Navbar logo height. |
| `STORE_HERO_OVERLAY` | Hero image overlay, e.g. `rgba(0,0,0,0.25)`. |
| `STORE_HERO_POSITION` | Hero image crop, e.g. `center 30%`. |

## Homepage Sections

Use `true` or `false`.

| Field | Effect |
| --- | --- |
| `SHOW_FEATURED_CATEGORIES` | Shows/hides the shop-all block and homepage category rows. |
| `SHOW_WHY_US` | Shows/hides the why-us feature section. |
| `SHOW_REVIEWS` | Shows/hides reviews and review form. |
| `SHOW_NEWSLETTER` | Shows/hides newsletter footer block. |
| `SHOW_POLICIES` | Shows/hides homepage policy tiles. |

## Homepage Copy

| Field | What it controls |
| --- | --- |
| `STORE_HERO_TITLE_EN` / `STORE_HERO_TITLE_AR` | Hero title. |
| `STORE_HERO_SUBTITLE_EN` / `STORE_HERO_SUBTITLE_AR` | Hero subtitle. |
| `STORE_WHY_TITLE_EN` / `STORE_WHY_TITLE_AR` | Why-us title. |
| `STORE_WHY_SUBTITLE_EN` / `STORE_WHY_SUBTITLE_AR` | Why-us subtitle. |
| `STORE_FOOTER_ABOUT_EN` / `STORE_FOOTER_ABOUT_AR` | Footer brand paragraph. |
| `HOME_POLICY_SHIPPING_SUB_EN` / `HOME_POLICY_SHIPPING_SUB_AR` | Homepage shipping tile subtitle. |
| `HOME_POLICY_RETURN_SUB_EN` / `HOME_POLICY_RETURN_SUB_AR` | Homepage return tile subtitle. |

## Checkout Shipping Zones

Use `CHECKOUT_SHIPPING_ZONES` for one or multiple countries/areas.

Format:

```bash
CHECKOUT_SHIPPING_ZONES="name|label|phone_code|shipping_label|shipping_rate|free_shipping_threshold;name2|label2|phone2|shipping label2|rate2|threshold2"
```

Example:

```bash
CHECKOUT_SHIPPING_ZONES="Country|Country|+000|Standard Delivery|1.5|20;Second Country|Second Country|+111|Regional Shipping|5|50"
```

Meaning:

| Part | Meaning |
| --- | --- |
| `name` | Stored value in orders. |
| `label` | Customer-facing dropdown label. |
| `phone_code` | Phone code selected for that country/area. |
| `shipping_label` | Shipping option label shown at checkout. |
| `shipping_rate` | Shipping fee in base currency. |
| `free_shipping_threshold` | If cart subtotal reaches this, shipping becomes free. Use `0` to disable. |

## Payment Options

Use `true` or `false`.

| Field | Effect |
| --- | --- |
| `ENABLE_COD` | Enables cash on delivery button and server acceptance. |
| `ENABLE_TAP` | Enables online payment flow through Tap. |
| `ENABLE_BENEFITPAY` | Shows BenefitPay as an online option label. |
| `ENABLE_CARD_PAYMENT` | Shows card as an online option label. |
| `TAP_SECRET_KEY` | Tap secret key. Required when online payment is enabled. |
| `TAP_PUBLIC_KEY` | Tap public key if needed by frontend/payment config. |

## Mail And Receipt Emails

| Field | What it controls |
| --- | --- |
| `MAIL_SERVER` | SMTP host. |
| `MAIL_PORT` | SMTP port. |
| `MAIL_USE_TLS` | Enable TLS. |
| `MAIL_USE_SSL` | Enable SSL. |
| `MAIL_USERNAME` | SMTP username. |
| `MAIL_PASSWORD` | SMTP password. |
| `MAIL_SENDER_NAME` | Sender display name. |
| `MAIL_DEFAULT_SENDER` | Sender email. |
| `EMAIL_BRAND_COLOR` | Receipt email main color. |
| `EMAIL_ACCENT_COLOR` | Receipt email accent color. |
| `EMAIL_RECEIPT_SUBJECT` | Customer receipt subject. Supports `{order_id}`, `{store_name}`, `{amount}`, `{currency}`, `{status}`. |
| `EMAIL_ADMIN_SUBJECT` | Admin notification subject. Same placeholders. |
| `EMAIL_SUPPORT_CTA` | Help text inside receipt email. |

## SEO / Social Preview

| Field | What it controls |
| --- | --- |
| `SEO_TITLE` | Browser title and OG title. |
| `SEO_DESCRIPTION` | Meta description and social description. |
| `SEO_KEYWORDS` | Optional meta keywords. |
| `SEO_OG_IMAGE` | Open Graph preview image. |
| `SEO_WHATSAPP_IMAGE` | WhatsApp/Twitter preview image. |

## Policies

These appear on the help/policy page.

| Field | What it controls |
| --- | --- |
| `POLICY_LAST_UPDATED` | Last updated label. |
| `POLICY_SHIPPING_INTRO` | Shipping section intro. |
| `POLICY_SHIPPING_POINT_1` / `2` / `3` | Shipping bullet points. |
| `POLICY_REFUND_RULE` | Refund highlighted rule. |
| `POLICY_REFUND_PROCESS` | Refund process text. |
| `POLICY_REFUND_CONDITION` | Refund condition text. |
| `POLICY_REFUND_NOTE` | Refund note. |
| `POLICY_PRIVACY_INTRO` | Privacy section intro. |
| `POLICY_PRIVACY_POINT_1` / `2` | Privacy bullet points. |
| `POLICY_TERMS` | Terms section body. |

## Product Translation Glossary

Use this when product/category words need custom Arabic translation.

Format:

```bash
STORE_GLOSSARY="english phrase:arabic phrase;another phrase:another translation"
```

Example:

```bash
STORE_GLOSSARY="gift box:علبة هدية;premium flowers:ورد فاخر"
```

## Shipping Provider Pickup Details

Only needed if you connect the shipping provider integration.

| Field | What it controls |
| --- | --- |
| `STORE_PICKUP_ADDRESS` | Pickup address sent to shipping provider. |
| `STORE_PICKUP_LNG` | Pickup longitude. |
| `STORE_PICKUP_LAT` | Pickup latitude. |
| `STORE_DISPATCH_NAME` | Pickup contact name. |
| `STORE_DISPATCH_EMAIL` | Pickup contact email. |
| `SHIPPING_BASE_URL` | Shipping API base URL. |
| `SHIPPING_CLIENT_ID` | Shipping API client ID. |
| `SHIPPING_CLIENT_SECRET` | Shipping API client secret. |
| `SHIPPING_CUSTOMER_ID` | Shipping API customer ID. |

## Usually Do Not Edit

These are code/template files. Prefer env fields first.

| File | When to edit |
| --- | --- |
| `config.py` | Only when adding a new template field. |
| `app/templates/base.html` | Only when changing global layout. |
| `app/templates/main/home.html` | Only when changing homepage structure. |
| `app/templates/main/checkout.html` | Only when changing checkout workflow. |
| `app/translations.py` | Only for fixed app labels, not per-store copy. |

## Quick New Store Checklist

- `STORE_NAME`
- `STORE_EMAIL`
- `STORE_PHONE`
- `STORE_WHATSAPP_URL`
- `STORE_LOGO`
- `STORE_HERO_IMAGE`
- `STORE_PRIMARY_COLOR`
- `STORE_ACCENT_COLOR`
- `CHECKOUT_SHIPPING_ZONES`
- `ENABLE_COD` / `ENABLE_TAP`
- `MAIL_USERNAME` / `MAIL_PASSWORD`
- `SEO_TITLE` / `SEO_DESCRIPTION`
- Policy fields if this store needs custom legal wording
