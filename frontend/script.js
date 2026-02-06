const API = "http://127.0.0.1:8001";  // ✅ FIXED: Changed from 8000 to 8001

async function uploadFile() {
  const fileInput = document.getElementById("fileInput");
  const status = document.getElementById("uploadStatus");

  if (!fileInput.files.length) {
    status.innerText = "Please select a file.";
    return;
  }

  const filename = fileInput.files[0].name;
  status.innerText = `📤 Uploading ${filename}...`;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const response = await fetch(`${API}/upload`, {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    
    // If async upload, track job progress
    if (data.job_id) {
      status.innerText = `⏳ Indexing... (${filename})`;
      trackJobProgress(data.job_id, filename);
    } else if (data.doc_id) {
      status.innerText = `✅ Done! Indexed ${filename}`;
      fetchNotifications();
      fileInput.value = "";  // Clear input
    } else {
      status.innerText = data.message || data.error || "Upload failed";
    }
  } catch (error) {
    console.error(error);
    status.innerText = `❌ Error: ${error.message}`;
  }
}

async function trackJobProgress(jobId, filename) {
  // Poll job status every 2 seconds
  const pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API}/job/${jobId}`);
      const job = await res.json();
      
      const status = document.getElementById("uploadStatus");
      
      if (job.status === "done") {
        clearInterval(pollInterval);
        status.innerText = `✅ Done! Indexed ${filename}`;
        fetchNotifications();
        document.getElementById("fileInput").value = "";  // Clear input
      } else if (job.status === "failed") {
        clearInterval(pollInterval);
        status.innerText = `❌ Failed: ${job.error || "Unknown error"}`;
      } else {
        status.innerText = `⏳ Indexing... ${filename}`;
      }
    } catch (error) {
      console.error('Job tracking error:', error);
    }
  }, 2000);
}

async function downloadFile(encodedName) {
  const filename = decodeURIComponent(encodedName);
  const alertBox = document.getElementById('uploadStatus');
  alertBox.innerText = `Downloading ${filename}...`;

  try {
    const res = await fetch(`http://127.0.0.1:8001/download?filename=${encodeURIComponent(filename)}`);
    if (!res.ok) {
      let errText = 'Download failed';
      try { const err = await res.json(); errText = err.error || errText; } catch(e){}
      alertBox.innerText = `Error: ${errText}`;
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    alertBox.innerText = `Downloaded ${filename}`;
    fetchNotifications();
  } catch (e) {
    console.error(e);
    alertBox.innerText = 'Download failed';
  }
}

async function fetchNotifications() {
  try {
    const res = await fetch('http://127.0.0.1:8001/notifications');
    const data = await res.json();
    const box = document.getElementById('notifications');
    box.innerHTML = '';
    (data.notifications || []).slice().reverse().forEach(n => {
      const el = document.createElement('div');
      el.className = 'notif';
      el.innerText = `${new Date(n.time).toLocaleString()}: ${n.message}`;
      box.appendChild(el);
    });
  } catch (e) {
    console.error('notif', e);
  }
}

// poll notifications every 8 seconds
setInterval(fetchNotifications, 8000);
fetchNotifications();

async function searchText() {
  const query = document.getElementById("query").value;
  const resultsBox = document.getElementById("results");

  resultsBox.innerHTML = "<p>🔍 Searching...</p>";

  if (query.length < 3) {
    resultsBox.innerHTML = "<p>Please enter a longer query.</p>";
    return;
  }

  try {
    const response = await fetch(
      `${API}/search?query=${encodeURIComponent(query)}`
    );

    const data = await response.json();
    resultsBox.innerHTML = "";

    if (!data.results || data.results.length === 0) {
      resultsBox.innerHTML = `
        <div class="no-results-box">
          <div class="no-results-icon">❌</div>
          <div class="no-results-title">This item is not present</div>
          <div class="no-results-message">
            <p>We couldn't find any documents for "<strong>${query}</strong>".</p>
            <p class="suggestion-text">Suggestions:</p>
            <ul>
              <li>Check spelling or try variations (e.g. full name)</li>
              <li>Upload documents related to this person or topic</li>
              <li>Try shorter keywords (e.g. surname)</li>
            </ul>
          </div>
        </div>
      `;
      return;
    }

    const showRaw = document.getElementById("showRaw")?.checked;

    // collect unique related sources
    const relatedBox = document.getElementById("related");
    relatedBox.innerHTML = "";
    const relatedFiles = new Map();  // Use Map to track files with their details

    data.results.forEach(item => {
      const card = document.createElement("div");
      card.className = "result-card";

      // `item` is expected to be an object { clean, raw, source, url, title }
      const metaHtml = `<div class="meta"><strong>${item.title || item.source || ''}</strong> ${item.url ? `<a href="${item.url}" target="_blank">(source)</a>` : ''}</div>`;
      const cleanHtml = `<div class="clean">${item.clean}</div>`;
      const rawHtml = `<pre class="raw" style="display:${showRaw ? 'block' : 'none'};white-space:pre-wrap;">${item.raw}</pre>`;

      card.innerHTML = metaHtml + cleanHtml + rawHtml;

      resultsBox.appendChild(card);

      // Collect related source files with better tracking
      if (item.source) {
        relatedFiles.set(item.source, {
          name: item.source,
          title: item.title || item.source
        });
      }
    });

    // Show related documents with download buttons
    if (relatedFiles.size > 0) {
      const filesArray = Array.from(relatedFiles.values());
      filesArray.forEach(file => {
        const row = document.createElement('div');
        row.className = 'related-row';
        row.innerHTML = `<span title="${file.title}">📄 ${file.name}</span> <button onclick="downloadFile('${encodeURIComponent(file.name)}')">⬇️ Download</button>`;
        relatedBox.appendChild(row);
      });
    } else {
      relatedBox.innerHTML = '<p style="color: #999; font-size: 0.9rem;">No documents matched</p>';
    }

    // refresh notifications immediately
    fetchNotifications();

  } catch (error) {
    console.error(error);
    resultsBox.innerHTML = "<p>⚠️ Unable to fetch results.</p>";
  }
}

/* ==================== END OF SEARCH FUNCTIONALITY ==================== */
