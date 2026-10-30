// Doc Converter — Chat Assistant & Document Intelligence (Strictly Non-Blue Liquid Glass)

(function () {
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const chatMessageInput = document.getElementById('chatMessageInput');
  const attachFileBtn = document.getElementById('attachFileBtn');
  const chatDocUpload = document.getElementById('chatDocUpload');
  const activeDocContext = document.getElementById('activeDocContext');
  const contextFilename = document.getElementById('contextFilename');
  const ocrWarningBadge = document.getElementById('ocrWarningBadge');
  const removeContextBtn = document.getElementById('removeContextBtn');
  const clearChatBtn = document.getElementById('clearChatBtn');
  const quickChips = document.getElementById('quickChips');

  let activeDocId = null;
  let activeFilename = null;
  let conversationHistory = [];
  const sessionId = 'session_' + Math.random().toString(36).substring(2, 11);

  // 1. File Upload / Attachment for Chat
  attachFileBtn.addEventListener('click', () => chatDocUpload.click());

  chatDocUpload.addEventListener('change', async () => {
    if (chatDocUpload.files.length > 0) {
      const file = chatDocUpload.files[0];
      await uploadDocumentForChat(file);
    }
  });

  async function uploadDocumentForChat(file) {
    const fd = new FormData();
    fd.append('file', file);
    addMessageToUi('assistant', `Uploading and analyzing <strong>${escapeHtml(file.name)}</strong>...`);

    try {
      const res = await fetch('/api/chat/upload', {
        method: 'POST',
        body: fd
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Upload failed');
      }
      const data = await res.json();
      setDocumentContext(data);
      addMessageToUi('assistant', `Document <strong>${escapeHtml(data.filename)}</strong> attached (${data.char_count.toLocaleString()} characters extracted across ${data.page_count} page(s)). You can now ask questions or request a structured summary.`);
    } catch (e) {
      addMessageToUi('assistant', `<span style="color: var(--status-error);">Failed to attach document: ${escapeHtml(e.message)}</span>`);
    }
  }

  // Attach from existing converted output file
  async function attachExistingFile(filename) {
    addMessageToUi('assistant', `Loading converted file <strong>${escapeHtml(filename)}</strong> into intelligence engine...`);
    try {
      const fd = new FormData();
      fd.append('existing_filename', filename);
      const res = await fetch('/api/chat/upload', {
        method: 'POST',
        body: fd
      });
      if (!res.ok) {
        throw new Error('Could not load converted file.');
      }
      const data = await res.json();
      setDocumentContext(data);
      addMessageToUi('assistant', `Attached converted output <strong>${escapeHtml(data.filename)}</strong>. How would you like to analyze it?`);
    } catch (e) {
      addMessageToUi('assistant', `<span style="color: var(--status-error);">Notice: ${escapeHtml(e.message)}</span>`);
    }
  }

  function setDocumentContext(docData) {
    activeDocId = docData.doc_id;
    activeFilename = docData.filename;
    contextFilename.textContent = docData.filename;
    activeDocContext.style.display = 'flex';
    ocrWarningBadge.style.display = docData.is_ocr ? 'inline-block' : 'none';
  }

  removeContextBtn.addEventListener('click', () => {
    activeDocId = null;
    activeFilename = null;
    activeDocContext.style.display = 'none';
    addMessageToUi('assistant', 'Document detached. Queries will now operate in general mode without document grounding.');
  });

  // 2. Clear Chat Session
  clearChatBtn.addEventListener('click', () => {
    conversationHistory = [];
    chatMessages.innerHTML = `
      <div class="chat-bubble assistant-message">
        <div class="bubble-content">
          Session cleared. Attach a document or ask a question to begin a new analysis.
        </div>
      </div>
    `;
  });

  // 3. Quick Action Chips
  quickChips.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const prompt = btn.dataset.prompt;
      if (!activeDocId) {
        chatMessageInput.value = prompt;
        chatMessageInput.focus();
        return;
      }

      // If user clicks "Summarise" and a document is active, trigger structured summarization endpoint
      if (btn.textContent.trim().toLowerCase() === 'summarise') {
        await executeDirectSummarize(activeDocId, 'detailed', 'standard');
      } else {
        await sendUserMessage(prompt);
      }
    });
  });

  // 4. Direct Structured Summarize
  async function executeDirectSummarize(docId, style, length) {
    addMessageToUi('user', `Generate a ${style} summary (${length}) for this document.`);
    const assistantBubble = createMessageBubble('assistant');
    const contentDiv = assistantBubble.querySelector('.bubble-content');
    contentDiv.textContent = 'Generating summary via Gemini...';

    try {
      const res = await fetch('/api/chat/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: docId, style: style, length: length })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Summarization request failed.');
      }
      contentDiv.innerHTML = formatMarkdown(data.summary);
      attachSummaryActions(assistantBubble, data.summary, activeFilename || 'Document_Summary');
    } catch (e) {
      contentDiv.innerHTML = `<span style="color: var(--status-error);">Error: ${escapeHtml(e.message)}</span>`;
    }
  }

  // 5. Chat Form Submit & SSE Streaming
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = chatMessageInput.value.trim();
    if (!message) return;
    chatMessageInput.value = '';
    await sendUserMessage(message);
  });

  async function sendUserMessage(message) {
    addMessageToUi('user', message);
    conversationHistory.push({ role: 'user', content: message });

    const assistantBubble = createMessageBubble('assistant');
    const contentDiv = assistantBubble.querySelector('.bubble-content');
    contentDiv.classList.add('typing-cursor');

    try {
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          doc_id: activeDocId,
          message: message,
          history: conversationHistory.slice(-8)
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let fullText = '';
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep partial line in buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.slice(6);
            if (dataStr === '[DONE]') {
              break;
            }
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.chunk) {
                fullText += parsed.chunk;
                contentDiv.innerHTML = formatMarkdown(fullText);
                chatMessages.scrollTop = chatMessages.scrollHeight;
              } else if (parsed.error) {
                fullText += `\n[Error: ${parsed.error}]`;
                contentDiv.innerHTML = formatMarkdown(fullText);
              }
            } catch (jsonErr) {}
          }
        }
      }

      contentDiv.classList.remove('typing-cursor');
      conversationHistory.push({ role: 'assistant', content: fullText });
      attachSummaryActions(assistantBubble, fullText, activeFilename || 'Response');
    } catch (err) {
      contentDiv.classList.remove('typing-cursor');
      contentDiv.innerHTML = `<span style="color: var(--status-error);">Communication error: ${escapeHtml(err.message)}</span>`;
    }
  }

  // 6. UI Helpers
  function addMessageToUi(role, htmlContent) {
    const bubble = createMessageBubble(role);
    bubble.querySelector('.bubble-content').innerHTML = htmlContent;
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
  }

  function createMessageBubble(role) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role === 'user' ? 'user-message' : 'assistant-message'}`;
    bubble.innerHTML = `<div class="bubble-content"></div>`;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
  }

  function attachSummaryActions(bubbleElement, rawText, docTitle) {
    if (!rawText || rawText.length < 50) return;
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';
    actionsDiv.innerHTML = `
      <button type="button" class="btn-bubble-action copy-btn" title="Copy text">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
        <span>Copy</span>
      </button>
      <button type="button" class="btn-bubble-action export-txt" title="Export as TXT">TXT</button>
      <button type="button" class="btn-bubble-action export-docx" title="Export as DOCX">DOCX</button>
      <button type="button" class="btn-bubble-action export-pdf" title="Export as PDF">PDF</button>
    `;
    bubbleElement.appendChild(actionsDiv);

    // Copy Handler
    actionsDiv.querySelector('.copy-btn').addEventListener('click', async () => {
      await navigator.clipboard.writeText(rawText);
      const span = actionsDiv.querySelector('.copy-btn span');
      span.textContent = 'Copied!';
      setTimeout(() => { span.textContent = 'Copy'; }, 2000);
    });

    // Export Handlers
    ['txt', 'docx', 'pdf'].forEach(fmt => {
      const btn = actionsDiv.querySelector(`.export-${fmt}`);
      if (btn) {
        btn.addEventListener('click', () => {
          triggerExport(rawText, fmt, docTitle);
        });
      }
    });
  }

  async function triggerExport(text, format, title) {
    try {
      const res = await fetch('/api/chat/export-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          format: format,
          title: `Summary of ${title}`
        })
      });
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Summary_${title.replace(/[^a-zA-Z0-9]/g, '_')}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Export error: ${e.message}`);
    }
  }

  function formatMarkdown(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^### (.*$)/gim, '<h4 style="margin: 8px 0 4px; color: var(--accent-bronze-light);">$1</h4>')
      .replace(/^## (.*$)/gim, '<h3 style="margin: 10px 0 6px; color: var(--text-ivory);">$1</h3>')
      .replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/gs, '<ul style="margin: 8px 0 8px 18px;">$1</ul>')
      .replace(/\n\n+/g, '<br><br>')
      .replace(/\n/g, '<br>');
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Expose global controller
  window.DocChatAssistant = {
    attachExistingFile
  };
})();
