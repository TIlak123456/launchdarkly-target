/**
 * =============================================================================
 * ABC Company Landing Page — LaunchDarkly Targeting Demo (Part 2)
 * =============================================================================
 *
 * This script handles the client-side LaunchDarkly integration for the
 * targeting demo. It manages:
 *
 *   1. SDK INITIALIZATION
 *      Connects to LaunchDarkly with the default user's context attributes.
 *      The SDK opens a streaming connection for real-time flag updates.
 *
 *   2. USER SWITCHING (identify)
 *      When a user button is clicked, calls client.identify() to switch the
 *      SDK to a new user context. LaunchDarkly re-evaluates the flag based
 *      on the new user's attributes and targeting rules.
 *
 *   3. BANNER UPDATE
 *      Updates the hero banner component by swapping CSS classes based on
 *      the flag variation returned for the current user.
 *
 *   4. CONTEXT DISPLAY
 *      Shows the current user's attributes and flag evaluation result in
 *      the info panel for transparency during the demo.
 *
 * KEY LAUNCHDARKLY CONCEPTS DEMONSTRATED:
 *   - Context Attributes: Each user has plan, role, country, company, email
 *   - Individual Targeting: Specific user keys → specific variations
 *   - Rule-Based Targeting: Attribute rules (e.g., plan=free) → variations
 *   - identify(): SDK method to switch user contexts at runtime
 *
 * FALLBACK STRATEGY:
 *   Every call to client.variation() includes a fallback value of "control".
 *   If LaunchDarkly is unreachable, the SDK is not initialized, or the flag
 *   doesn't exist, the app gracefully shows the default "control" banner.
 *   The app NEVER breaks due to LaunchDarkly issues.
 */

(function () {
  "use strict";

  // ===========================================================================
  // CONFIGURATION
  // ===========================================================================
  // These values are injected by the Flask template engine (see index.html).
  // They bridge the server-side and client-side LaunchDarkly integrations.
  var CLIENT_SIDE_ID = window.__LD_CLIENT_SIDE_ID__;   // LD client-side ID (safe to expose in browser)
  var FLAG_KEY = window.__LD_FLAG_KEY__;               // Flag key: "hero-banner"
  var INITIAL_VARIATION = window.__LD_INITIAL_VARIATION__; // Server-side evaluated variation
  var SELECTED_USER_ID = window.__LD_SELECTED_USER_ID__;   // Currently selected user ID
  var USERS = window.__LD_USERS__;                     // All pre-defined users with attributes

  // ===========================================================================
  // DOM ELEMENT REFERENCES
  // ===========================================================================

  // Hero banner container — CSS class determines which variation is visible
  var heroBanner = document.getElementById("hero-banner");

  // Flag evaluation display elements
  var flagVariationEl = document.getElementById("flag-variation");
  var flagSourceEl = document.getElementById("flag-source");
  var flagReasonEl = document.getElementById("flag-reason");
  var explanationTextEl = document.getElementById("explanation-text");

  // User selector buttons
  var userButtons = document.querySelectorAll(".user-btn");

  // Context attribute display elements
  var ctxKey = document.getElementById("ctx-key");
  var ctxName = document.getElementById("ctx-name");
  var ctxEmail = document.getElementById("ctx-email");
  var ctxPlan = document.getElementById("ctx-plan");
  var ctxRole = document.getElementById("ctx-role");
  var ctxCountry = document.getElementById("ctx-country");
  var ctxCompany = document.getElementById("ctx-company");

  // ===========================================================================
  // BUILD LAUNCHDARKLY CONTEXT
  // ===========================================================================
  /**
   * Builds a LaunchDarkly context object from user data.
   *
   * The context contains attributes that LD's targeting engine evaluates
   * against your configured rules. Each attribute can be used in rules:
   *
   *   Attribute | Example Rule
   *   ----------|--------------------------------------------------
   *   key       | Individual target: user-003 → internal-preview
   *   plan      | Rule: IF plan is one of [free] → upgrade-cta
   *   role      | Rule: IF role is one of [executive] → ...
   *   country   | Rule: IF country is one of [US, UK] → ...
   *   company   | Rule: IF company is "ABC Company" → ...
   *
   * @param {Object} userData - User object from the USERS dictionary
   * @returns {Object} LaunchDarkly context object
   */
  function buildContext(userData) {
    return {
      kind: "user",              // Context kind — "user" is the most common
      key: userData.key,          // REQUIRED: Unique identifier for this user
      name: userData.name,        // Display name (shown in LD dashboard)
      email: userData.email,      // Email — can be used for individual targeting

      // Custom attributes — these are the core of rule-based targeting.
      // Any attribute you include here can be used in targeting rules
      // configured in the LaunchDarkly dashboard.
      plan: userData.plan,        // "free", "pro", "enterprise" — drives Rule 1 & 2
      role: userData.role,        // "developer", "manager", "executive"
      country: userData.country,  // "US", "UK", "IN", "DE" — for geo targeting
      company: userData.company,  // Company name — for internal vs external
    };
  }

  // ===========================================================================
  // INITIALIZE THE LAUNCHDARKLY CLIENT-SIDE SDK
  // ===========================================================================
  // The SDK connects to LaunchDarkly using:
  //   1. CLIENT_SIDE_ID — identifies your LD project + environment
  //   2. context — the current user's attributes for flag evaluation
  //   3. options — streaming: true enables real-time flag updates via SSE
  //
  // IMPORTANT: The client-side ID is NOT a secret. It's designed to be
  // embedded in browser code. The server-side SDK key should NEVER be here.
  var currentUser = USERS[SELECTED_USER_ID];
  var context = buildContext(currentUser);

  var client = LDClient.initialize(CLIENT_SIDE_ID, context, {
    // Enable streaming (Server-Sent Events) for real-time flag updates.
    // When targeting rules are changed in the LD dashboard, the SDK
    // receives the update immediately — no polling delay.
    streaming: true,
  });

  // ===========================================================================
  // SDK READY EVENT — Initial Flag Evaluation
  // ===========================================================================
  // The "ready" event fires once the SDK has connected to LaunchDarkly and
  // received the initial flag values for the current user context.
  client.on("ready", function () {
    console.log("[LaunchDarkly] Client-side SDK ready and connected.");

    // =========================================================================
    // FLAG EVALUATION WITH FALLBACK
    // =========================================================================
    // client.variation() evaluates the flag for the current user context.
    //
    // Arguments:
    //   1. FLAG_KEY   — the flag key ("hero-banner")
    //   2. "control"  — FALLBACK VALUE
    //
    // FALLBACK SCENARIO:
    //   The second argument "control" is the FALLBACK value. It is returned when:
    //   - The SDK hasn't finished initializing
    //   - The flag doesn't exist in LaunchDarkly
    //   - The flag isn't enabled for client-side SDKs (missing checkbox)
    //   - LaunchDarkly is unreachable and there's no cached value
    //
    //   This ensures the app ALWAYS shows the default banner — never crashes
    //   or shows a blank page due to LaunchDarkly issues.
    // =========================================================================
    var variation = client.variation(FLAG_KEY, "control");
    updateBanner(variation);
    updateFlagDisplay(variation, "Client-side (JS SDK)", "SDK initialized");

    console.log(
      '[LaunchDarkly] "' + FLAG_KEY + '" = "' + variation + '" for user: ' + currentUser.name
    );
  });

  // ===========================================================================
  // REAL-TIME FLAG CHANGE LISTENER
  // ===========================================================================
  // If you change the targeting rules in the LD dashboard while the page is
  // open, the SDK receives the update via streaming and fires this event.
  // The banner updates automatically — no page reload needed.
  //
  // This also works when a flag trigger fires (Part 1 remediation concept).
  client.on("change:" + FLAG_KEY, function () {
    // FALLBACK: "control" is used if the evaluation fails for any reason
    var newVariation = client.variation(FLAG_KEY, "control");

    console.log(
      '[LaunchDarkly] Flag "' + FLAG_KEY + '" changed to "' + newVariation + '" — updating banner.'
    );

    updateBanner(newVariation);
    updateFlagDisplay(
      newVariation,
      "Real-time stream (JS SDK)",
      "Flag targeting rules changed at " + new Date().toLocaleTimeString()
    );
  });

  // ===========================================================================
  // SDK FAILURE HANDLER
  // ===========================================================================
  // If the SDK fails to initialize (bad client-side ID, network error, etc.),
  // the app still works — it just uses the FALLBACK value "control" for all
  // flag evaluations, showing the default banner to all users.
  client.on("failed", function () {
    console.error(
      "[LaunchDarkly] Client-side SDK FAILED to initialize. " +
      "All flag evaluations will return the FALLBACK value 'control'. " +
      "Check your LAUNCHDARKLY_CLIENT_ID."
    );

    // Show the default banner as fallback
    updateBanner("control");
    updateFlagDisplay(
      "control (FALLBACK)",
      "FALLBACK — SDK failed to initialize",
      "LaunchDarkly is unavailable. Showing default banner."
    );
  });

  // ===========================================================================
  // USER SWITCHING — client.identify()
  // ===========================================================================
  // This is the CORE of the targeting demo.
  //
  // When a user button is clicked, we call client.identify() to switch the
  // SDK to a new user context. This tells LaunchDarkly:
  //   "Stop evaluating flags for the old user. Evaluate for THIS new user."
  //
  // LaunchDarkly's targeting engine then:
  //   1. Checks individual targets — does this user's key match any?
  //   2. Checks rules top-to-bottom — do this user's attributes match any rule?
  //   3. Falls through to the default rule if nothing matches
  //
  // EXPECTED RESULTS:
  //   Alice  (plan=free)       → "upgrade-cta"      (matches Rule 1)
  //   Bob    (plan=enterprise) → "enterprise-cta"    (matches Rule 2)
  //   Carol  (key=user-003)    → "internal-preview"  (individual target — HIGHEST priority)
  //   Dave   (plan=free)       → "upgrade-cta"      (matches Rule 1)
  //   Eve    (plan=pro)        → "control"           (no match — default rule)
  userButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var userId = this.getAttribute("data-user-id");

      // Guard: ignore if user doesn't exist in our data
      if (!USERS[userId]) return;

      // Update active button styling (visual feedback)
      userButtons.forEach(function (b) {
        b.classList.remove("active");
      });
      this.classList.add("active");

      // Get the new user data and update tracking variable
      currentUser = USERS[userId];
      SELECTED_USER_ID = userId;

      // Build new LaunchDarkly context with the user's targeting attributes
      var newContext = buildContext(currentUser);

      console.log(
        "[LaunchDarkly] Switching to user: " +
          currentUser.name +
          " (key=" + currentUser.key +
          ", plan=" + currentUser.plan +
          ", role=" + currentUser.role + ")"
      );

      // Update the context display panel immediately (before LD responds)
      updateContextDisplay(currentUser);

      // =====================================================================
      // client.identify() — Switch User Context
      // =====================================================================
      // This is the key LaunchDarkly method for targeting demos.
      //
      // What happens when identify() is called:
      //   1. SDK sends the new context to LaunchDarkly
      //   2. LD evaluates ALL flags for the new user's attributes
      //   3. LD returns the evaluated flag values
      //   4. SDK updates its internal cache
      //   5. The Promise resolves and we can call variation()
      //
      // After identify(), calling variation() returns the flag value
      // evaluated specifically for the new user — with their plan, role,
      // country, etc. applied against all targeting rules.
      // =====================================================================
      client
        .identify(newContext)
        .then(function () {
          // Evaluate the flag for the new user context
          // FALLBACK: "control" if anything goes wrong
          var variation = client.variation(FLAG_KEY, "control");

          console.log(
            '[LaunchDarkly] After identify: "' +
              FLAG_KEY + '" = "' + variation + '" for ' + currentUser.name
          );

          // Update the UI with the new variation
          updateBanner(variation);
          updateFlagDisplay(
            variation,
            "Client-side identify() (JS SDK)",
            "User switched to " + currentUser.name
          );
        })
        .catch(function (err) {
          // =====================================================================
          // FALLBACK: identify() failed
          // =====================================================================
          // If identify() fails (network error, LD outage, etc.), we fall back
          // to the "control" variation. The app continues to work — the user
          // just sees the default banner instead of a targeted one.
          // =====================================================================
          console.error("[LaunchDarkly] identify() failed:", err);
          console.warn("[LaunchDarkly] Falling back to 'control' variation.");

          updateBanner("control");
          updateFlagDisplay(
            "control (FALLBACK)",
            "FALLBACK — identify() failed",
            "Could not evaluate targeting for " + currentUser.name
          );
        });
    });
  });

  // ===========================================================================
  // UI UPDATE FUNCTIONS
  // ===========================================================================

  /**
   * Update the hero banner to show the correct variation.
   *
   * How it works:
   *   1. Remove all variation-specific CSS classes from the banner
   *   2. Add the new variation's CSS class (e.g., "hero-upgrade-cta")
   *   3. CSS rules show/hide the correct banner-content div and apply
   *      the correct gradient background
   *
   * Each variation has its own distinct visual style:
   *   "control"          → Purple gradient
   *   "upgrade-cta"      → Pink/red gradient + "Limited Time Offer" badge
   *   "enterprise-cta"   → Teal/green gradient
   *   "internal-preview"  → Dark gradient + red border + "Internal Preview" badge
   *
   * @param {string} variation - The flag variation to display
   */
  function updateBanner(variation) {
    // Reset to base class (removes any previous variation class)
    heroBanner.className = "hero-banner";
    // Apply the new variation's CSS class
    heroBanner.classList.add("hero-" + variation);
  }

  /**
   * Update the context details panel to show the current user's attributes.
   * This helps the demo audience understand WHY a particular variation was served.
   *
   * @param {Object} user - The current user's data object
   */
  function updateContextDisplay(user) {
    ctxKey.textContent = user.key;
    ctxName.textContent = user.name;
    ctxEmail.textContent = user.email;
    ctxPlan.textContent = user.plan;
    ctxRole.textContent = user.role;
    ctxCountry.textContent = user.country;
    ctxCompany.textContent = user.company;
  }

  /**
   * Update the flag evaluation display panel.
   * Shows the current variation, which SDK evaluated it, and why.
   *
   * @param {string} variation - The flag variation value
   * @param {string} source - Which SDK provided this value (server/client/fallback)
   * @param {string} reason - Human-readable explanation of why this variation was served
   */
  function updateFlagDisplay(variation, source, reason) {
    flagVariationEl.textContent = variation;
    flagSourceEl.textContent = source;
    flagReasonEl.textContent = reason;
    explanationTextEl.textContent = currentUser.description;
  }
})();
