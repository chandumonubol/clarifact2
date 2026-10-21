(() => {
  const state = {
    jobId: null,
    currentStep: null,
    messages: [], // {id, type:'user'|'ai', text, fileName, thumbnail}
  };

  const elements = {
    textInput: document.getElementById('text-input'),
    sendBtn: document.getElementById('send-btn'),
    addBtn: document.getElementById('add-btn'),
    fileInput: document.getElementById('file-input'),
    filePreview: document.getElementById('file-preview'),
    chatArea: document.querySelector('.chat-area'),
    recentList: document.getElementById('recent-list'),
    newChatBtn: document.querySelector('.sidebar-btn.new-chat'),
  };

  let currentQuery = '';

  const esc = (s) => {
    const str = String(s);
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#39;');
  };

  // Helper to determine domain authority for a source URL
  const getAuthority = (url) => {
    try {
      const host = new URL(url).hostname;
      if (/\b(wikipedia|nytimes|bbc|theguardian)\.org$/.test(host) || /\.(edu|gov|mil)$/.test(host)) return 'High';
      if (/\.com$/.test(host) || /\.net$/.test(host)) return 'Medium';
      return 'Low';
    } catch (e) {
      return 'Low';
    }
  };

  // Show a message bubble in the chat
  const addMessage = (msg) => {
    const div = document.createElement('div');
    div.className = 'message ' + (msg.type === 'user' ? 'user' : 'ai');
    div.dataset.id = msg.id;

    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = msg.timestamp || '';

    let textDiv;
    if (msg.type === 'user') {
      textDiv = document.createElement('div');
      textDiv.className = 'message-text';
      textDiv.textContent = msg.text;

      if (msg.fileName && msg.thumbnail) {
        const thumb = document.createElement('img');
        thumb.src = msg.thumbnail;
        thumb.alt = 'Upload';
        thumb.style = 'max-width: 120px; max-height: 90px; border-radius: 6px; margin-right: 8px; object-fit: cover;';
        const thumbWrap = document.createElement('div');
        thumbWrap.style = 'display: flex; align-items: center; gap: 8px;';
        thumbWrap.appendChild(thumb);
        thumbWrap.appendChild(document.createTextNode(msg.fileName));
        textDiv.insertBefore(thumbWrap, textDiv.firstChild);
      } else if (msg.fileName) {
        textDiv.insertBefore(document.createTextNode(' – ' + msg.fileName), textDiv.firstChild);
      }
    } else {
      textDiv = document.createElement('div');
      textDiv.className = 'message-text';
      textDiv.textContent = msg.text;
    }

    div.appendChild(textDiv);
    if (meta.textContent) div.appendChild(meta);
    elements.chatArea.appendChild(div);
    elements.chatArea.scrollTop = elements.chatArea.scrollHeight;
  };

  // Show progress line
  const showProgress = (step) => {
    elements.currentStep = step;
    let prog = document.querySelector('.progress-bar');
    if (!prog) {
      prog = document.createElement('div');
      prog.className = 'progress-bar spinning';
      prog.textContent = step;
      // Insert after the last message or at top of chat-area if no messages
      const lastMsg = elements.chatArea.querySelector('.message:last-child');
      if (lastMsg && lastMsg.parentNode) {
        lastMsg.parentNode.insertBefore(prog, lastMsg.nextSibling);
      } else {
        elements.chatArea.insertBefore(prog, elements.chatArea.firstChild);
      }
    } else {
      prog.textContent = step;
      prog.classList.add('spinning');
    }
  };

  // Remove progress line
  const removeProgress = () => {
    const prog = document.querySelector('.progress-bar');
    if (prog) prog.remove();
    state.currentStep = null;
  };

  // Render result cards from AnalysisResult
  const renderResults = (result) => {
    // Clear existing progress
    removeProgress();

    // Clear chat area for results

    // 1. Score ring + label + confidence chip
    const scoreCard = document.createElement('div');
    scoreCard.className = 'result-card';
    scoreCard.innerHTML = `
      <div class="score-ring">
        <svg viewBox="0 0 100 100">
          <circle class="track" cx="50" cy="50" r="45"/>
          <circle class="progress" cx="50" cy="50" r="45" fill="none" stroke-width="8"
            stroke-linecap="round"/>
        </svg>
        <div class="label" id="score-label"></div>
      </div>
      <div class="confidence-chip" id="confidence-chip"></div>
    `;
    // Insert score breakdown expander
    const breakdownCard = document.createElement('div');
    breakdownCard.className = 'result-card';
    breakdownCard.innerHTML = `
      <div class="breakdown-header" style="cursor:pointer;font-weight:600;">Score breakdown (click to expand)</div>
      <div class="breakdown-content" style="display:none;margin-top:8px;"></div>
    `;
    elements.chatArea.appendChild(breakdownCard);
    // Toggle handler
    const header = breakdownCard.querySelector('.breakdown-header');
    const content = breakdownCard.querySelector('.breakdown-content');
    header.addEventListener('click', () => {
      const visible = content.style.display === 'block';
      content.style.display = visible ? 'none' : 'block';
    });
    // Build breakdown details
    const computeBreakdown = () => {
      const lines = [];
      let base = 100;
      lines.push(`<li>Base: 100</li>`);
      // Claims penalties
      const verdictCounts = { contradicted:0, misleading:0, unverified:0 };
      result.claims.forEach(c => {
        if (c.verdict in verdictCounts) verdictCounts[c.verdict]++;
      });
      if (verdictCounts.contradicted) lines.push(`<li>Contradicted claims (${verdictCounts.contradicted}): -${verdictCounts.contradicted * 25}</li>`);
      if (verdictCounts.misleading) lines.push(`<li>Misleading claims (${verdictCounts.misleading}): -${verdictCounts.misleading * 15}</li>`);
      if (verdictCounts.unverified) lines.push(`<li>Unverified claims (${verdictCounts.unverified}): -${verdictCounts.unverified * 5}</li>`);
      // Promo penalties
      if (result.promo && result.promo.detected) {
        const promoLoss = result.promo.type === 'hidden' ? 20 : result.promo.type === 'disclosed' ? 5 : 0;
        if (promoLoss) lines.push(`<li>Promotion (${result.promo.type}): -${promoLoss}</li>`);
      }
      // Red flag penalties (capped at 20)
      const redFlagLoss = Math.min(result.red_flags.length * 5, 20);
      if (redFlagLoss) lines.push(`<li>Red flags (${result.red_flags.length}): -${redFlagLoss}</li>`);
      // Final score
      lines.push(`<li><strong>Final score: ${result.credibility_score}</strong></li>`);
      return `<ul style="padding-left:1.2em;">${lines.join('')}</ul>`;
    };
    content.innerHTML = computeBreakdown();

    const labelMap = { Credible: 'var(--good-text)', 'Use caution': 'var(--caution-text)', 'Likely misleading': 'var(--bad-text)' };
    const labelColor = labelMap[result.label] || 'red';
    const scoreRing = scoreCard.querySelector('.progress');
    if (scoreRing) {
      const pct = result.credibility_score;
      scoreRing.style.stroke = labelColor;
      scoreRing.style.transition = 'stroke 0.3s';
      scoreRing.style.strokeDasharray = `${Math.PI * 90}`;
      scoreRing.style.strokeDashoffset = `${(100 - pct) / 100 * Math.PI * 90}`;
      const labelDiv = scoreCard.querySelector('#score-label');
      if (labelDiv) {
        labelDiv.textContent = `${result.credibility_score} — ${result.label}`;
        labelDiv.style.color = labelColor;
      }
    }
    const confChip = scoreCard.querySelector('#confidence-chip');
    if (confChip) {
      const confClass = result.confidence === 'high' ? 'chip-high' : result.confidence === 'medium' ? 'chip-medium' : 'chip-low';
      confChip.className = `confidence-chip ${confClass}`;
      confChip.textContent = result.confidence;
    }

    // 2. Promotion banner
    const promoCard = document.createElement('div');
    promoCard.className = 'result-card';
    const promoType = result.promo.type || 'none';
    const promoClass = { hidden: 'hidden', disclosed: 'disclosed', none: 'none' }[promoType] || 'none';
    promoCard.classList.add('promo-banner', promoClass);
    promoCard.innerHTML = `
      <span class="type">Promotion: ${promoType}</span>
      <ul class="evidence">${result.promo.evidence.map(e => `<li>${e}</li>`).join('')}</ul>
    `;
    elements.chatArea.appendChild(promoCard);

    // 3. Claims list
    const claimsDiv = document.createElement('div');
    claimsDiv.className = 'result-card';
    claimsDiv.innerHTML = '<h4 style="font-size:0.75rem;color:var(--muted);margin:8px 0;">Claims</h4>';
    const claimsList = document.createElement('div');
    claimsList.className = 'claims-list';
    result.claims.forEach((c, i) => {
      const verdictClass = { supported: 'supported', contradicted: 'contradicted', misleading: 'misleading', unverified: 'unverified' }[c.verdict] || 'unverified';
      // Build source chips with domain authority badges
      const srcHtml = c.sources && c.sources.length ? c.sources.map(s => {
        const authority = getAuthority(s.url);
        const badgeClass = authority === 'High' ? 'good' : authority === 'Medium' ? 'caution' : 'bad';
        return `<a class="source-chip" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)} <span class="domain-badge ${badgeClass}">${authority}</span></a>`;
      }).join(' ') : '<em>none</em>';
      const item = document.createElement('div');
      item.className = `claim-item`;
      item.innerHTML = `<div class="claim-verdict ${verdictClass}">${c.verdict}</div><div class="claim-text">${esc(c.text)}</div><div class="claim-explanation">${esc(c.explanation)}</div><div class="sources-list"><strong>SOURCES & EVIDENCE:</strong> ${srcHtml}</div>`;
      claimsList.appendChild(item);
    });
    claimsDiv.appendChild(claimsList);
    elements.chatArea.appendChild(claimsDiv);

    // 4. Red flag chips
    const redFlagsDiv = document.createElement('div');
    redFlagsDiv.className = 'result-card';
    const rfHeader = document.createElement('h4');
    rfHeader.style.cssText = 'font-size:0.75rem;color:var(--muted);margin:8px 0;';
    rfHeader.textContent = 'Red flags';
    const rfList = document.createElement('div');
    rfList.className = 'red-flags';
    result.red_flags.forEach(f => {
      const chip = document.createElement('span');
      chip.className = 'red-flag';
      chip.textContent = f;
      rfList.appendChild(chip);
    });
    redFlagsDiv.appendChild(rfHeader);
    redFlagsDiv.appendChild(rfList);
    elements.chatArea.appendChild(redFlagsDiv);

    // 5. Collapsible Transcript and OCR text
    const collapsiblesDiv = document.createElement('div');
    collapsiblesDiv.className = 'result-card';
    collapsiblesDiv.innerHTML = `
      <h4 style="font-size:0.75rem;color:var(--muted);margin:8px 0;">Transcript</h4>
      <div class="transcript-section" id="transcript-section"></div>
      <h4 style="font-size:0.75rem;color:var(--muted);margin:8px 0;">On-screen text</h4>
      <div class="transcript-section" id="ocr-section"></div>
    `;
    elements.chatArea.appendChild(collapsiblesDiv);

    const transcriptSection = document.getElementById('transcript-section');
    const ocrSection = document.getElementById('ocr-section');
    if (transcriptSection) {
      transcriptSection.innerHTML = `<pre>${esc(result.transcript)}</pre>`;
    }
    if (ocrSection) {
      ocrSection.innerHTML = `<pre>${esc(result.ocr_text)}</pre>`;
    }

    // 6. Warnings
    if (result.warnings && result.warnings.length > 0) {
      const warnCard = document.createElement('div');
      warnCard.className = 'result-card';
      warnCard.classList.add('warning-box');
      warnCard.textContent = result.warnings.join('. ');
      elements.chatArea.appendChild(warnCard);
    }
  };

  // Show error state
  // Show error state
  const showError = (err) => {
    removeProgress();
    elements.chatArea.innerHTML = '';
    const errorCard = document.createElement('div');
    errorCard.className = 'error-card';
    errorCard.innerHTML = `<p style="margin-bottom:16px;">${esc(err || 'An error occurred')}</p>`;
    const btn = document.createElement('button');
    btn.className = 'try-again';
    btn.textContent = 'Try again';
    btn.onclick = () => location.reload();
    errorCard.appendChild(btn);
    elements.chatArea.appendChild(errorCard);
  };

  // History helpers
  const loadHistory = () => {
    const data = localStorage.getItem('clarifact_history');
    return data ? JSON.parse(data) : [];
  };
  const saveHistory = (hist) => {
    localStorage.setItem('clarifact_history', JSON.stringify(hist));
  };
  const addHistoryEntry = (title, result) => {
    const hist = loadHistory();
    const entry = { title, result, timestamp: Date.now() };
    hist.unshift(entry);
    if (hist.length > 50) hist.pop();
    saveHistory(hist);
  };
  const renderHistoryList = () => {
    const list = elements.recentList;
    if (!list) return;
    const hist = loadHistory();
    list.innerHTML = '';
    if (hist.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No analyses yet';
      list.appendChild(empty);
      return;
    }
    hist.forEach(entry => {
      const item = document.createElement('div');
      item.className = 'recent-item';
      const titleSpan = document.createElement('span');
      titleSpan.textContent = entry.title;
      const badge = document.createElement('span');
      badge.textContent = entry.result.credibility_score;
      badge.style.cssText = 'margin-left:auto;background:var(--surface-2);color:var(--text);border-radius:var(--radius-sm);padding:var(--space-4) var(--space-8);font-size:13px;';
      item.appendChild(titleSpan);
      item.appendChild(badge);
      item.addEventListener('click', () => {
        elements.chatArea.innerHTML = '';
        document.body.classList.add('has-messages');
        addMessage({ id: 'user-' + Date.now(), type: 'user', text: entry.title });
        renderResults(entry.result);
      });
      list.appendChild(item);
    });
  };

  // Handle sending
  const send = async () => {
    const text = elements.textInput.value.trim();
    if (!text && !state.selectedFile) return;

    // Check if text starts with http -> send as url, else as text
    let formText = text;
    let formFile = null;
    if (text.startsWith('http://') || text.startsWith('https://')) {
      formText = text;
    }

    const formData = new FormData();
    if (formText) { formData.append('text', formText); }
    currentQuery = formText;

    // If there's a file attached from the file picker
    const attachedFile = state.selectedFile;
    if (attachedFile) {
      formData.append('file', attachedFile);
    }

    // Preserve file info for user message before clearing state
    const fileNameForMsg = attachedFile ? attachedFile.name : null;
    const thumbnailForMsg = attachedFile ? URL.createObjectURL(attachedFile) : null;

    // Clear input
    elements.textInput.value = '';
    state.selectedFile = null;
    elements.addBtn.textContent = '+';
    elements.addBtn.title = 'Attach file';
    elements.addBtn.style.background = 'none';

    // Show user message
    addMessage({
      id: 'user-' + Date.now(),
      type: 'user',
      text: formText,
      fileName: fileNameForMsg,
      thumbnail: thumbnailForMsg,
    });

    // POST /analyze
    // Mark UI as having sent first message
    if (!document.body.classList.contains('has-messages')) {
      document.body.classList.add('has-messages');
    }
    try {
      const resp = await fetch('/analyze', {
        method: 'POST',
        body: formData,
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'API error');
      state.jobId = data.job_id;
      pollJob();
    } catch (e) {
      showError(e.message);
    }
  };

  // Poll GET /jobs/{job_id}
  const pollJob = async () => {
    if (!state.jobId) return;
    showProgress('Queued');
    while (state.jobId) {
      try {
        const resp = await fetch(`/jobs/${state.jobId}`);
        const data = await resp.json();
        if (resp.status === 404) {
          showError('Job not found');
          return;
        }
        if (!resp.ok) throw new Error('API error');

        // Update progress based on step
        if (data.step) {
          showProgress(data.step);
        }

        if (data.status === 'done') {
          removeProgress();
          renderResults(data.result);
          break;
        } else if (data.status === 'error') {
          removeProgress();
          showError(data.error || 'Analysis failed');
          break;
        }
      } catch (e) {
        showError('Network error or API failed');
        break;
      }
      await new Promise(r => setTimeout(r, 1000));
    }
  };

  // File input change handling
  elements.fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      state.selectedFile = file;
      elements.filePreview.textContent = file.name;
      elements.filePreview.style.display = 'flex';
    } else {
      state.selectedFile = null;
      elements.filePreview.textContent = '';
      elements.filePreview.style.display = 'none';
    }
  });

  // Form submit handling
  const analyzeForm = document.getElementById('analyze-form');
  if (analyzeForm) {
    analyzeForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const textVal = elements.textInput.value.trim();
      const fileVal = elements.fileInput.files[0];
      if (!textVal && !fileVal) {
        return;
      }
      const formData = new FormData();
      if (textVal) formData.append('text', textVal);
      if (fileVal) formData.append('file', fileVal);

      // Show user message
      addMessage({
        id: 'user-' + Date.now(),
        type: 'user',
        text: textVal,
        fileName: fileVal ? fileVal.name : null,
        thumbnail: fileVal ? URL.createObjectURL(fileVal) : null,
      });

      // Clear inputs
      elements.textInput.value = '';
      elements.fileInput.value = '';
      elements.filePreview.textContent = '';
      elements.filePreview.style.display = 'none';
      state.selectedFile = null;

      // Mark UI as having sent first message
      if (!document.body.classList.contains('has-messages')) {
        document.body.classList.add('has-messages');
      }
      try {
        const resp = await fetch('/analyze', { method: 'POST', body: formData });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || 'API error');
        state.jobId = data.job_id;
        pollJob();
      } catch (err) {
        showError(err.message);
      }
    });
  }

  // Removed old file picker and button click logic

  // Init
  // New chat button – reset UI
  if (elements.newChatBtn) {
    elements.newChatBtn.onclick = () => {
      // clear chat area
      elements.chatArea.innerHTML = '';
      // reset UI state
      document.body.classList.remove('has-messages');
      // reset state
      state.jobId = null;
      state.selectedFile = null;
      elements.textInput.value = '';
      elements.addBtn.textContent = '+';
      elements.addBtn.title = 'Attach file';
      elements.addBtn.style.background = 'none';
      // clear current query tracking
      currentQuery = '';
    };
  }
  // Populate history sidebar on load
  renderHistoryList();
})();