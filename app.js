const chatBox        = document.getElementById('chat-box');
const userInput      = document.getElementById('userInput');
const sendBtn        = document.getElementById('sendBtn');
const micBtn         = document.getElementById('micBtn');
const speakToggle    = document.getElementById('speakToggle');

const conversationIdInput = document.getElementById('conversationId');
const conversationsList   = document.getElementById('conversationsList');
const newChatBtn          = document.getElementById('newChatBtn');

const chatLayout          = document.getElementById('chatLayout');
const toggleSidebarBtn    = document.getElementById('toggleSidebarBtn');

let currentConversationId = conversationIdInput && conversationIdInput.value
  ? conversationIdInput.value
  : null;

// ==============================
// زر إظهار / إخفاء الشريط الجانبي
// ==============================
if (toggleSidebarBtn && chatLayout) {
  toggleSidebarBtn.addEventListener('click', () => {
    chatLayout.classList.toggle('collapsed');
    // تغيير شكل الزر فقط (اختياري)
    if (chatLayout.classList.contains('collapsed')) {
      toggleSidebarBtn.textContent = '☰'; // لفتح
    } else {
      toggleSidebarBtn.textContent = '☰'; // نفس الأيقونة (تقدر تغيرها لسهم)
    }
  });
}

// ==============================
// إضافة رسالة (الكتابة المتدرجة)
// ==============================
function addMessage(text, cls = 'bot') {
  if (!chatBox) return;
  const div = document.createElement('div');
  div.className = 'message ' + cls;
  chatBox.appendChild(div);

  let i = 0;
  function type() {
    if (i <= text.length) {
      // 🛑🛑 تم إصلاح هذا السطر سابقاً (لتمكين الروابط والتنسيق) 🛑🛑
      div.innerHTML = text.slice(0, i); 
      i++;
      setTimeout(type, 10);
    }
  }
  type();
  chatBox.scrollTop = chatBox.scrollHeight;
  return div;
}

// ==============================
// تمييز المحادثة النشطة في القائمة
// ==============================
function setActiveConversationItem(id) {
  if (!conversationsList) return;
  const items = conversationsList.querySelectorAll('.conv-item');
  items.forEach(li => {
    li.classList.toggle('active', li.dataset.id === String(id));
  });
}

// ==============================
// تحميل محادثة من الشريط الجانبي
// ==============================
async function loadConversation(convId) {
  if (!convId || !chatBox) return;

  try {
    const res = await fetch(`/conversation/${convId}`);
    if (!res.ok) return;
    const data = await res.json();

    chatBox.innerHTML = '';
    if (data.messages && data.messages.length) {
      data.messages.forEach(msg => {
        addMessage(msg.text, msg.sender === 'user' ? 'user' : 'bot');
      });
    } else {
      addMessage('👋 أهلاً بك! اكتب سؤالك لبدء المحادثة.', 'bot');
    }

    currentConversationId = data.id;
    if (conversationIdInput) {
      conversationIdInput.value = currentConversationId;
    }
    setActiveConversationItem(currentConversationId);
  } catch (e) {
    console.error(e);
  }
}

// ==============================
// إنشاء محادثة جديدة (زر +)
// ==============================
async function createNewConversation() {
  if (!chatBox) return;
  try {
    const res = await fetch('/conversation/new', { method: 'POST' });
    const data = await res.json();

    currentConversationId = data.conversation_id;
    if (conversationIdInput) {
      conversationIdInput.value = currentConversationId;
    }

    // نظف الشات وابدأ ترحيب جديد
    chatBox.innerHTML = '';
    addMessage('👋 محادثة جديدة بدأت، اكتب سؤالك.', 'bot');

    if (conversationsList) {
      // احذف سطر "لا توجد محادثات بعد" لو موجود
      const empty = conversationsList.querySelector('.empty');
      if (empty) empty.remove();

      // أضف المحادثة الجديدة أعلى القائمة
      const li = document.createElement('li');
      li.className = 'conv-item active';
      li.dataset.id = data.conversation_id;
      li.textContent = data.title || 'محادثة جديدة';

      li.addEventListener('click', () => loadConversation(data.conversation_id));

      // شيل active من الباقي
      conversationsList.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
      conversationsList.prepend(li);
    }
  } catch (e) {
    console.error(e);
  }
}

// ==============================
// إرسال رسالة للمسار /chat (مع conversation_id)
// ==============================
async function send() {
  const text = userInput ? userInput.value.trim() : '';
  if (!text || !chatBox) return;

  addMessage(text, 'user');
  if (userInput) userInput.value = '';

  const thinking = addMessage('...', 'bot');

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        conversation_id: currentConversationId
      })
    });

    const data = await res.json();
    if (thinking) thinking.remove();

    addMessage(data.answer, 'bot');

    // لو هذه أول رسالة في محادثة جديدة، حدّث الـ conversation_id والقائمة
    if (data.conversation_id) {
      currentConversationId = data.conversation_id;
      if (conversationIdInput) {
        conversationIdInput.value = currentConversationId;
      }

      if (conversationsList) {
        let li = conversationsList.querySelector(`.conv-item[data-id="${data.conversation_id}"]`);
        if (!li) {
          const empty = conversationsList.querySelector('.empty');
          if (empty) empty.remove();

          li = document.createElement('li');
          li.className = 'conv-item active';
          li.dataset.id = data.conversation_id;
          li.textContent = data.title || 'محادثة جديدة';
          li.addEventListener('click', () => loadConversation(data.conversation_id));
          conversationsList.prepend(li);
        } else {
          // حدّث العنوان لو كان "محادثة جديدة"
          if (data.title && li.textContent === 'محادثة جديدة') {
            li.textContent = data.title;
          }
        }
        setActiveConversationItem(data.conversation_id);
      }
    }

    // 🛑🛑🛑 تم وضع وظيفة TTS في تعليق (لحل مشكلة الخطأ) 🛑🛑🛑
    /*
    if (speakToggle && speakToggle.checked) {
      const ttsRes = await fetch('/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: data.answer })
      });
      const blob = await ttsRes.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
    }
    */
    // 🛑🛑🛑 نهاية وظيفة TTS 🛑🛑🛑

  } catch (e) {
    console.error(e);
    if (thinking) thinking.remove();
    // 🛑 هذا هو السطر الذي كان يرسل رسالة الخطأ 🛑
    addMessage('حصل خطأ، حاول مرة أخرى.', 'bot'); 
  }
}

// أحداث الإرسال
sendBtn?.addEventListener('click', send);
userInput?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') send();
});

// ربط عناصر القائمة الجانبية الموجودة من السيرفر
if (conversationsList) {
  conversationsList.querySelectorAll('.conv-item').forEach(li => {
    if (!li.classList.contains('empty')) {
      li.addEventListener('click', () => {
        const id = li.dataset.id;
        loadConversation(id);
      });
    }
  });
}

// زر محادثة جديدة
newChatBtn?.addEventListener('click', createNewConversation);

// ==============================
// إدخال صوتي (نفس كودك السابق)
// ==============================
let recognition;
if ('webkitSpeechRecognition' in window) {
  recognition = new webkitSpeechRecognition();
  recognition.lang = 'ar-SA';
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.onresult = function (e) {
    const txt = e.results[0][0].transcript;
    if (userInput) userInput.value = txt;
  };
}

micBtn?.addEventListener('click', () => {
  if (recognition) {
    recognition.start();
  } else {
    alert('المتصفح لا يدعم التعرف على الصوت.');
  }
});

// ==============================
// تقييم من القائمة اليمينية
// ==============================
document.querySelectorAll(".rate-btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const convId = btn.parentElement.dataset.conv;
    const value  = parseInt(btn.dataset.value);

    const res = await fetch("/rate_conversation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: convId, value: value })
    });

    // بعد التقييم — استبدل الأزرار بكلمة "تم التقييم"
    const parent = btn.parentElement;
    parent.innerHTML = `<span class="rated-label">تم التقييم ✔</span>`;
  });
});