import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken } from "./api";

const ar = {
  "Ma'ak": "معك",
  "Welcome back": "أهلاً بعودتك",
  "Sign in to Ma'ak. Your role is remembered from sign-up.": "سجّل الدخول إلى معك. دورك محفوظ من التسجيل.",
  "Phone code": "رمز الهاتف",
  "Email + password": "البريد وكلمة السر",
  "Phone number": "رقم الهاتف",
  "Email": "البريد الإلكتروني",
  "Password": "كلمة السر",
  "Send code": "إرسال الرمز",
  "Send by WhatsApp": "الإرسال عبر واتساب",
  "Sign in": "دخول",
  "Create an account": "إنشاء حساب",
  "Emergency aid works without signing in": "المساعدة الطارئة تعمل بدون تسجيل",
  "Demo code": "رمز التجربة",
  "Try a role": "جرّب دوراً",
  "Create your account": "أنشئ حسابك",
  "I am signing up as": "أسجّل بصفتي",
  "Full name": "الاسم الكامل",
  "Continue": "متابعة",
  "Already have an account? Sign in": "لديك حساب؟ دخول",
  "Verify who you are": "أكّد هويتك",
  "Specialty": "الاختصاص",
  "License number": "رقم الترخيص",
  "Licensing body": "جهة الترخيص",
  "License expires": "انتهاء الترخيص",
  "Upload a document": "ارفع مستنداً",
  "Scan license card": "مسح بطاقة الترخيص",
  "Submit for review": "إرسال للمراجعة",
  "Order of Physicians card": "بطاقة نقابة الأطباء",
  "Hold the card inside the frame. Ma'ak stores the image for a reviewer. It does not read the card by itself.": "ضع البطاقة داخل الإطار. معك يحفظ الصورة لمراجع بشري ولا يقرأ البطاقة آلياً.",
  "Card detected — hold still": "تم التقاط البطاقة",
  "Back": "رجوع",
  "Check your details": "راجع بياناتك",
  "Confirm and continue": "تأكيد ومتابعة",
  "Account created": "تم إنشاء الحساب",
  "Documents received": "تم استلام المستندات",
  "Checking with the licensing body": "قيد المراجعة لدى جهة الترخيص",
  "Approved — full access": "موافق عليه — وصول كامل",
  "Your health record, wherever you go.": "سجلك الصحي معك، أينما ذهبت.",
  "Sign up": "تسجيل",
  "I already have an account": "لدي حساب",
  "Scan emergency code": "مسح رمز الطوارئ",
  "Home": "الرئيسية",
  "Passport": "الجواز الصحي",
  "Care": "الاحتياجات",
  "Requests": "الطلبات",
  "Profile": "الملف",
  "Tasks": "المهام",
  "Notices": "الإعلانات",
  "Support": "الدعم",
  "Needs": "الاحتياجات",
  "My gifts": "تبرعاتي",
  "Family": "العائلة",
  "Add a family member": "إضافة فرد من العائلة",
  "Relationship": "صلة القرابة",
  "Date of birth": "تاريخ الولادة",
  "Save": "حفظ",
  "Near you": "بالقرب منك",
  "Quick actions": "إجراءات سريعة",
  "Health passport": "الجواز الصحي",
  "Care needs": "الاحتياجات الصحية",
  "Request transport": "طلب نقل",
  "File a complaint": "تقديم شكوى",
  "Critical": "حرج",
  "Not yet confirmed": "بانتظار التأكيد",
  "Confirmed": "مؤكد",
  "Conditions": "الحالات",
  "Medications": "الأدوية",
  "Records": "السجلات",
  "Vaccines": "اللقاحات",
  "Access": "الوصول",
  "All": "الكل",
  "Add a record": "إضافة سجل",
  "Title": "العنوان",
  "Details": "التفاصيل",
  "Date": "التاريخ",
  "Facility": "المركز الطبي",
  "Clinician name": "اسم الطبيب",
  "Result": "النتيجة",
  "Patient-entered": "أدخله المريض",
  "Clinician-entered": "أدخله الطبيب",
  "Attach a file": "إرفاق ملف",
  "Who can see this passport": "من يمكنه رؤية الجواز",
  "Grant access": "منح الوصول",
  "Revoke": "سحب الوصول",
  "Emergency card": "بطاقة الطوارئ",
  "Save on this phone": "احفظها على هذا الهاتف",
  "Saved on this phone": "حُفظت على هذا الهاتف",
  "Oxygen and power": "الأكسجين والكهرباء",
  "Device": "الجهاز",
  "Supply percent": "نسبة المخزون",
  "Hours left": "الساعات المتبقية",
  "Add dependency": "إضافة اعتماد طبي",
  "Food and supplies": "الغذاء والمستلزمات",
  "Report a shortage": "الإبلاغ عن نقص",
  "Dialysis": "غسيل الكلى",
  "Available seats": "مقاعد متاحة",
  "Pregnancy": "الحمل",
  "Weeks": "أسابيع",
  "Due date": "موعد الولادة",
  "High-risk notes": "ملاحظات الخطورة",
  "Shelters with backup power": "مراكز لديها كهرباء احتياطية",
  "Request a move": "طلب نقل",
  "Suggested from reported supplies. A coordinator or clinician confirms it.": "اقتراح من المستلزمات المبلّغ عنها. يؤكده منسق أو طبيب.",
  "This supports a decision. It does not assign care.": "هذا يدعم القرار ولا يوزّع الرعاية تلقائياً.",
  "Transport": "النقل",
  "Destination": "الوجهة",
  "Wheelchair access": "يحتاج كرسياً متحركاً",
  "Link an appointment": "ربط بموعد",
  "Appointments at risk": "مواعيد بلا نقل",
  "Mental health support": "دعم نفسي",
  "Reason": "السبب",
  "Includes bullying": "يشمل تنمّراً",
  "Flag for support": "طلب دعم",
  "Complaints": "الشكاوى",
  "Category": "الفئة",
  "How it arrived": "كيف وصلت",
  "What happened": "ماذا حدث",
  "Submit": "إرسال",
  "Status": "الحالة",
  "Accept": "قبول",
  "Decline": "رفض",
  "Complete": "إتمام",
  "Where help is needed": "حيث المساعدة مطلوبة",
  "Suggested if you have no recipient in mind": "اقتراح إذا لم تختر مستفيداً",
  "You still choose. Nothing is assigned automatically.": "أنت تختار. لا يتم تخصيص التبرع تلقائياً.",
  "Give": "تبرّع",
  "Amount": "المبلغ",
  "Supplies": "المستلزمات",
  "Money": "مال",
  "Overview": "نظرة عامة",
  "Residents": "المقيمون",
  "Shortages": "النواقص",
  "Exchange": "التبادل",
  "Donations": "التبرعات",
  "Volunteers": "المتطوعون",
  "Reports": "التقارير",
  "Shelters": "المراكز",
  "NGOs": "المنظمات",
  "Sign out": "خروج",
  "Language": "اللغة",
  "Capacity": "السعة",
  "Occupancy": "الإشغال",
  "Update shelter": "تحديث المركز",
  "Add item": "إضافة مادة",
  "Backup power": "كهرباء احتياطية",
  "Accessible spaces": "أماكن مهيأة",
  "Find a patient": "ابحث عن مريض",
  "Add a clinician record": "إضافة سجل طبي",
  "Save to health passport": "حفظ في الجواز الصحي",
  "Patients grant access. You cannot open a passport they have not shared.": "المريض يمنح الوصول. لا يمكن فتح جواز لم يشاركه.",
  "National shelter overview": "نظرة وطنية على المراكز",
  "Demand forecast": "تقدير الطلب",
  "Planning estimate from reported shortages. A person decides what to send.": "تقدير للتخطيط من النواقص المبلّغ عنها. الشخص يقرر ما يُرسل.",
  "High-risk counts": "أعداد الفئات الأكثر عرضة",
  "Counts only. Individual health passports stay with the patient.": "أعداد فقط. جوازات الصحة الفردية تبقى مع المريض.",
  "Connect an NGO": "ربط منظمة",
  "Verification queue": "طلبات التحقق",
  "Approve": "موافقة",
  "Outbreak reports": "بلاغات العدوى",
  "This flags a cluster for public health staff. It does not declare an outbreak.": "هذا ينبّه فرق الصحة العامة ولا يعلن وباءً.",
  "Distribution gaps": "فجوات التوزيع",
  "Emergency summary": "ملخص الطوارئ",
  "No internet is required for a summary saved on this phone.": "الملخص المحفوظ على الهاتف لا يحتاج إلى إنترنت.",
  "Blood type": "زمرة الدم",
  "Allergies": "الحساسية",
  "Helper type": "نوع المساعدة",
  "Shelter": "المركز",
  "Region": "المنطقة",
  "Priority": "الأولوية",
  "Mark resolved": "تعليم كمحلول",
  "Escalate": "تصعيد",
  "Received": "تم الاستلام",
  "Under review": "قيد المراجعة",
  "Being addressed": "قيد المعالجة",
  "Resolved": "تم الحل",
};

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(localStorage.getItem("maak_lang") || "en");
  useEffect(() => {
    localStorage.setItem("maak_lang", lang);
    document.documentElement.lang = lang === "ar" ? "ar" : "en";
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);
  const value = useMemo(
    () => ({
      lang,
      setLang: setLangState,
      t: (key) => (lang === "ar" && ar[key]) || key,
    }),
    [lang]
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const expired = () => setUser(null);
    window.addEventListener("maak-session-expired", expired);
    return () => window.removeEventListener("maak-session-expired", expired);
  }, []);

  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api("/auth/me")
      .then((data) => setUser(data.user))
      .catch(() => {
        setToken(null);
        setUser(null);
      })
      .finally(() => setReady(true));
  }, []);

  async function login(body) {
    const data = await api("/auth/login", { method: "POST", body: JSON.stringify(body) });
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }

  async function register(body) {
    const data = await api("/auth/register", { method: "POST", body: JSON.stringify(body) });
    setToken(data.token);
    setUser(data.user);
    return data.user;
  }

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    setToken(null);
    setUser(null);
  }

  function refresh(next) {
    setUser(next);
  }

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
