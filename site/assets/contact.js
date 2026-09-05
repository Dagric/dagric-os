
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
