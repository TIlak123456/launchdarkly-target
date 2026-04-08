"""
ABC Company Landing Page — LaunchDarkly Targeting Demo (Part 2)

This Flask application demonstrates LaunchDarkly's targeting capabilities:

  1. FEATURE FLAG:
     A "hero-banner" multivariate string flag controls the hero CTA component
     on the landing page. Unlike Part 1's boolean flag, this is a STRING flag
     with 4 possible variations — each rendering a completely different banner.

  2. CONTEXT ATTRIBUTES:
     Users have rich context attributes (plan, role, country, company, email).
     These attributes are sent to LaunchDarkly and used to evaluate targeting
     rules. The more attributes you provide, the more granular your targeting
     can be.

  3. INDIVIDUAL TARGETING:
     Specific users (identified by their unique key) can be individually
     targeted to receive a specific variation, regardless of any rules.
     Example: Carol (user-003) is individually targeted to see "internal-preview".

  4. RULE-BASED TARGETING:
     Users matching attribute-based rules receive targeted variations.
     Example: All users with plan="free" see the "upgrade-cta" banner.

ARCHITECTURE:
  - Server-side (Python SDK): Evaluates the flag for the initial page render
  - Client-side (JS SDK): Handles user switching via identify() and real-time
    flag changes via streaming

FALLBACK STRATEGY:
  If LaunchDarkly is unavailable (SDK fails to initialize, network issues, etc.),
  the app gracefully degrades to the "control" variation — the default banner.
  This ensures the landing page always renders correctly, even without LD.
"""

import os
import json
import atexit
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import ldclient
from ldclient import Context
from ldclient.config import Config, HTTPConfig

# ---------------------------------------------------------------------------
# Load environment variables from .env file
# ---------------------------------------------------------------------------
# python-dotenv reads the .env file and sets environment variables.
# This keeps SDK keys out of source code (security best practice).
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration — LaunchDarkly SDK Keys
# ---------------------------------------------------------------------------
# These keys connect your app to a specific LaunchDarkly project + environment.
# REPLACE these with your actual keys, or set them in a .env file.
#
# SDK_KEY:    Server-side key (SECRET — never expose in browser code)
#             Found in: LD Dashboard > Settings > Projects > Environments > SDK key
#
# CLIENT_ID:  Client-side ID (SAFE to expose — designed for browser use)
#             Found in: LD Dashboard > Settings > Projects > Environments > Client-side ID
LAUNCHDARKLY_SDK_KEY = os.getenv("LAUNCHDARKLY_SDK_KEY", "sdk-your-server-side-sdk-key-here")
LAUNCHDARKLY_CLIENT_ID = os.getenv("LAUNCHDARKLY_CLIENT_ID", "your-client-side-id-here")

# ---------------------------------------------------------------------------
# Feature Flag Configuration
# ---------------------------------------------------------------------------
# The feature flag key — must EXACTLY match the flag you create in the LD dashboard.
#
# This is a MULTIVARIATE STRING flag with 4 variations:
#
#   Variation          | Description                    | Target
#   -------------------|--------------------------------|---------------------------
#   "control"          | Original banner (default)      | Everyone else (default rule)
#   "upgrade-cta"      | "Upgrade to Pro" banner        | Rule: plan = "free"
#   "enterprise-cta"   | "Talk to Sales" banner         | Rule: plan = "enterprise"
#   "internal-preview" | "New Feature Preview" banner   | Individual: user-003 (Carol)
#
# FALLBACK: If the flag doesn't exist, SDK isn't initialized, or LD is
# unreachable, the fallback value "control" is used (see variation() calls below).
HERO_BANNER_FLAG_KEY = "hero-banner"

# ---------------------------------------------------------------------------
# Pre-Defined User Contexts
# ---------------------------------------------------------------------------
# These represent different types of visitors to the ABC Company landing page.
# Each user has rich context attributes that LaunchDarkly uses for targeting.
#
# In a real application, these attributes would come from your authentication
# system, user database, or session data. For this demo, we define them
# statically so you can switch between users to see targeting in action.
#
# TARGETING ATTRIBUTE REFERENCE:
#   Attribute   | Used For                        | Example Rule
#   ------------|--------------------------------|----------------------------------
#   key         | Individual targeting            | Target user-003 specifically
#   email       | Individual targeting (optional) | Target alice@abccompany.com
#   plan        | Rule-based targeting            | IF plan = "free" THEN upgrade-cta
#   role        | Rule-based targeting            | IF role = "executive" THEN ...
#   country     | Geo-based targeting             | IF country = "US" THEN ...
#   company     | Internal vs external targeting  | IF company = "ABC Company" THEN ...
USERS = {
    # -----------------------------------------------------------------------
    # ALICE — Free plan user (Rule-based target: plan = "free")
    # Expected variation: "upgrade-cta"
    # Why: Matches Rule 1 (IF plan is one of [free] THEN serve upgrade-cta)
    # -----------------------------------------------------------------------
    "alice": {
        "key": "user-001",          # Unique identifier for this user
        "name": "Alice Engineer",    # Display name
        "email": "alice@abccompany.com",
        "plan": "free",              # <-- KEY ATTRIBUTE: triggers Rule 1
        "role": "developer",
        "country": "US",
        "company": "ABC Company",
        "description": "Internal developer on free plan — should see 'Upgrade to Pro' via rule-based targeting"
    },

    # -----------------------------------------------------------------------
    # BOB — Enterprise user (Rule-based target: plan = "enterprise")
    # Expected variation: "enterprise-cta"
    # Why: Matches Rule 2 (IF plan is one of [enterprise] THEN serve enterprise-cta)
    # -----------------------------------------------------------------------
    "bob": {
        "key": "user-002",
        "name": "Bob Manager",
        "email": "bob@megacorp.com",
        "plan": "enterprise",        # <-- KEY ATTRIBUTE: triggers Rule 2
        "role": "manager",
        "country": "UK",
        "company": "MegaCorp",
        "description": "Enterprise customer — should see 'Talk to Sales' via rule-based targeting"
    },

    # -----------------------------------------------------------------------
    # CAROL — Individually targeted user
    # Expected variation: "internal-preview"
    # Why: Her user key "user-003" is individually targeted in the LD dashboard.
    #      Individual targets are evaluated BEFORE rules, so even though Carol
    #      is on the "pro" plan (which would normally get "control"), she gets
    #      "internal-preview" because individual targeting has highest priority.
    # -----------------------------------------------------------------------
    "carol": {
        "key": "user-003",          # <-- THIS KEY is individually targeted
        "name": "Carol Executive",
        "email": "carol@abccompany.com",
        "plan": "pro",              # Would normally get "control" (default)
        "role": "executive",
        "country": "US",
        "company": "ABC Company",
        "description": "Internal executive on pro plan — individually targeted to see 'New Feature Preview'"
    },

    # -----------------------------------------------------------------------
    # DAVE — Another free plan user (Rule-based target: plan = "free")
    # Expected variation: "upgrade-cta"
    # Why: Same as Alice — matches Rule 1 (plan = "free")
    #      Shows that rules apply to ALL matching users, not just one.
    # -----------------------------------------------------------------------
    "dave": {
        "key": "user-004",
        "name": "Dave Visitor",
        "email": "dave@startup.io",
        "plan": "free",              # <-- KEY ATTRIBUTE: triggers Rule 1
        "role": "developer",
        "country": "IN",
        "company": "StartupIO",
        "description": "External free user — should see 'Upgrade to Pro' via rule-based targeting"
    },

    # -----------------------------------------------------------------------
    # EVE — Pro plan user, no special targeting
    # Expected variation: "control" (default)
    # Why: No individual target matches, no rules match (plan="pro" has no rule).
    #      Falls through to the Default Rule, which serves "control".
    # -----------------------------------------------------------------------
    "eve": {
        "key": "user-005",
        "name": "Eve Prospect",
        "email": "eve@bigbank.com",
        "plan": "pro",              # No rule targets "pro" — gets default
        "role": "manager",
        "country": "DE",
        "company": "BigBank",
        "description": "Pro plan user, no special targeting — should see the default 'control' banner"
    },
}

# ---------------------------------------------------------------------------
# Initialize LaunchDarkly Server-Side SDK
# ---------------------------------------------------------------------------
# The server-side SDK connects to LaunchDarkly's streaming API, downloads
# the complete flag ruleset, and caches it in memory. All flag evaluations
# happen locally (no network call per evaluation), making them extremely fast.
#
# NOTE: disable_ssl_verification=True is used here to bypass SSL certificate
# errors caused by corporate proxies/firewalls that use self-signed certificates.
# This is acceptable for a demo/development environment.
# WARNING: Do NOT use disable_ssl_verification=True in production — it disables
# certificate validation, making connections vulnerable to MITM attacks.
# Production fix: Install the corporate CA cert or set REQUESTS_CA_BUNDLE.
ldclient.set_config(Config(
    LAUNCHDARKLY_SDK_KEY,
    http=HTTPConfig(disable_ssl_verification=True),
))
ld_client = ldclient.get()

# Check if the SDK connected successfully.
# If initialization fails (bad key, network issues), the SDK will return
# FALLBACK VALUES for all flag evaluations — the app still works, just
# without personalized targeting.
if ld_client.is_initialized():
    print("[LaunchDarkly] Server-side SDK initialized successfully.")
    print("[LaunchDarkly] Flag evaluations will use live targeting rules.")
else:
    print("[LaunchDarkly] WARNING: Server-side SDK failed to initialize.")
    print("[LaunchDarkly] All flag evaluations will return the FALLBACK value 'control'.")
    print("[LaunchDarkly] Check your LAUNCHDARKLY_SDK_KEY in the .env file.")

# ---------------------------------------------------------------------------
# Flask Application
# ---------------------------------------------------------------------------
app = Flask(__name__)


def build_context(user_data):
    """
    Build a LaunchDarkly Context from user data.

    A Context represents the entity being evaluated. It contains attributes
    that LaunchDarkly's targeting engine uses to determine which flag variation
    to serve. The more attributes you include, the more granular your
    targeting rules can be.

    Context attributes used for targeting:
      - key:     Unique user identifier (REQUIRED) — used for individual targeting
      - name:    Display name — used for the LD dashboard UI
      - email:   Email address — can be used for individual targeting
      - plan:    Subscription plan — used in Rule 1 (free → upgrade-cta)
                 and Rule 2 (enterprise → enterprise-cta)
      - role:    User role — available for role-based targeting rules
      - country: Country code — available for geo-based targeting rules
      - company: Company name — available for company-based targeting rules

    Args:
        user_data (dict): User attributes from the USERS dictionary

    Returns:
        ldclient.Context: A LaunchDarkly context object ready for flag evaluation
    """
    return Context.builder(user_data["key"]) \
        .kind("user") \
        .name(user_data["name"]) \
        .set("email", user_data["email"]) \
        .set("plan", user_data["plan"]) \
        .set("role", user_data["role"]) \
        .set("country", user_data["country"]) \
        .set("company", user_data["company"]) \
        .build()


@app.route("/")
def index():
    """
    Landing page with hero banner controlled by the 'hero-banner' flag.

    The selected user (default: "alice") determines which banner variation
    is served, based on the targeting rules configured in LaunchDarkly.

    EVALUATION ORDER (first match wins):
      1. Individual targets — e.g., user-003 (Carol) → "internal-preview"
      2. Rule 1 — IF plan = "free" → "upgrade-cta"
      3. Rule 2 — IF plan = "enterprise" → "enterprise-cta"
      4. Default rule → "control"

    FALLBACK BEHAVIOR:
      If the SDK is not initialized or LD is unreachable, ld_client.variation()
      returns the fallback value "control" (the third argument). This ensures
      the page always renders with the default banner — no errors, no blank page.
    """
    # Get the selected user from query params (default: alice)
    selected_user_id = request.args.get("user", "alice")
    if selected_user_id not in USERS:
        selected_user_id = "alice"

    selected_user = USERS[selected_user_id]

    # Build the LaunchDarkly context with all user attributes.
    # These attributes are sent to LD and matched against targeting rules.
    context = build_context(selected_user)

    # ===================================================================
    # FLAG EVALUATION — Server-Side
    # ===================================================================
    # ld_client.variation() evaluates the flag for the given context.
    #
    # Arguments:
    #   1. HERO_BANNER_FLAG_KEY  — the flag key ("hero-banner")
    #   2. context               — the user context with targeting attributes
    #   3. "control"             — FALLBACK VALUE (used when LD is unavailable)
    #
    # FALLBACK SCENARIO:
    #   If the SDK failed to initialize, the flag doesn't exist, or LD is
    #   unreachable, this call returns "control" — the safe default that
    #   shows the original banner. The app NEVER crashes due to LD issues.
    # ===================================================================
    banner_variation = ld_client.variation(HERO_BANNER_FLAG_KEY, context, "control")

    return render_template(
        "index.html",
        banner_variation=banner_variation,     # The variation to render (e.g., "upgrade-cta")
        selected_user=selected_user,           # Current user's data for the info panel
        selected_user_id=selected_user_id,     # Current user's ID for button highlighting
        users=USERS,                           # All users for the user selector buttons
        users_json=json.dumps(USERS),          # Users as JSON for the JS SDK
        client_side_id=LAUNCHDARKLY_CLIENT_ID, # Client-side ID for the JS SDK
        flag_key=HERO_BANNER_FLAG_KEY,         # Flag key for display in the info panel
    )


@app.route("/api/evaluate", methods=["POST"])
def evaluate_flag():
    """
    API endpoint for server-side flag evaluation.

    Called by the frontend when switching users to get the server-side
    evaluation result for comparison with the client-side SDK.

    FALLBACK: Returns "control" if user is unknown or LD is unavailable.
    """
    data = request.get_json()
    user_id = data.get("user_id", "alice")

    if user_id not in USERS:
        return jsonify({"error": "Unknown user"}), 400

    user_data = USERS[user_id]
    context = build_context(user_data)

    # FALLBACK: Third argument "control" is returned if LD is unavailable
    banner_variation = ld_client.variation(HERO_BANNER_FLAG_KEY, context, "control")

    return jsonify({
        "variation": banner_variation,
        "user": user_data,
        "source": "server-side (Python SDK)"
    })


@app.route("/health")
def health():
    """
    Health check endpoint.

    Useful for verifying the SDK is connected. Returns the initialization
    status so you can confirm LD is working before demoing.
    """
    return jsonify({
        "status": "ok",
        "launchdarkly_initialized": ld_client.is_initialized(),
    })


# ---------------------------------------------------------------------------
# Cleanup — Graceful Shutdown
# ---------------------------------------------------------------------------
# When the app stops (Ctrl+C, kill signal, etc.), we flush any pending
# analytics events and close the streaming connection to LaunchDarkly.
# Without this, pending events may be lost.
def cleanup():
    print("[LaunchDarkly] Shutting down server-side SDK...")
    print("[LaunchDarkly] Flushing pending analytics events...")
    ld_client.close()


atexit.register(cleanup)

# ---------------------------------------------------------------------------
# Run the app
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  ABC Company Landing Page — LaunchDarkly Targeting Demo")
    print("  Open http://localhost:6001 in your browser")
    print("=" * 60 + "\n")
    app.run(debug=True, port=6001)
