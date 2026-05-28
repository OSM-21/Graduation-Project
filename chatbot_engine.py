# chatbot_engine.py
import json
import pandas as pd # type: ignore
import numpy as np # type: ignore
from sentence_transformers import SentenceTransformer # type: ignore
from sklearn.metrics.pairwise import cosine_similarity # type: ignore
import sys
import os

# --- 1. الإعدادات وتحميل البيانات ---

# التأكد من وجود ملف البيانات في نفس المجلد
QA_FILE = 'questions_answers.json'
if not os.path.exists(QA_FILE):
    print(f"❌ خطأ: ملف البيانات {QA_FILE} غير موجود.")
    print("يرجى التأكد من أن الملف موجود في نفس مجلد هذا الكود.")
    sys.exit(1)

# تحميل البيانات من ملف JSON
try:
    with open(QA_FILE, 'r', encoding='utf-8') as f:
        qa_data = json.load(f)
except Exception as e:
    print(f"❌ خطأ في قراءة ملف JSON: {e}")
    sys.exit(1)

# تحويل البيانات إلى تنسيق جدول (DataFrame) لتسهيل التعامل معها وتوليد المتجهات
training_data = []
for item in qa_data:
    intent = item['intent']
    answer = item['answer']
    # إضافة كل صياغة سؤال كمدخل منفصل
    for question in item['question']:
        training_data.append({
            'question': question,
            'intent': intent,
            'answer': answer
        })

df = pd.DataFrame(training_data)

# --- 2. تهيئة النموذج وتوليد المتجهات ---

# النموذج المستخدم: paraphrase-multilingual-mpnet-base-v2
# هو نموذج فعال لـ (Embeddings) يدعم اللغة العربية بشكل ممتاز.
print("🧠 جاري تحميل نموذج الذكاء الاصطناعي...")
try:
    # تحميل النموذج (يتم مرة واحدة عند بدء التشغيل)
    model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
except Exception as e:
    print(f"❌ فشل تحميل نموذج Sentence Transformer. تأكد من اتصالك بالإنترنت. الخطأ: {e}")
    sys.exit(1)

print("✨ تم تحميل النموذج بنجاح.")
print("جاري تجهيز قاعدة المعرفة (توليد المتجهات)...")

# توليد المتجهات لجميع أسئلة التدريب
training_embeddings = model.encode(df['question'].tolist(), convert_to_numpy=True, show_progress_bar=False)
df['embedding'] = training_embeddings.tolist()

print(f"✅ تم تجهيز قاعدة المعرفة ({len(df)} سؤال تدريبي جاهز).")

# --- 3. دالة تحديد النية واسترجاع الإجابة ---

def get_chatbot_response(user_query, df, model, threshold=0.70):
    """
    تحديد النية (Intent) من سؤال المستخدم واسترجاع الإجابة المناسبة.
    
    Args:
        user_query (str): السؤال الذي طرحه المستخدم.
        df (pd.DataFrame): جدول البيانات المحملة مع المتجهات.
        model (SentenceTransformer): نموذج توليد المتجهات.
        threshold (float): عتبة الثقة (من 0 إلى 1) لتحديد ما إذا كانت النية مؤكدة.
        
    Returns:
        str: الإجابة المناسبة.
    """
    # 1. تحويل سؤال المستخدم إلى متجه
    user_embedding = model.encode([user_query], convert_to_numpy=True)[0]

    # 2. حساب التشابه (Cosine Similarity)
    similarities = cosine_similarity(
        user_embedding.reshape(1, -1),
        np.array(df['embedding'].tolist())
    )

    # 3. العثور على أعلى درجة تشابه
    best_score_index = np.argmax(similarities)
    best_score = similarities[0, best_score_index]
    
    # استخراج نية السؤال الأكثر تشابهاً
    matched_intent = df.iloc[best_score_index]['intent']

    # 4. تحديد الإجابة بناءً على عتبة الثقة (Threshold)
    if best_score >= threshold:
        # إذا كانت الثقة عالية، نرجع الإجابة الخاصة بالنية المطابقة
        final_answer = df[df['intent'] == matched_intent]['answer'].iloc[0]
        return final_answer
    else:
        # إذا كانت الثقة ضعيفة، نرجع رسالة عدم الفهم (unknown intent)
        # البحث عن الإجابة المخصصة للـ 'unknown'
        unknown_entry = next((item for item in qa_data if item['intent'] == 'unknown'), None)
        if unknown_entry:
            return unknown_entry['answer']
        else:
            return "لم أفهم سؤالك تمامًا. هل يمكنك إعادة صياغته أو توضيحه أكثر؟"

# --- 4. تشغيل حلقة المحادثة في التيرمينال ---

def run_chatbot_loop():
    print("=========================================")
    print("🤖 الشات بوت الأكاديمي جاهز للعمل. ")
    print("💡 يمكنك الآن طرح أسئلة بصيغ مختلفة.")
    print("اكتب 'خروج' لإنهاء الجلسة.")
    print("=========================================")
    
    while True:
        try:
            user_input = input("أنت: ")
        except EOFError:
            # لمعالجة إنهاء الإدخال بشكل مفاجئ
            break
        
        if user_input.lower() in ['خروج', 'exit', 'quit']:
            print("👋 مع السلامة! تم إيقاف الشات بوت.")
            break

        # الحصول على الرد
        response = get_chatbot_response(user_input, df, model)
        
        print(f"البوت: {response}")

# نقطة بداية تشغيل البرنامج
if __name__ == "__main__":
    run_chatbot_loop()