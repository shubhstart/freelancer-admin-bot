/* Freelancer Admin Chatbot — Frontend Logic */

const chatArea = document.getElementById("chat-area");
const input    = document.getElementById("msg-input");
const sendBtn  = document.getElementById("send-btn");

const SESSION_ID = crypto.randomUUID();

// ── Helpers ──────────────────────────────────────────────────────────

function escapeHTML(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

/** Very small markdown → HTML (bold, italic, tables, line breaks) */
function miniMarkdown(md) {
  let html = md
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");

  // Detect markdown tables
  const lines = html.split("\n");
  let out = [], inTable = false;
  for (const ln of lines) {
    const trimmed = ln.trim();
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      if (/^\|[\s\-:|]+\|$/.test(trimmed)) continue; // separator row
      const cells = trimmed.slice(1, -1).split("|").map(c => c.trim());
      if (!inTable) { out.push("<table>"); inTable = true; }
      const tag = inTable && out.filter(x => x.includes("<tr>")).length === 0 ? "th" : "td";
      out.push("<tr>" + cells.map(c => `<${tag}>${c}</${tag}>`).join("") + "</tr>");
    } else {
      if (inTable) { out.push("</table>"); inTable = false; }
      if (trimmed === "---") { out.push("<hr>"); }
      else if (trimmed === "") { out.push("<br>"); }
      else { out.push(trimmed); }
    }
  }
  if (inTable) out.push("</table>");
  return out.join("\n");
}

// ── Message rendering ────────────────────────────────────────────────

function addMessage(role, rawText, extra) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "U" : "H";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = miniMarkdown(rawText);

  // Action buttons (downloads, send email)
  if (extra) {
    const row = document.createElement("div");
    row.className = "action-row";
    if (extra.proposal_id) {
      row.innerHTML += `<a class="action-btn pdf"  href="/api/download/proposal/${extra.proposal_id}/pdf"  target="_blank">PDF</a>`;
      row.innerHTML += `<a class="action-btn docx" href="/api/download/proposal/${extra.proposal_id}/docx" target="_blank">DOCX</a>`;
    }
    if (extra.invoice_id) {
      row.innerHTML += `<a class="action-btn pdf" href="/api/download/invoice/${extra.invoice_id}" target="_blank">Invoice PDF</a>`;
    }
    if (extra.type === "reminder") {
      const sendEmailBtn = document.createElement("button");
      sendEmailBtn.className = "action-btn send";
      sendEmailBtn.textContent = "Send Email";
      sendEmailBtn.onclick = () => { input.value = "send"; doSend(); };
      row.appendChild(sendEmailBtn);

      const cancelBtn = document.createElement("button");
      cancelBtn.className = "action-btn pdf";
      cancelBtn.textContent = "Cancel";
      cancelBtn.style.background = "#ef4444";
      cancelBtn.onclick = () => { input.value = "cancel"; doSend(); };
      row.appendChild(cancelBtn);
    }
    bubble.appendChild(row);
  }

  wrap.appendChild(avatar);
  wrap.appendChild(bubble);
  chatArea.appendChild(wrap);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function showTyping() {
  const wrap = document.createElement("div");
  wrap.className = "msg bot";
  wrap.id = "typing-indicator";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "H";

  const bubble = document.createElement("div");
  bubble.className = "bubble typing";
  bubble.innerHTML = "<span></span><span></span><span></span>";

  wrap.appendChild(avatar);
  wrap.appendChild(bubble);
  chatArea.appendChild(wrap);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

// ── API call ─────────────────────────────────────────────────────────

async function doSend() {
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addMessage("user", escapeHTML(text));
  showTyping();
  input.disabled = true;
  sendBtn.disabled = true;

  try {
    const lang = document.getElementById("lang-select").value;
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: SESSION_ID, language: lang }),
    });
    const data = await res.json();
    removeTyping();
    addMessage("bot", data.reply, {
      proposal_id: data.proposal_id,
      invoice_id: data.invoice_id,
      type: data.type,
    });
  } catch (err) {
    removeTyping();
    addMessage("bot", "Something went wrong. Please try again.");
  } finally {
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

// ── Translations ─────────────────────────────────────────────────────

const UI_TEXT = {
  English: {
    assistant: "Assistant", proposals: "Proposals", invoices: "Invoices", paymentStatus: "Payment Status",
    placeholder: "Type a message…",
    welcome: "Welcome! I'm your **Freelancer Admin Assistant**.\n\nI can help you with:\n\n" +
      "**1.** Create a proposal -- just describe your project\n\n" +
      "**2.** Generate an invoice -- tell me the hours and rate\n\n" +
      "**3.** Send payment reminders -- I'll draft and email them\n\n" +
      "**4.** Check invoice status -- ask about unpaid invoices\n\n" +
      "Type a **number** (1-4) or describe what you need!"
  },
  Hindi: {
    assistant: "सहायक", proposals: "प्रस्ताव", invoices: "चालान", paymentStatus: "भुगतान स्थिति",
    placeholder: "संदेश लिखें…",
    welcome: "नमस्ते! मैं आपका **फ्रीलांसर एडमिन सहायक** हूँ।\n\nमैं इनमें मदद कर सकता हूँ:\n\n" +
      "**1.** प्रस्ताव बनाएं -- अपने प्रोजेक्ट का वर्णन करें\n\n" +
      "**2.** चालान बनाएं -- घंटे और दर बताएं\n\n" +
      "**3.** भुगतान रिमाइंडर भेजें -- मैं ड्राफ्ट करके ईमेल करूँगा\n\n" +
      "**4.** चालान स्थिति जाँचें -- अवैतनिक चालान के बारे में पूछें\n\n" +
      "एक **नंबर** (1-4) टाइप करें या बताएं आपको क्या चाहिए!"
  },
  Tamil: {
    assistant: "உதவியாளர்", proposals: "முன்மொழிவுகள்", invoices: "விலைப்பட்டியல்", paymentStatus: "கட்டண நிலை",
    placeholder: "செய்தி தட்டச்சு செய்யவும்…",
    welcome: "வணக்கம்! நான் உங்கள் **ஃப்ரீலான்சர் நிர்வாக உதவியாளர்**.\n\nநான் இவற்றில் உதவ முடியும்:\n\n" +
      "**1.** முன்மொழிவு உருவாக்கு -- உங்கள் திட்டத்தை விவரிக்கவும்\n\n" +
      "**2.** விலைப்பட்டியல் உருவாக்கு -- மணிநேரம் மற்றும் கட்டணம் சொல்லுங்கள்\n\n" +
      "**3.** கட்டண நினைவூட்டல் அனுப்பு -- நான் வரைந்து மின்னஞ்சல் அனுப்புவேன்\n\n" +
      "**4.** விலைப்பட்டியல் நிலை சரிபார்க்கவும்\n\n" +
      "ஒரு **எண்** (1-4) தட்டச்சு செய்யவும்!"
  },
  Kannada: {
    assistant: "ಸಹಾಯಕ", proposals: "ಪ್ರಸ್ತಾವನೆಗಳು", invoices: "ಇನ್ವಾಯ್ಸ್‌ಗಳು", paymentStatus: "ಪಾವತಿ ಸ್ಥಿತಿ",
    placeholder: "ಸಂದೇಶ ಟೈಪ್ ಮಾಡಿ…",
    welcome: "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ **ಫ್ರೀಲ್ಯಾನ್ಸರ್ ನಿರ್ವಾಹಕ ಸಹಾಯಕ**.\n\nನಾನು ಇವುಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ:\n\n" +
      "**1.** ಪ್ರಸ್ತಾವನೆ ರಚಿಸಿ -- ನಿಮ್ಮ ಯೋಜನೆಯನ್ನು ವಿವರಿಸಿ\n\n" +
      "**2.** ಇನ್ವಾಯ್ಸ್ ರಚಿಸಿ -- ಗಂಟೆಗಳು ಮತ್ತು ದರ ಹೇಳಿ\n\n" +
      "**3.** ಪಾವತಿ ಜ್ಞಾಪನೆ ಕಳುಹಿಸಿ -- ನಾನು ಡ್ರಾಫ್ಟ್ ಮಾಡಿ ಇಮೇಲ್ ಮಾಡುತ್ತೇನೆ\n\n" +
      "**4.** ಇನ್ವಾಯ್ಸ್ ಸ್ಥಿತಿ ಪರಿಶೀಲಿಸಿ\n\n" +
      "ಒಂದು **ಸಂಖ್ಯೆ** (1-4) ಟೈಪ್ ಮಾಡಿ!"
  },
  Marathi: {
    assistant: "सहाय्यक", proposals: "प्रस्ताव", invoices: "बीजक", paymentStatus: "पेमेंट स्थिती",
    placeholder: "संदेश टाइप करा…",
    welcome: "नमस्कार! मी तुमचा **फ्रीलान्सर ॲडमिन सहाय्यक** आहे.\n\nमी यामध्ये मदत करू शकतो:\n\n" +
      "**1.** प्रस्ताव तयार करा -- तुमच्या प्रकल्पाचे वर्णन करा\n\n" +
      "**2.** बीजक तयार करा -- तास आणि दर सांगा\n\n" +
      "**3.** पेमेंट रिमाइंडर पाठवा -- मी ड्राफ्ट करून ईमेल करेन\n\n" +
      "**4.** बीजक स्थिती तपासा\n\n" +
      "एक **नंबर** (1-4) टाइप करा!"
  },
};

function applyLanguage(lang) {
  const t = UI_TEXT[lang] || UI_TEXT.English;
  // Sidebar labels
  document.querySelector('[data-page="assistant"] .nav-label').textContent = t.assistant;
  document.querySelector('[data-page="proposals"] .nav-label').textContent = t.proposals;
  document.querySelector('[data-page="invoices"] .nav-label').textContent = t.invoices;
  document.querySelector('[data-page="payment-status"] .nav-label').textContent = t.paymentStatus;
  // Header title
  const activePage = document.querySelector('.nav-item.active')?.dataset.page;
  const titleMap = { "assistant": t.assistant, "proposals": t.proposals, "invoices": t.invoices, "payment-status": t.paymentStatus };
  pageTitle.textContent = titleMap[activePage] || t.assistant;
  // Placeholder
  input.placeholder = t.placeholder;
  // Re-show welcome
  chatArea.innerHTML = "";
  addMessage("bot", t.welcome);
}

// ── Event listeners ──────────────────────────────────────────────────

sendBtn.addEventListener("click", doSend);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); doSend(); }
});

// Welcome message
addMessage("bot", UI_TEXT.English.welcome);


// ── Sidebar Navigation ──────────────────────────────────────────────

const navItems = document.querySelectorAll(".nav-item");
const pages = document.querySelectorAll(".page");
const pageTitle = document.getElementById("page-title");
const menuToggle = document.getElementById("menu-toggle");
const sidebar = document.getElementById("sidebar");

function switchPage(pageName) {
  const lang = document.getElementById("lang-select").value;
  const t = UI_TEXT[lang] || UI_TEXT.English;
  navItems.forEach(n => n.classList.remove("active"));
  document.querySelector(`.nav-item[data-page="${pageName}"]`).classList.add("active");
  pages.forEach(p => p.classList.remove("active"));
  document.getElementById(`page-${pageName}`).classList.add("active");
  const titleMap = { "assistant": t.assistant, "proposals": t.proposals, "invoices": t.invoices, "payment-status": t.paymentStatus };
  pageTitle.textContent = titleMap[pageName] || pageName;
  sidebar.classList.remove("open");
  if (pageName === "proposals") loadProposals();
  if (pageName === "invoices") loadInvoices();
  if (pageName === "payment-status") loadPaymentStatus();
}

navItems.forEach(item => {
  item.addEventListener("click", () => switchPage(item.dataset.page));
});

menuToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

// Language change
document.getElementById("lang-select").addEventListener("change", (e) => applyLanguage(e.target.value));

// Profile toggle
document.getElementById("profile-toggle").addEventListener("click", () => {
  document.getElementById("profile-card").classList.toggle("hidden");
});


// ── Data Loaders ─────────────────────────────────────────────────────

function statusBadge(status) {
  const s = (status || "").toUpperCase();
  let cls = "badge-default";
  if (s === "PAID") cls = "badge-paid";
  else if (s === "UNPAID") cls = "badge-unpaid";
  else if (s === "OVERDUE") cls = "badge-overdue";
  return `<span class="card-badge ${cls}">${s || "N/A"}</span>`;
}

async function loadProposals() {
  const container = document.getElementById("proposals-list");
  container.innerHTML = '<p class="empty-state">Loading...</p>';
  try {
    const res = await fetch("/api/proposals");
    const data = await res.json();
    if (!data.length) {
      container.innerHTML = '<p class="empty-state">No proposals yet. Use the Assistant to create one!</p>';
      return;
    }
    container.innerHTML = data.map(p => `
      <div class="data-card">
        <div class="card-header">
          <span class="card-title">${escapeHTML(p.project_title || "Untitled")}</span>
        </div>
        <div class="card-row">
          <span><strong>Client:</strong> ${escapeHTML(p.client_name || "")}</span>
          <span><strong>Budget:</strong> ${escapeHTML(p.budget || "N/A")}</span>
          <span><strong>Timeline:</strong> ${escapeHTML(p.timeline || "N/A")}</span>
          <span><strong>Created:</strong> ${p.created_at || ""}</span>
        </div>
        <div class="card-actions">
          ${p.file_path_pdf ? `<a href="/api/download/proposal/${p.id}/pdf" target="_blank">Download PDF</a>` : ""}
          ${p.file_path_docx ? `<a href="/api/download/proposal/${p.id}/docx" target="_blank">Download DOCX</a>` : ""}
        </div>
      </div>
    `).join("");
  } catch {
    container.innerHTML = '<p class="empty-state">Failed to load proposals.</p>';
  }
}

async function loadInvoices() {
  const container = document.getElementById("invoices-list");
  container.innerHTML = '<p class="empty-state">Loading...</p>';
  try {
    const res = await fetch("/api/invoices");
    const data = await res.json();
    if (!data.length) {
      container.innerHTML = '<p class="empty-state">No invoices yet. Use the Assistant to create one!</p>';
      return;
    }
    container.innerHTML = data.map(inv => {
      const isPaid = (inv.status || "").toUpperCase() === "PAID";
      const markPaidBtn = !isPaid
        ? `<button class="mark-paid-btn" onclick="markAsPaid(${inv.id}, this)">Mark as Paid</button>`
        : "";

      return `
        <div class="data-card">
          <div class="card-header">
            <span class="card-title">Invoice #${escapeHTML(inv.invoice_number)}</span>
            ${statusBadge(inv.status)}
          </div>
          <div class="card-row">
            <span><strong>Client:</strong> ${escapeHTML(inv.client_name || "")}</span>
            <span><strong>Project:</strong> ${escapeHTML(inv.project_name || "")}</span>
            <span><strong>Total:</strong> $${Number(inv.grand_total || 0).toFixed(2)}</span>
            <span><strong>Due:</strong> ${inv.due_date || "N/A"}</span>
          </div>
          <div class="card-actions">
            ${inv.file_path_pdf ? `<a href="/api/download/invoice/${inv.id}" target="_blank">Download PDF</a>` : ""}
            ${markPaidBtn}
          </div>
        </div>
      `;
    }).join("");
  } catch {
    container.innerHTML = '<p class="empty-state">Failed to load invoices.</p>';
  }
}

async function markAsPaid(invoiceId, btnEl) {
  btnEl.disabled = true;
  btnEl.textContent = "Updating...";
  btnEl.style.opacity = "0.6";
  try {
    const res = await fetch(`/api/invoice/${invoiceId}/mark-paid`, { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      btnEl.textContent = "Paid!";
      btnEl.style.background = "#22c55e";
      setTimeout(() => loadInvoices(), 1000);
    } else {
      btnEl.textContent = "Failed";
      alert(data.error || "Failed to update.");
      setTimeout(() => { btnEl.textContent = "Mark as Paid"; btnEl.style.opacity = ""; btnEl.disabled = false; }, 2000);
    }
  } catch {
    btnEl.textContent = "Error";
    setTimeout(() => { btnEl.textContent = "Mark as Paid"; btnEl.style.opacity = ""; btnEl.disabled = false; }, 2000);
  }
}


async function loadPaymentStatus() {
  const container = document.getElementById("payment-list");
  container.innerHTML = '<p class="empty-state">Loading...</p>';
  try {
    // Load invoices for payment overview
    const invRes = await fetch("/api/invoices");
    const invoices = await invRes.json();

    // Load reminders
    const remRes = await fetch("/api/reminders");
    const reminders = await remRes.json();

    if (!invoices.length && !reminders.length) {
      container.innerHTML = '<p class="empty-state">No payment data yet.</p>';
      return;
    }

    let html = "";

    // Payment summary from invoices
    if (invoices.length) {
      const paid = invoices.filter(i => (i.status || "").toUpperCase() === "PAID");
      const unpaid = invoices.filter(i => (i.status || "").toUpperCase() !== "PAID");
      const totalDue = unpaid.reduce((s, i) => s + (i.grand_total || 0), 0);

      html += `
        <div class="data-card">
          <div class="card-header">
            <span class="card-title">Payment Summary</span>
          </div>
          <div class="card-row">
            <span><strong>Total Invoices:</strong> ${invoices.length}</span>
            <span><strong>Paid:</strong> ${paid.length}</span>
            <span><strong>Unpaid:</strong> ${unpaid.length}</span>
            <span><strong>Outstanding:</strong> $${totalDue.toFixed(2)}</span>
          </div>
        </div>
      `;

      // Individual invoice payment cards with send reminder button for unpaid
      invoices.forEach(inv => {
        const isUnpaid = (inv.status || "").toUpperCase() !== "PAID";
        const reminderBtn = isUnpaid
          ? `<button class="reminder-btn" data-inv="${escapeHTML(inv.invoice_number)}" onclick="sendReminder('${escapeHTML(inv.invoice_number)}', this)">Send Reminder</button>`
          : "";

        html += `
          <div class="data-card">
            <div class="card-header">
              <span class="card-title">Invoice #${escapeHTML(inv.invoice_number)}</span>
              ${statusBadge(inv.status)}
            </div>
            <div class="card-row">
              <span><strong>Client:</strong> ${escapeHTML(inv.client_name || "")}</span>
              <span><strong>Email:</strong> ${escapeHTML(inv.client_email || "N/A")}</span>
              <span><strong>Amount:</strong> $${Number(inv.grand_total || 0).toFixed(2)}</span>
              <span><strong>Due:</strong> ${inv.due_date || "N/A"}</span>
            </div>
            <div class="card-actions">
              ${reminderBtn}
            </div>
          </div>
        `;
      });
    }

    // Reminder history
    if (reminders.length) {
      html += `<h3 style="margin: 20px 0 12px; font-size: 1rem; color: var(--text-secondary);">Reminder History</h3>`;
      reminders.forEach(r => {
        const sentBadge = r.sent
          ? '<span class="card-badge badge-sent">SENT</span>'
          : '<span class="card-badge badge-pending">PENDING</span>';
        html += `
          <div class="data-card">
            <div class="card-header">
              <span class="card-title">${escapeHTML(r.subject || "Reminder")}</span>
              ${sentBadge}
            </div>
            <div class="card-row">
              <span><strong>Client:</strong> ${escapeHTML(r.client_name || "")}</span>
              <span><strong>Invoice:</strong> ${escapeHTML(r.invoice_number || "N/A")}</span>
              <span><strong>Date:</strong> ${r.date_sent || r.created_at || "N/A"}</span>
            </div>
          </div>
        `;
      });
    }

    container.innerHTML = html;
  } catch {
    container.innerHTML = '<p class="empty-state">Failed to load payment data.</p>';
  }
}


// ── Send Reminder from Payment Status tab ────────────────────────────

async function sendReminder(invoiceNumber, btnEl) {
  btnEl.disabled = true;
  btnEl.textContent = "Sending...";
  btnEl.style.opacity = "0.6";

  try {
    const res = await fetch(`/api/send-reminder/${invoiceNumber}`, { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      btnEl.textContent = "Sent!";
      btnEl.style.background = "#22c55e";
      // Refresh after a moment to show updated reminder history
      setTimeout(() => loadPaymentStatus(), 1500);
    } else {
      btnEl.textContent = "Failed";
      btnEl.style.background = "#ef4444";
      alert(data.error || "Failed to send reminder.");
      setTimeout(() => {
        btnEl.textContent = "Send Reminder";
        btnEl.style.background = "";
        btnEl.style.opacity = "";
        btnEl.disabled = false;
      }, 2000);
    }
  } catch {
    btnEl.textContent = "Error";
    btnEl.style.background = "#ef4444";
    setTimeout(() => {
      btnEl.textContent = "Send Reminder";
      btnEl.style.background = "";
      btnEl.style.opacity = "";
      btnEl.disabled = false;
    }, 2000);
  }
}

