/* Dagric OS — the contact form.
 *
 * MOVED OUT OF contact.html SO THE SITE CAN SHIP A REAL CSP. With this and
 * thanks-pro.js external, every script on the site is same-origin, which lets
 * firebase.json send `script-src 'self'` with NO 'unsafe-inline'. Left inline,
 * the only workable policy would have been script-src 'unsafe-inline', which
 * permits exactly the injection a CSP exists to stop and is barely worth
 * sending. Do not move this back into the page.
 *
 * The worker it posts to is dagric-contact.dagric.workers.dev, and its CORS
 * allow-list must contain the origin the visitor is actually on. That list was
 * missing dagric.com — the domain /etc/os-release, the motd, the Calamares
 * branding and the Hub's Support button all point at — so this fetch was
 * blocked by the browser and every support and refund message sent from the
 * production domain was silently lost. The fix is committed in
 * infra/contact-worker.js and takes effect only once that worker is redeployed.
 */
document.getElementById("cform").addEventListener("submit", async function (e) {
  e.preventDefault();
  var f = e.target, s = document.getElementById("status"), b = document.getElementById("send");
  var msg = f.message.value.trim();
  if (msg.length < 10) { s.className = "err"; s.textContent = "Please write a little more so we can help."; return; }
  b.disabled = true; s.className = ""; s.textContent = "Sending…";
  try {
    var r = await fetch("https://dagric-contact.dagric.workers.dev/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: f.topic.value, name: f.name.value, email: f.email.value,
        message: msg, website: f.website.value
      })
    });
    var j = await r.json();
    if (j.ok) { s.className = "ok"; s.textContent = "Sent — thank you. If you left an email, we'll reply there."; f.reset(); }
    else { s.className = "err"; s.textContent = j.error || "Something went wrong — please try again."; }
  } catch (err) {
    s.className = "err"; s.textContent = "Couldn't reach the server — check your connection and try again.";
  }
  b.disabled = false;
});
