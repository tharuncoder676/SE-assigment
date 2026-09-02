/* SmartCare single-page client.
   Talks only to the documented REST API; the access token is held in memory
   and in sessionStorage so that it is cleared when the tab is closed. */

const state = { token: null, user: null, doctor: null, slot: null, doctors: [] };

/* ------------------------------------------------------------------ api */
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const res = await fetch(path, { ...options, headers });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error((body && body.detail) || ("HTTP " + res.status));
  return body;
}

function toast(message, kind = "") {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = "toast " + kind;
  setTimeout(() => el.classList.add("hidden"), 3200);
}

const fmt = (iso) => new Date(iso).toLocaleString("en-GB",
  { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false });

/* ----------------------------------------------------------------- auth */
document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const login = tab.dataset.tab === "login";
    document.getElementById("loginForm").classList.toggle("hidden", !login);
    document.getElementById("registerForm").classList.toggle("hidden", login);
  };
});

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

document.getElementById("loginForm").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const data = await api("/api/v1/auth/login", {
      method: "POST", body: JSON.stringify(formData(e.target)),
    });
    startSession(data);
  } catch (err) { toast(err.message, "err"); }
};

document.getElementById("registerForm").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const data = await api("/api/v1/auth/register", {
      method: "POST", body: JSON.stringify(formData(e.target)),
    });
    toast("Account created. Welcome, " + data.full_name, "ok");
    startSession(data);
  } catch (err) { toast(err.message, "err"); }
};

function startSession(data) {
  state.token = data.access_token;
  state.user = data.full_name;
  sessionStorage.setItem("smartcare_token", data.access_token);
  sessionStorage.setItem("smartcare_user", data.full_name);
  document.getElementById("who").textContent = "Signed in as " + data.full_name;
  document.getElementById("who").classList.remove("hidden");
  document.getElementById("logoutBtn").classList.remove("hidden");
  document.getElementById("authView").classList.add("hidden");
  document.getElementById("appView").classList.remove("hidden");
  loadSpecialities();
  loadDoctors();
  loadNotifications();
}

document.getElementById("logoutBtn").onclick = () => {
  sessionStorage.clear();
  location.reload();
};

/* ------------------------------------------------------------ navigation */
document.querySelectorAll(".navtab").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll(".navtab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    ["book", "mine", "alerts"].forEach((v) =>
      document.getElementById(v + "View").classList.toggle("hidden", v !== tab.dataset.view));
    if (tab.dataset.view === "mine") loadAppointments();
    if (tab.dataset.view === "alerts") loadNotifications();
  };
});

/* --------------------------------------------------------------- doctors */
async function loadSpecialities() {
  const list = await api("/api/v1/doctors/specialities");
  const select = document.getElementById("speciality");
  list.forEach((s) => select.add(new Option(s, s)));
}

async function loadDoctors() {
  const speciality = document.getElementById("speciality").value;
  const q = document.getElementById("search").value.trim();
  const params = new URLSearchParams();
  if (speciality) params.set("speciality", speciality);
  if (q) params.set("q", q);
  state.doctors = await api("/api/v1/doctors?" + params.toString());

  const box = document.getElementById("doctors");
  box.innerHTML = "";
  if (!state.doctors.length) {
    box.innerHTML = '<p class="muted">No doctors match the selected filters.</p>';
    return;
  }
  state.doctors.forEach((d) => {
    const card = document.createElement("div");
    card.className = "doctor";
    card.innerHTML = `<h3>${d.name}</h3><span class="spec">${d.speciality}</span>
      <div class="meta">${d.qualification}<br>${d.department} &middot; Fee &#8377;${d.consultation_fee}</div>`;
    card.onclick = () => selectDoctor(d, card);
    box.appendChild(card);
  });
}

document.getElementById("speciality").onchange = loadDoctors;
document.getElementById("search").oninput = () => {
  clearTimeout(window._t);
  window._t = setTimeout(loadDoctors, 250);
};

/* ----------------------------------------------------------------- slots */
async function selectDoctor(doctor, card) {
  document.querySelectorAll(".doctor").forEach((c) => c.classList.remove("selected"));
  card.classList.add("selected");
  state.doctor = doctor;
  state.slot = null;
  document.getElementById("confirmCard").classList.add("hidden");

  const slots = await api(`/api/v1/doctors/${doctor.id}/slots`);
  document.getElementById("slotFor").textContent =
    `${slots.length} free slots for ${doctor.name} (${doctor.speciality})`;
  const box = document.getElementById("slots");
  box.innerHTML = "";
  slots.slice(0, 24).forEach((s) => {
    const el = document.createElement("div");
    el.className = "slot";
    const d = new Date(s.start_at);
    el.innerHTML = `<span class="d">${d.toLocaleDateString("en-GB",
      { day: "2-digit", month: "short" })}</span>
      ${d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
    el.onclick = () => selectSlot(s, el);
    box.appendChild(el);
  });
  document.getElementById("slotCard").classList.remove("hidden");
}

function selectSlot(slot, el) {
  document.querySelectorAll(".slot").forEach((s) => s.classList.remove("selected"));
  el.classList.add("selected");
  state.slot = slot;
  document.getElementById("confirmText").textContent =
    `${state.doctor.name} (${state.doctor.speciality}) on ${fmt(slot.start_at)} ` +
    `— consultation fee ₹${state.doctor.consultation_fee}`;
  document.getElementById("confirmCard").classList.remove("hidden");
}

document.getElementById("confirmBtn").onclick = async () => {
  if (!state.slot) return;
  try {
    const res = await api("/api/v1/appointments", {
      method: "POST",
      body: JSON.stringify({
        slot_id: state.slot.id,
        reason: document.getElementById("reason").value,
      }),
    });
    toast("Appointment confirmed — reference " + res.reference, "ok");
    document.getElementById("confirmCard").classList.add("hidden");
    document.getElementById("slotCard").classList.add("hidden");
    setTimeout(loadNotifications, 400);
  } catch (err) { toast(err.message, "err"); }
};

/* ---------------------------------------------------------- appointments */
async function loadAppointments() {
  const rows = await api("/api/v1/appointments");
  const body = document.getElementById("apptRows");
  body.innerHTML = "";
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="6" class="muted">No appointments booked yet.</td></tr>';
    return;
  }
  rows.forEach((a) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><code>${a.reference}</code></td><td>${a.doctor_name}</td>
      <td>${a.speciality}</td><td>${fmt(a.start_at)}</td>
      <td><span class="pill ${a.status}">${a.status}</span></td><td></td>`;
    if (a.status === "CONFIRMED") {
      const btn = document.createElement("button");
      btn.className = "btn small danger";
      btn.textContent = "Cancel";
      btn.onclick = async () => {
        try {
          await api("/api/v1/appointments/" + a.reference, { method: "DELETE" });
          toast("Appointment cancelled", "ok");
          loadAppointments();
        } catch (err) { toast(err.message, "err"); }
      };
      tr.lastElementChild.appendChild(btn);
    }
    body.appendChild(tr);
  });
}

/* --------------------------------------------------------- notifications */
async function loadNotifications() {
  const rows = await api("/api/v1/notifications");
  const unread = rows.filter((n) => !n.is_read).length;
  const badge = document.getElementById("badge");
  badge.textContent = unread;
  badge.classList.toggle("hidden", unread === 0);

  const box = document.getElementById("alerts");
  box.innerHTML = "";
  if (!rows.length) {
    box.innerHTML = '<p class="muted">No notifications yet.</p>';
    return;
  }
  rows.forEach((n) => {
    const el = document.createElement("div");
    el.className = "alert" + (n.is_read ? " read" : "");
    el.innerHTML = `<b>${n.subject}</b><p>${n.body}</p>
      <time>${fmt(n.created_at)} &middot; channel: ${n.channel}</time>`;
    el.onclick = async () => {
      if (n.is_read) return;
      await api(`/api/v1/notifications/${n.id}/read`, { method: "POST" });
      loadNotifications();
    };
    box.appendChild(el);
  });
}

/* --------------------------------------------------------------- restore */
if (sessionStorage.getItem("smartcare_token")) {
  startSession({
    access_token: sessionStorage.getItem("smartcare_token"),
    full_name: sessionStorage.getItem("smartcare_user"),
  });
}
