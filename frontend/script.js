/* Orenda Frontend Logic (Vanilla JS)
   Features:
   - Today's date, mood selection, prompts, counters
   - Reflection via FastAPI SSE (with placeholder fallback)
   - History via GET /api/history (with dummy fallback on API failure)
   - Navbar toggle, smooth scrolling, fade reveals
*/

(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // -------------------------
  // API base URL
  // -------------------------
  // In frontend-only mode there is no backend API.
  // We keep this logic but default to empty so fetch() stays same-origin (and will 404/placeholder).
  const API_BASE = (() => {
    const meta = document.querySelector('meta[name="orenda-api"]');
    if (meta && meta.content) return meta.content.replace(/\/$/, '');
    return '';
  })();


  const apiUrl = (path) => `${API_BASE}${path}`;

  // -------------------------
  // Navbar
  // -------------------------
  const initNavbar = () => {
    const nav = document.querySelector('.navbar');
    if (!nav) return;

    const toggleBtn = $('.hamburger', nav);
    const panel = $('.mobile-panel', nav);
    if (!toggleBtn || !panel) return;

    const setOpen = (isOpen) => {
      panel.classList.toggle('is-open', isOpen);
      toggleBtn.setAttribute('aria-expanded', String(isOpen));
    };

    toggleBtn.addEventListener('click', () => {
      const isOpen = panel.classList.contains('is-open');
      setOpen(!isOpen);
    });

    $$('.mobile-links a', panel).forEach((a) => {
      a.addEventListener('click', () => setOpen(false));
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') setOpen(false);
    });
  };

  // -------------------------
  // Fade-in reveal
  // -------------------------
  const initReveal = () => {
    const els = $$('.reveal');
    if (!els.length) return;

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) entry.target.classList.add('is-visible');
        }
      },
      { threshold: 0.12 }
    );

    els.forEach((el) => io.observe(el));
  };

  // -------------------------
  // Today's date
  // -------------------------
  const initDate = () => {
    const dateEl = $('#todayDate');
    if (!dateEl) return;

    const now = new Date();
    const formatter = new Intl.DateTimeFormat(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    dateEl.textContent = formatter.format(now);
  };

  const getTodayIso = () => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  // -------------------------
  // Mood selection
  // -------------------------
  const initMoodSelection = () => {
    const moodButtons = $$('.mood-btn[data-mood]');
    if (!moodButtons.length) return;

    const setMood = (btn) => {
      moodButtons.forEach((b) => b.setAttribute('aria-pressed', 'false'));
      btn.setAttribute('aria-pressed', 'true');
    };

    moodButtons.forEach((btn) => {
      btn.addEventListener('click', () => setMood(btn));
      btn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setMood(btn);
        }
      });
    });

    const first = moodButtons[0];
    if (first) first.setAttribute('aria-pressed', 'true');
  };

  const getSelectedMood = () => {
    const pressed = $('.mood-btn[aria-pressed="true"]');
    return pressed ? pressed.getAttribute('data-mood') : '';
  };

  // -------------------------
  // Random prompts (journal page)
  // -------------------------
  const PROMPTS = [
    'What made you smile today?',
    'What challenged you?',
    'What are you grateful for?',
    'What is on your mind?',
    'Where did you show kindness today?',
    'What felt heavy—and what helped it lighten?',
    'What do you want to remember from today?',
    'What are you proud of (even if it's small)?',
    'What lesson did today offer?',
    'What do you need more of right now?',
    'What boundary would support your peace?',
    'What moment felt unexpectedly good?',
    'What are you avoiding—and why?',
    'If today had a theme, what would it be?',
    'What emotion are you ready to understand?',
    'What are you looking forward to?',
    'What did you learn about yourself today?',
    'How did you care for yourself—directly or indirectly?',
    'What do you want to release?',
    'What does "enough" look like today?'
  ];

  const initPrompt = () => {
    const promptEl = $('#dailyPrompt');
    if (!promptEl) return;

    const idx = Math.floor(Math.random() * PROMPTS.length);
    promptEl.textContent = PROMPTS[idx];
  };

  // -------------------------
  // Counters (journal page)
  // -------------------------
  const initCounters = () => {
    const textarea = $('#journalText');
    if (!textarea) return;

    const wordEl = $('#wordCount');
    const charEl = $('#charCount');

    const update = () => {
      const text = textarea.value || '';
      const words = text.trim().length ? text.trim().split(/\s+/).length : 0;
      const chars = text.length;

      if (wordEl) wordEl.textContent = String(words);
      if (charEl) charEl.textContent = String(chars);
    };

    textarea.addEventListener('input', update);
    update();
  };

  // -------------------------
  // Reflection parsing helpers
  // -------------------------
  const REFLECTION_MARKERS = [
    'SUMMARY:',
    'EMOTIONS:',
    'REFLECTION QUESTIONS:',
    'ENCOURAGEMENT:',
    'SMALL GOAL:',
    "TODAY'S BLOOM:"
  ];

  const extractSection = (text, marker, nextMarkers) => {
    const idx = text.indexOf(marker);
    if (idx === -1) return null;

    const start = idx + marker.length;
    let end = text.length;

    for (const next of nextMarkers) {
      const nIdx = text.indexOf(next, start);
      if (nIdx !== -1) end = Math.min(end, nIdx);
    }

    return text.slice(start, end).trim();
  };

  const parseReflectionSections = (text) => {
    const sections = {};
    for (let i = 0; i < REFLECTION_MARKERS.length; i++) {
      const marker = REFLECTION_MARKERS[i];
      const nextMarkers = REFLECTION_MARKERS.slice(i + 1);
      const value = extractSection(text, marker, nextMarkers);
      if (value) sections[marker] = value;
    }
    return sections;
  };

  const parseEmotions = (raw) => {
    if (!raw) return [];
    return raw
      .split(/[,;]/)
      .map((e) => e.trim())
      .filter(Boolean)
      .slice(0, 3);
  };

  const parseQuestions = (raw) => {
    if (!raw) return [];
    const numbered = raw.match(/\d+\.\s*[^\n\d]+/g);
    if (numbered && numbered.length) {
      return numbered.map((q) => q.replace(/^\d+\.\s*/, '').trim()).slice(0, 2);
    }
    return raw
      .split(/\n/)
      .map((q) => q.replace(/^\d+\.\s*/, '').trim())
      .filter(Boolean)
      .slice(0, 2);
  };

  const renderEmotionChips = (el, emotions) => {
    if (!el) return;
    el.innerHTML = '';
    emotions.forEach((e) => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = e;
      el.appendChild(chip);
    });
  };

  const renderQuestions = (el, questions) => {
    if (!el) return;
    el.innerHTML = '';
    questions.forEach((q) => {
      const li = document.createElement('li');
      li.textContent = q;
      el.appendChild(li);
    });
  };

  const applyReflectionSections = (sections) => {
    const summaryEl = $('#cardSummary');
    const emotionsEl = $('#cardEmotions');
    const questionsEl = $('#cardQuestions');
    const encouragementEl = $('#cardEncouragement');
    const goalEl = $('#cardGoal');
    const bloomEl = $('#cardBloom');

    if (sections['SUMMARY:'] && summaryEl) {
      summaryEl.textContent = sections['SUMMARY:'];
    }
    if (sections['EMOTIONS:'] && emotionsEl) {
      renderEmotionChips(emotionsEl, parseEmotions(sections['EMOTIONS:']));
    }
    if (sections['REFLECTION QUESTIONS:'] && questionsEl) {
      renderQuestions(questionsEl, parseQuestions(sections['REFLECTION QUESTIONS:']));
    }
    if (sections['ENCOURAGEMENT:'] && encouragementEl) {
      encouragementEl.textContent = sections['ENCOURAGEMENT:'];
    }
    if (sections['SMALL GOAL:'] && goalEl) {
      goalEl.textContent = sections['SMALL GOAL:'];
    }
    if (sections["TODAY'S BLOOM:"] && bloomEl) {
      const bloom = sections["TODAY'S BLOOM:"];
      bloomEl.textContent = bloom.startsWith('"') || bloom.startsWith('"')
        ? bloom
        : `"${bloom}"`;
    }
  };

  const resetReflectionCards = () => {
    const summaryEl = $('#cardSummary');
    const emotionsEl = $('#cardEmotions');
    const questionsEl = $('#cardQuestions');
    const encouragementEl = $('#cardEncouragement');
    const goalEl = $('#cardGoal');
    const bloomEl = $('#cardBloom');

    if (summaryEl) summaryEl.textContent = '—';
    if (emotionsEl) emotionsEl.innerHTML = '';
    if (questionsEl) questionsEl.innerHTML = '';
    if (encouragementEl) encouragementEl.textContent = '—';
    if (goalEl) goalEl.textContent = '—';
    if (bloomEl) bloomEl.textContent = '—';
  };

  const placeholderByMood = (mood) => {
    const moodMap = {
      Happy: {
        summary: 'Your words suggest patterns of care, honesty, and momentum.',
        emotions: ['Hopeful', 'Light', 'Grateful'],
        questions: ['What made joy feel close today?', 'How can you invite more of it?'],
        encouragement: "Your happiness counts. Notice it—then let it guide your next gentle step.",
        goal: 'Write one sentence about what supports your peace.',
        bloom: 'Small joys grow into steady sunlight.'
      },
      Calm: {
        summary: 'A steady presence runs through your entry—grounded and aware.',
        emotions: ['Grounded', 'Steady', 'Present'],
        questions: ['What helped you feel safe inside your day?', 'What moment do you want to repeat?'],
        encouragement: 'Even quiet moments are meaningful. Keep choosing what brings you back to yourself.',
        goal: 'Take one mindful breath, then write one kind thought to yourself.',
        bloom: 'Stillness is a form of progress.'
      },
      Neutral: {
        summary: 'Your entry holds space for clarity without forcing meaning.',
        emotions: ['Balanced', 'Aware', 'Steady'],
        questions: ['What did you learn from neutrality?', 'What feels ready to change—gently?'],
        encouragement: 'Neutral days are space for clarity. You don't have to force meaning—just allow it to appear.',
        goal: 'Write one insight and one next step.',
        bloom: 'Clarity comes when you meet yourself honestly.'
      },
      Sad: {
        summary: 'You named something tender—and that honesty matters.',
        emotions: ['Tender', 'Compassionate', 'Honest'],
        questions: ['What do you need most while feeling this?', 'What could you do that feels caring and doable?'],
        encouragement: "Let your feelings be real. You deserve gentleness while you pass through them.",
        goal: 'Name one support you can reach for today.',
        bloom: 'Soft hearts heal with time and care.'
      },
      Anxious: {
        summary: 'Your mind is working hard to protect you—notice that with kindness.',
        emotions: ['Aware', 'Worried', 'Trying'],
        questions: ['What is your anxiety protecting you from?', 'What is one tiny action that restores safety?'],
        encouragement: 'Anxiety speaks loudly—but you can guide it with small, grounded steps.',
        goal: 'Write three grounding words and one calming action.',
        bloom: 'Courage can look like breathing first.'
      },
      Frustrated: {
        summary: 'Frustration is showing you where a need or boundary wants attention.',
        emotions: ['Noticed', 'Frustrated', 'Hopeful'],
        questions: ['What boundary or need is underneath this frustration?', 'What would make the next step feel easier?'],
        encouragement: 'Frustration is information. Thank it for trying—and then choose a kinder strategy.',
        goal: 'Rewrite your plan in one smaller step.',
        bloom: 'You can move forward without forcing yourself.'
      }
    };

    return moodMap[mood] || moodMap.Neutral;
  };

  const applyPlaceholderReflection = (mood, entry) => {
    const data = placeholderByMood(mood);
    const summaryEl = $('#cardSummary');
    const emotionsEl = $('#cardEmotions');
    const questionsEl = $('#cardQuestions');
    const encouragementEl = $('#cardEncouragement');
    const goalEl = $('#cardGoal');
    const bloomEl = $('#cardBloom');

    if (summaryEl) {
      summaryEl.textContent = entry
        ? data.summary
        : 'Select a mood and write a few lines when you're ready.';
    }
    renderEmotionChips(emotionsEl, data.emotions);
    renderQuestions(questionsEl, data.questions);
    if (encouragementEl) encouragementEl.textContent = data.encouragement;
    if (goalEl) goalEl.textContent = data.goal;
    if (bloomEl) bloomEl.textContent = `"${data.bloom}"`;
  };

  const streamReflection = async (mood, journalText, onText) => {
    const response = await fetch(apiUrl('/api/reflect/stream'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({
        mood,
        journal_text: journalText,
        date: getTodayIso()
      })
    });

    if (!response.ok) throw new Error(`Reflect API failed (${response.status})`);
    if (!response.body) throw new Error('Reflect API returned no stream');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        const lines = part.split('\n');
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);
          if (data === '[DONE]') return fullText;
          fullText += data;
          onText(fullText);
        }
      }
    }

    return fullText;
  };

  // -------------------------
  // Reflection (FastAPI SSE + placeholder fallback)
  // -------------------------
  const initReflection = () => {
    const reflectBtn = $('#reflectBtn');
    const clearBtn = $('#clearBtn');
    const journal = $('#journalText');
    const reflectionWrap = $('#reflectionWrap');
    const reflectionArea = $('#reflectionArea');
    const reflectionSubtitle = $('#reflectionSubtitle');

    if (!reflectBtn || !reflectionWrap || !reflectionArea) return;

    let streaming = false;

    const openReflection = () => {
      reflectionWrap.classList.remove('hidden');
      reflectionArea.classList.remove('hidden');
      reflectionArea.classList.remove('fade-expand');
      void reflectionArea.offsetHeight;
      reflectionArea.classList.add('fade-expand');
    };

    const setReflecting = (isReflecting) => {
      streaming = isReflecting;
      reflectBtn.disabled = isReflecting;
      reflectBtn.textContent = isReflecting ? 'Reflecting…' : 'Reflect';
      reflectBtn.setAttribute('aria-busy', String(isReflecting));
    };

    reflectBtn.addEventListener('click', async () => {
      if (streaming) return;

      const mood = getSelectedMood();
      const entry = journal ? (journal.value || '').trim() : '';

      openReflection();
      resetReflectionCards();
      setReflecting(true);

      if (reflectionSubtitle) {
        reflectionSubtitle.textContent = 'Generating your reflection…';
      }

      try {
        await streamReflection(mood, entry, (accumulated) => {
          applyReflectionSections(parseReflectionSections(accumulated));
        });

        if (reflectionSubtitle) {
          reflectionSubtitle.textContent = 'Your reflection is ready.';
        }
      } catch {
        applyPlaceholderReflection(mood, entry);
        if (reflectionSubtitle) {
          reflectionSubtitle.textContent =
            'Showing a gentle placeholder while the reflection service is unavailable.';
        }
      } finally {
        setReflecting(false);
      }
    });

    if (clearBtn && journal) {
      clearBtn.addEventListener('click', () => {
        journal.value = '';
        reflectionWrap.classList.add('hidden');
        reflectionArea.classList.add('hidden');
        resetReflectionCards();
        if (reflectionSubtitle) {
          reflectionSubtitle.textContent = 'Reflections appear here after you journal.';
        }
      });
    }
  };

  // -------------------------
  // History page (API + dummy fallback)
  // -------------------------
  const HISTORY_DUMMY = [
    { date: '2026-07-01', mood: 'Happy', summary: 'A calm win: I finished what I started and felt lighter afterward.' },
    { date: '2026-06-29', mood: 'Calm', summary: 'Slow mornings and steady breaths helped me feel grounded again.' },
    { date: '2026-06-27', mood: 'Neutral', summary: 'Nothing felt dramatic, and that in itself felt peaceful.' },
    { date: '2026-06-25', mood: 'Anxious', summary: 'My mind raced—but writing it down made the next step clearer.' },
    { date: '2026-06-20', mood: 'Sad', summary: 'Grief showed up quietly. I gave myself room to feel it fully.' },
    { date: '2026-06-18', mood: 'Frustrated', summary: 'I was impatient with myself. I noticed the pattern and paused.' }
  ];

  const filterHistoryItems = (items, q, mood) => {
    const query = (q || '').trim().toLowerCase();
    return items.filter((x) => {
      const matchesMood = mood === 'All' ? true : x.mood === mood;
      const matchesText = query
        ? `${x.summary || ''} ${x.date || ''} ${x.mood || ''}`.toLowerCase().includes(query)
        : true;
      return matchesMood && matchesText;
    });
  };

  const renderHistoryCards = (grid, items, { isFallback = false } = {}) => {
    if (!items.length) {
      grid.innerHTML = `
        <article class="card card-pad" role="status" aria-live="polite">
          <h2 class="h2" style="font-size:1.1rem">No entries yet</h2>
          <p class="p" style="margin-top:10px">Start journaling to create your first history card.</p>
        </article>
      `;
      return;
    }

    const fallbackNote = isFallback
      ? '<p class="p" style="margin:0 0 10px;font-size:.9rem;color:var(--muted)">Showing sample entries while history is unavailable.</p>'
      : '';

    grid.innerHTML = items
      .map((x, i) => {
        const summary = x.summary || '';
        const firstLines = summary.slice(0, 90) + (summary.length > 90 ? '…' : '');

        return `
          <article class="card card-pad card-hover" role="listitem" aria-label="Journal history entry">
            ${i === 0 ? fallbackNote : ''}
            <div class="counter-row" style="margin-top:0">
              <span><strong>${x.date}</strong></span>
              <span style="color:var(--primary)"><strong>${x.mood}</strong></span>
            </div>
            <p style="margin:12px 0 10px;color:var(--muted)">${firstLines}</p>
            <hr class="hr-soft" />
            <p style="margin:0"><strong>AI Summary</strong></p>
            <p style="margin:8px 0 14px;color:var(--muted)">${summary}</p>
            <button class="btn btn-ghost btn-sm" type="button" aria-label="Read more about this entry">Read More</button>
          </article>
        `;
      })
      .join('');
  };

  const fetchHistory = async (q, mood) => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (mood && mood !== 'All') params.set('mood', mood);

    const query = params.toString();
    const url = apiUrl(`/api/history${query ? `?${query}` : ''}`);

    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`History API failed (${response.status})`);

    const data = await response.json();
    return Array.isArray(data.items) ? data.items : [];
  };

  const initHistory = () => {
    const grid = $('#historyGrid');
    if (!grid) return;

    const search = $('#historySearch');
    const filter = $('#moodFilter');
    if (!search || !filter) return;

    let debounceTimer = null;
    let requestId = 0;

    const apply = async () => {
      const q = (search.value || '').trim();
      const mood = filter.value;
      const currentRequest = ++requestId;

      grid.innerHTML = `
        <article class="card card-pad" role="status" aria-live="polite">
          <p class="p" style="margin:0">Loading your journal history…</p>
        </article>
      `;

      try {
        const items = await fetchHistory(q, mood);
        if (currentRequest !== requestId) return;
        renderHistoryCards(grid, items, { isFallback: false });
      } catch {
        if (currentRequest !== requestId) return;
        const filtered = filterHistoryItems(HISTORY_DUMMY, q, mood);
        renderHistoryCards(grid, filtered, { isFallback: true });
      }
    };

    const scheduleApply = () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(apply, 250);
    };

    search.addEventListener('input', scheduleApply);
    filter.addEventListener('change', apply);
    apply();
  };

  // -------------------------
  // Smooth scrolling fallback
  // -------------------------
  const initSmoothScrolling = () => {
    document.addEventListener('click', (e) => {
      const a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
      if (!a) return;
      const id = a.getAttribute('href');
      const el = id ? document.querySelector(id) : null;
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  // -------------------------
  // Boot
  // -------------------------
  document.addEventListener('DOMContentLoaded', () => {
    initNavbar();
    initReveal();
    initDate();
    initMoodSelection();
    initPrompt();
    initCounters();
    initReflection();
    initHistory();
    initSmoothScrolling();

    const yearEl = document.getElementById('year');
    if (yearEl) yearEl.textContent = String(new Date().getFullYear());
  });
})();
