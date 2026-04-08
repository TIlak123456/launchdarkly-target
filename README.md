# LaunchDarkly Demo — Part 2: Target

A Python Flask web application demonstrating LaunchDarkly's **individual and rule-based targeting** capabilities.

## What This Demonstrates

**Scenario:** ABC Company is revamping their landing page. Your team owns the hero CTA banner — a high-visibility component seen by ~40,000 daily visitors. You're using LaunchDarkly to target different banner variations to different user segments.

| Requirement | Implementation |
|---|---|
| **Feature Flag** | A `hero-banner` multivariate string flag controls which hero CTA banner is shown |
| **Context Attributes** | Users have rich attributes: `plan`, `role`, `country`, `company`, `email` |
| **Individual Targeting** | A specific user (Carol) is individually targeted to see the "Internal Preview" banner |
| **Rule-Based Targeting** | Users with `plan=free` see "Upgrade to Pro"; users with `plan=enterprise` see "Talk to Sales" |

## Banner Variations

| Variation | Visual | Target | Example User |
|---|---|---|---|
| `control` | Purple gradient — "Build Better Software" | Default (everyone else) | Eve (pro plan) |
| `upgrade-cta` | Pink/red gradient — "Upgrade to Pro — 50% Off" | Rule: `plan` = `free` | Alice, Dave |
| `enterprise-cta` | Teal/green gradient — "Your Enterprise Account is Growing" | Rule: `plan` = `enterprise` | Bob |
| `internal-preview` | Dark with red border — "AI-Powered Flag Suggestions" | Individual: `user-003` (Carol) | Carol |

## How It Works

The app includes a **User Simulator** panel with 5 pre-defined users. Click a user button to switch contexts — the hero banner updates instantly based on LaunchDarkly's targeting rules.

```
User clicks "Bob Manager" button
        │
        ▼
JS SDK calls client.identify(bobContext)
        │
        ▼
LaunchDarkly evaluates targeting rules:
  1. Individual targets? No match.
  2. Rule: plan = "free"? Bob is "enterprise" — no match.
  3. Rule: plan = "enterprise"? Bob IS enterprise — MATCH!
        │
        ▼
Returns "enterprise-cta" variation
        │
        ▼
Hero banner switches to "Talk to Sales" (teal/green gradient)
```

---

## Prerequisites

1. **Python 3.8+** installed
2. **pip** (Python package manager)
3. **A LaunchDarkly account** — [Sign up for a free trial](https://launchdarkly.com/start-trial/)

---

## Setup Instructions

### Step 1: Install Dependencies

```bash
cd ~/launchdarkly-target

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate   # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure SDK Keys

```bash
cp .env.example .env
nano .env
```

Paste your LaunchDarkly SDK key and Client-side ID (same keys as Part 1 if using the same project/environment).

### Step 3: Create the `hero-banner` Feature Flag

In the LaunchDarkly dashboard:

1. Click **Feature flags** > **Create flag**
2. Configure:
   - **Name:** `Hero Banner`
   - **Key:** `hero-banner` (must match exactly)
   - **Flag type:** String
3. Add **4 variations:**

   | Variation # | Value | Name | Description |
   |---|---|---|---|
   | 1 | `control` | Control | Default banner |
   | 2 | `upgrade-cta` | Upgrade CTA | Upgrade to Pro banner |
   | 3 | `enterprise-cta` | Enterprise CTA | Talk to Sales banner |
   | 4 | `internal-preview` | Internal Preview | New feature preview banner |

4. Set the **Default variation** (when targeting is OFF) to `control`
5. Under **Client-side SDK availability**, check **"SDKs using Client-side ID"**
6. Click **Save flag**

### Step 4: Configure Targeting Rules

Turn **Targeting ON** for the flag, then configure the following rules:

#### Individual Targeting

1. In the **Individual targets** section:
   - Click **+ Add individual targets**
   - For the `internal-preview` variation, add user key: `user-003`
   - This targets Carol specifically to see the preview banner

#### Rule-Based Targeting

2. Click **+ Add rule** to create Rule 1:
   - **IF** `plan` **is one of** `free`
   - **THEN** serve `upgrade-cta`
   - This targets all free plan users (Alice, Dave)

3. Click **+ Add rule** to create Rule 2:
   - **IF** `plan` **is one of** `enterprise`
   - **THEN** serve `enterprise-cta`
   - This targets enterprise users (Bob)

4. Set the **Default rule** to serve `control`
   - This catches everyone else (Eve)

5. Click **Review and save** > **Save changes**

Your targeting configuration should look like:

```
Individual targets:
  internal-preview → user-003

Rules:
  Rule 1: IF plan is one of [free] → serve upgrade-cta
  Rule 2: IF plan is one of [enterprise] → serve enterprise-cta

Default rule: serve control
```

### Step 5: Run the Application

```bash
python app.py
```

Open **http://localhost:5002** in your browser.

---

## Demo Walkthrough

### Demo 1: Default Experience (Eve)

1. Click the **"Eve Prospect"** button in the User Simulator
2. Eve is on the `pro` plan — no rules match
3. She sees the default **"Build Better Software"** banner (purple gradient)

### Demo 2: Rule-Based Targeting — Free Plan Users

1. Click **"Alice Engineer"** or **"Dave Visitor"**
2. Both are on the `free` plan → Rule 1 matches
3. They see the **"Upgrade to Pro — 50% Off"** banner (pink/red gradient)

### Demo 3: Rule-Based Targeting — Enterprise Users

1. Click **"Bob Manager"**
2. Bob is on the `enterprise` plan → Rule 2 matches
3. He sees the **"Your Enterprise Account is Growing"** banner (teal/green gradient)

### Demo 4: Individual Targeting

1. Click **"Carol Executive"**
2. Carol's user key (`user-003`) is individually targeted
3. She sees the **"AI-Powered Flag Suggestions"** banner (dark with red border)
4. Note: Even though Carol is on the `pro` plan (which would normally get "control"), individual targeting takes priority over rules

### What to Point Out

- **Individual targeting has highest priority** — Carol sees "internal-preview" even though no rule would match her plan
- **Rules are evaluated top-to-bottom** — first matching rule wins
- **Context attributes drive targeting** — the `plan` attribute determines which banner most users see
- **No page reload needed** — `client.identify()` switches context and re-evaluates flags instantly
- **Same code, different experiences** — all 5 users see the same page but different banners

---

## Project Structure

```
launchdarkly-target/
├── app.py              # Flask app with 5 pre-defined user contexts
├── requirements.txt    # Python dependencies
├── .env.example        # Template for SDK keys
├── .gitignore
├── templates/
│   └── index.html      # Landing page with hero banner + user simulator
├── static/
│   ├── css/
│   │   └── styles.css  # Banner variations + landing page styles
│   └── js/
│       └── app.js      # LD JS SDK with identify() for user switching
└── README.md           # This file
```

## Key Code Locations

| File | What to Look At |
|---|---|
| `app.py:55-107` | Pre-defined user contexts with targeting attributes |
| `app.py:118-139` | `build_context()` — creates LD context with custom attributes |
| `app.py:155-157` | Server-side flag evaluation with context |
| `static/js/app.js:56-67` | `buildContext()` — client-side context with custom attributes |
| `static/js/app.js:130-161` | `client.identify()` — switches user context for re-evaluation |
| `static/js/app.js:88-93` | `client.on("ready")` — initial flag evaluation |
| `static/js/app.js:100-111` | `client.on("change:")` — real-time targeting rule updates |

## Context Attributes Reference

| Attribute | Type | Values | Used For |
|---|---|---|---|
| `key` | String | `user-001` to `user-005` | Individual targeting |
| `name` | String | Full name | Display only |
| `email` | String | Email address | Individual targeting (optional) |
| `plan` | String | `free`, `pro`, `enterprise` | Rule-based targeting |
| `role` | String | `developer`, `manager`, `executive` | Rule-based targeting |
| `country` | String | `US`, `UK`, `IN`, `DE` | Geo-based targeting |
| `company` | String | Company name | Internal vs external targeting |

## Assumptions

- You have Python 3.8+ and pip installed
- You have a LaunchDarkly account (trial or paid)
- Port 5002 is available on your machine
- You have internet connectivity

## Troubleshooting

| Issue | Solution |
|---|---|
| Banner doesn't change when switching users | Check that targeting is ON and rules are configured correctly |
| All users see the same banner | Verify the "SDKs using Client-side ID" checkbox is checked |
| "control" shown for free plan users | Make sure Rule 1 uses the `plan` attribute (not `role` or `name`) |
| Carol sees "control" instead of "internal-preview" | Check that `user-003` is added in Individual targets for the `internal-preview` variation |

## Technologies Used

- **Python 3 / Flask** — Web server and server-side SDK host
- **LaunchDarkly Server-Side Python SDK** — Server-side flag evaluation with context
- **LaunchDarkly Client-Side JavaScript SDK** — Client-side targeting with `identify()`
- **LaunchDarkly Targeting** — Individual targets + rule-based targeting
