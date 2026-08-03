/* Dagric OS — the post-purchase page's download link.
 *
 * MOVED OUT OF thanks-pro.html SO THE SITE CAN SHIP A REAL CSP. See the note in
 * contact.js: with both scripts external, firebase.json can send
 * `script-src 'self'` with no 'unsafe-inline'. Do not move this back inline.
 *
 * Stripe returns the buyer here with ?session_id=cs_... The regex is the check
 * that matters: the value is interpolated into a URL the buyer is about to
 * follow, so anything that is not a Stripe checkout-session id is refused
 * rather than passed on. encodeURIComponent is belt and braces on top of it.
 *
 * The else branch is not an error path — it is the page being opened without a
 * session, which happens when somebody bookmarks it or arrives from history. It
 * says so and offers the purchase link rather than a broken download.
 */
(function () {
  var sid = new URLSearchParams(location.search).get("session_id");
  var a = document.getElementById("dl");
  if (sid && /^cs_[A-Za-z0-9_]+$/.test(sid)) {
    a.href = "https://dagric-gate.dagric.workers.dev/?session_id=" + encodeURIComponent(sid);
  } else {
    a.textContent = "Purchase Dagric OS Pro — $39";
    a.href = "https://buy.stripe.com/6oU5kwbye2Jogri31D8k809";
    document.getElementById("dlnote").textContent =
      "This page had no purchase session attached. If you already bought Pro, open the link from your receipt/checkout page; otherwise grab it below.";
  }
})();
