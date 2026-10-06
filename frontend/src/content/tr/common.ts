import type { CommonContent } from "@/lib/i18n/types";

export const commonContent: CommonContent = {
  brandName: "Health AI Platform Pro",
  brandTagline: "Modern sağlık ekipleri için klinik karar destek platformu",
  nav: {
    home: "Ana sayfa",
    login: "Giriş yap",
    register: "Hesap oluştur",
    patients: "Hastalar",
    management: "Klinik yönetimi",
    logout: "Çıkış yap",
    skipToContent: "Ana içeriğe geç",
    openMenu: "Menüyü aç",
    closeMenu: "Menüyü kapat",
  },
  common: {
    loading: "Yükleniyor…",
    error: "Bir hata oluştu.",
    retry: "Tekrar dene",
    back: "Geri",
    notFound: "Bulunamadı.",
    unauthorized: "Devam etmek için giriş yapın.",
    forbidden: "Bu sayfaya erişim yetkiniz yok.",
  },
  language: {
    switcherLabel: "Dil",
  },
  footer: {
    tagline: "Güvenli sağlık karar destek yazılımı.",
    disclaimer:
      "Bu platform yalnızca karar destek bilgisi sunar. Profesyonel tıbbi değerlendirmenin yerini almaz.",
    copyright: "Health AI Platform Pro. Tüm hakları saklıdır.",
    links: {
      privacy: "Gizlilik",
      terms: "Koşullar",
      contact: "İletişim",
    },
  },
  landing: {
    badge: "Klinik karar destek platformu",
    heroTitle: "Sağlık ekipleri için daha akıllı klinik iş akışları",
    heroDescription:
      "Sağlık profesyonelleri için tasarlanmış güvenli bir çalışma alanında hasta kayıtlarını, sağlık içgörülerini ve risk değerlendirmelerini yönetin.",
    primaryCta: "Başlayın",
    secondaryCta: "Giriş yap",
    secondaryCtaAuthenticated: "Hastalarımı görüntüle",
    featuresTitle: "Sorumlu sağlık yapay zekası için tasarlandı",
    features: [
      {
        title: "Yapılandırılmış hasta verileri",
        description:
          "Randevuları, tıbbi kayıtları ve sağlık ölçümlerini yetkilendirilmiş erişim kontrolleriyle düzenleyin.",
      },
      {
        title: "Karar destek analitiği",
        description:
          "Tanı sunmadan klinik değerlendirmeyi destekleyen trendleri ve içgörüleri inceleyin.",
      },
      {
        title: "Ölçeklenebilir teknik temel",
        description:
          "FastAPI, JWT kimlik doğrulama, PostgreSQL kalıcılığı ve gözlemlenebilirlik ile büyüyen klinik iş yükleri için modüler bir mimari.",
      },
    ],
    trustTitle: "Klinik güvenlik öncelikli tasarım",
    trustPoints: [
      "Demo içeriğinde hasta tanımlayıcı bilgisi yok",
      "Karar destek çıktılarında açık tıbbi uyarılar",
      "Ortam yapılandırması üzerinden güvenli API entegrasyonu",
    ],
  },
  auth: {
    loginTitle: "Giriş yap",
    loginDescription: "Health AI Platform Pro hesabınızla çalışma alanınıza erişin.",
    registerTitle: "Hesap oluştur",
    registerDescription: "Klinik çalışma alanınız için profesyonel bir hesap oluşturun.",
    emailLabel: "E-posta adresi",
    emailPlaceholder: "siz@klinik.ornek",
    passwordLabel: "Şifre",
    passwordPlaceholder: "Şifrenizi girin",
    confirmPasswordLabel: "Şifreyi onayla",
    confirmPasswordPlaceholder: "Şifrenizi tekrar girin",
    loginSubmit: "Giriş yap",
    registerSubmit: "Hesap oluştur",
    noAccount: "Hesabınız yok mu?",
    hasAccount: "Zaten hesabınız var mı?",
    phaseNotice:
      "Yalnızca karar destek. Demo ortamlarda gerçek hasta tanımlayıcıları girmeyin.",
    firstNameLabel: "Ad",
    firstNamePlaceholder: "Ayşe",
    lastNameLabel: "Soyad",
    lastNamePlaceholder: "Yılmaz",
    loginError: "Giriş başarısız. E-posta ve şifrenizi kontrol edin.",
    registerError: "Kayıt başarısız. Farklı e-posta veya daha güçlü şifre deneyin.",
    passwordMismatch: "Şifreler eşleşmiyor.",
    genericError: "Bir sorun oluştu. Lütfen tekrar deneyin.",
    logout: "Çıkış yap",
    signedInAs: "Oturum:",
    emailNotVerified:
      "Giriş yapmadan önce e-postanızı doğrulayın. Gelen kutunuzu kontrol edin veya yeni doğrulama mesajı isteyin.",
    checkEmailTitle: "E-postanızı kontrol edin",
    checkEmailDescription:
      "Adresinize bir doğrulama bağlantısı gönderdik. Hesabınızı etkinleştirmek için bağlantıyı açın, ardından giriş yapın.",
    checkEmailResend: "Doğrulama e-postasını yeniden gönder",
    checkEmailResendSuccess:
      "Bu e-posta için kayıtlı bir hesap varsa doğrulama mesajı gönderildi.",
    checkEmailBackToLogin: "Girişe dön",
    verifyEmailTitle: "E-posta doğrulama",
    verifyEmailSuccess: "E-postanız doğrulandı. Artık giriş yapabilirsiniz.",
    verifyEmailInvalid: "Bu doğrulama bağlantısı geçersiz veya süresi dolmuş.",
    verifyEmailMissingToken: "Doğrulama jetonu bulunamadı.",
    verifyEmailWorking: "E-postanız doğrulanıyor…",
  },
  patients: {
    title: "Hastalar",
    description: "Klinik zaman tünelini görüntülemek için bir hasta seçin.",
    empty: "Hasta bulunamadı. API ile hasta ekleyin veya backend'de demo veri oluşturun.",
    viewTimeline: "Zaman tünelini görüntüle",
    viewPatient: "Hasta detayı",
    name: "Ad",
    dateOfBirth: "Doğum tarihi",
    gender: "Cinsiyet",
    loadError: "Hastalar yüklenemedi.",
    genders: {
      male: "Erkek",
      female: "Kadın",
      other: "Diğer",
    },
  },
  patientHub: {
    title: "Hasta özeti",
    description: "Atanmış hasta bilgilerini, risk geçmişini ve raporları inceleyin.",
    decisionSupportTitle: "Yalnızca klinik karar destek",
    decisionSupportBody:
      "Bu sistem tıbbi tanı koymaz. Bilgiler klinik karar destek amaçlıdır ve profesyonel tıbbi değerlendirmenin yerini almaz.",
    clinicalTimeline: "Klinik zaman tüneli",
    downloadPdf: "PDF raporu indir",
    downloadingPdf: "PDF hazırlanıyor…",
    pdfError: "PDF raporu indirilemedi.",
    pdfSuccess: "PDF indirme başlatıldı.",
    riskHistoryTitle: "Risk değerlendirme geçmişi",
    riskHistoryEmpty: "Bu hasta için henüz kayıtlı risk değerlendirmesi yok.",
    riskHistoryLoadError: "Risk geçmişi yüklenemedi.",
    clinicalSummaryTitle: "Klinik özet",
    clinicalSummarySubtitle: "Son dönem klinik görünüm",
    clinicalSummaryPeriodViewSuffix: "klinik görünümü",
    clinicalSummaryDescription: "Mevcut kayıtların kısa karar destek özeti.",
    clinicalSummaryEmpty: "Özet oluşturmak için yeterli klinik veri bulunmuyor.",
    clinicalSummaryLoadError: "Klinik özet yüklenemedi.",
    clinicalSummaryDisclaimer:
      "Bu özet klinik karar destek amaçlıdır; tanı veya tedavi önerisi değildir.",
    clinicalSummaryItemLabels: {
      fasting_glucose_trend: "Açlık kan şekeri",
      post_meal_glucose_trend: "Yemek sonrası kan şekeri",
      blood_pressure_trend: "Kan basıncı",
      heart_rate_trend: "Nabız",
      laboratory_summary: "Laboratuvar",
      imaging_summary: "Görüntüleme",
      clinical_visit_summary: "Klinik muayene notu",
      neurological_follow_up_summary: "Nörolojik takip",
      medication_treatment_follow_up: "İlaç ve takip",
      upcoming_follow_up: "Yaklaşan kontrol",
      overdue_follow_up: "Gecikmiş takip",
    },
    clinicalSummaryTrendMessages: {
      stable_in_range:
        "{period_range} arasında kayıtlı {count} karşılaştırılabilir {context} ölçümünde stabil seyir izleniyor (bilgilendirme).",
      stable_on_date:
        "{period_date} tarihinde kayıtlı {count} karşılaştırılabilir {context} ölçümünde stabil seyir izleniyor (bilgilendirme).",
      increasing_in_range:
        "{period_range} arasında kayıtlı {count} karşılaştırılabilir {context} ölçümünde artış eğilimi izleniyor (bilgilendirme).",
      increasing_on_date:
        "{period_date} tarihinde kayıtlı {count} karşılaştırılabilir {context} ölçümünde artış eğilimi izleniyor (bilgilendirme).",
      decreasing_in_range:
        "{period_range} arasında kayıtlı {count} karşılaştırılabilir {context} ölçümünde azalış eğilimi izleniyor (bilgilendirme).",
      decreasing_on_date:
        "{period_date} tarihinde kayıtlı {count} karşılaştırılabilir {context} ölçümünde azalış eğilimi izleniyor (bilgilendirme).",
      recorded_no_direction_in_range:
        "{period_range} arasında {count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü değerlendirme için yeterli veri bulunmuyor.",
      recorded_no_direction_on_date:
        "{period_date} tarihinde {count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü değerlendirme için yeterli veri bulunmuyor.",
      insufficient_data_in_range:
        "{period_range} arasında {count} karşılaştırılabilir {context} ölçümü kayıtlı; trend değerlendirilmedi.",
      insufficient_data_on_date:
        "{period_date} tarihinde {count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü değerlendirme için yeterli veri bulunmuyor.",
    },
    clinicalSummaryItemMessages: {
      trend_hybrid_stable_in_range:
        "{period_range} arasında kayıtlı {count} karşılaştırılabilir {context} ölçümünde stabil seyir izleniyor (bilgilendirme).",
      trend_hybrid_stable_on_date:
        "{period_date} tarihinde kayıtlı {count} karşılaştırılabilir {context} ölçümünde stabil seyir izleniyor (bilgilendirme).",
      trend_hybrid_increasing_in_range:
        "{period_range} arasında kayıtlı {count} karşılaştırılabilir {context} ölçümünde artış eğilimi izleniyor (bilgilendirme).",
      trend_hybrid_increasing_on_date:
        "{period_date} tarihinde kayıtlı {count} karşılaştırılabilir {context} ölçümünde artış eğilimi izleniyor (bilgilendirme).",
      trend_hybrid_decreasing_in_range:
        "{period_range} arasında kayıtlı {count} karşılaştırılabilir {context} ölçümünde azalış eğilimi izleniyor (bilgilendirme).",
      trend_hybrid_decreasing_on_date:
        "{period_date} tarihinde kayıtlı {count} karşılaştırılabilir {context} ölçümünde azalış eğilimi izleniyor (bilgilendirme).",
      trend_hybrid_no_direction_in_range:
        "{period_range} arasında {count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü değerlendirme için yeterli veri bulunmuyor.",
      trend_hybrid_no_direction_on_date:
        "{period_date} tarihinde {count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü değerlendirme için yeterli veri bulunmuyor.",
      trend_hybrid_insufficient_in_range:
        "{period_range} arasında {count} karşılaştırılabilir {context} ölçümü kayıtlı; trend değerlendirilmedi.",
      trend_hybrid_insufficient_on_date:
        "{period_date} tarihinde {count} karşılaştırılabilir {context} ölçümü kayıtlı; yönlü değerlendirme için yeterli veri bulunmuyor.",
      hba1c_summary: "En güncel HbA1c ({record_date}): %{value} kayıtlı.",
      diabetes_metabolic_lab_on_file:
        "En güncel metabolik laboratuvar paneli ({record_date}) kayıtlarda mevcut.",
      diabetes_medication_documented:
        "Diyabet ilaç ve takip planı klinik kayıtlarda belgelenmiştir.",
      diabetes_follow_up_plan_documented:
        "Evde kan şekeri takibi, üç aylık HbA1c kontrolü ve yaşam tarzı danışmanlığına ilişkin takip planı kayıtlarda yer almaktadır.",
      stroke_neurological_follow_up_documented:
        "Nörolojik takip ve inme sonrası klinik değerlendirme ({record_date}) kayıtlarda belgelenmiştir.",
      brain_imaging_on_file: "Beyin görüntüleme raporu ({record_date}) klinik kayıtlarda mevcut.",
      stroke_secondary_prevention_documented:
        "Sekonder korunma ve takip planı klinik kayıtlarda belgelenmiştir.",
      lipid_panel_summary:
        "En güncel lipid paneli ({record_date}): LDL {ldl} mg/dL ve HDL {hdl} mg/dL kayıtlı.",
      lipid_panel_with_triglycerides:
        "En güncel lipid paneli ({record_date}): LDL {ldl} mg/dL, HDL {hdl} mg/dL ve trigliserid {triglycerides} mg/dL kayıtlı.",
      echocardiography_on_file:
        "Ekokardiyografi raporu ({record_date}) kayıtlarda mevcut.",
      imaging_report_on_file: "Görüntüleme raporu ({record_date}) kayıtlarda mevcut.",
      heart_rate_monitoring_insufficient_trend:
        "Dinlenme nabzı için mevcut kayıtlar izlenmektedir; yönlü değerlendirme için yeterli karşılaştırılabilir veri bulunmuyor.",
      medication_treatment_summary: "{detail}",
      cardiac_care_plan_documented:
        "Kan basıncı takibi, 3 ay içinde lipid kontrolü ve aktiviteye ilişkin takip planı kayıtlarda yer almaktadır.",
      medication_plan_on_file: "İlaç ve takip planı klinik kayıtlarda mevcut.",
      upcoming_follow_up_date: "Yaklaşan kontrol randevusu: {date}.",
      overdue_follow_up_date:
        "{date} tarihli planlanmış kontrol için sistemde tamamlanma kaydı bulunmuyor.",
      laboratory_on_file: "Laboratuvar sonuçları klinik kayıtlarda mevcut.",
      brain_imaging_summary: "{detail}",
      clinical_visit_summary: "{detail}",
    },
    riskType: "Tür",
    riskLevel: "Düzey",
    assessedAt: "Değerlendirme zamanı",
    score: "Skor",
    factors: "Katkı faktörleri",
    missingInputs: "Eksik girdiler",
    riskDisclaimer:
      "Risk çıktıları kural tabanlı karar destek tahminleridir; tanı veya tedavi planı değildir.",
    active: "Aktif",
    inactive: "Pasif",
    notFoundOrDenied: "Hasta bulunamadı veya bu hastaya erişim yetkiniz yok.",
    loadError: "Hasta bilgileri yüklenemedi.",
    assessmentTypes: {
      diabetes: "Diyabet",
      heart_disease: "Kalp hastalığı",
      stroke: "İnme",
    },
    riskLevels: {
      low: "Düşük",
      moderate: "Orta",
      elevated: "Yüksek",
      high: "Yüksek",
      very_high: "Çok yüksek",
    },
    missingInputLabels: {
      systolic_blood_pressure: "Sistolik tansiyon",
      diastolic_blood_pressure: "Diyastolik tansiyon",
      fasting_blood_glucose: "Açlık kan şekeri",
      blood_glucose: "Kan şekeri",
      height_cm: "Boy",
      stroke_history: "İnme/TIA öyküsü",
    },
    missingInputReasons: {
      systolic_blood_pressure:
        "Seçilen tarih aralığında sistolik tansiyon ölçümü bulunmuyor.",
      diastolic_blood_pressure:
        "Seçilen tarih aralığında diyastolik tansiyon ölçümü bulunmuyor.",
      fasting_blood_glucose:
        "Seçilen tarih aralığında açlık kan şekeri ölçümü bulunmuyor.",
      blood_glucose: "Seçilen tarih aralığında kan şekeri ölçümü bulunmuyor.",
      height_cm: "Hasta için boy bilgisi kayıtlı değil.",
      stroke_history:
        "Seçilen tarih aralığında yapılandırılmış inme veya geçici iskemik atak (TIA) öyküsü kaydı bulunmuyor.",
    },
  },
  timeline: {
    title: "Klinik zaman tüneli",
    description: "Kayıtlı ölçümler, tıbbi kayıtlar ve randevuların salt okunur özeti.",
    sortNotice: "Olaylar eskiden yeniye gösterilir.",
    empty: "Seçilen dönemde timeline olayı yok.",
    loadError: "Klinik timeline yüklenemedi.",
    truncatedNotice: "Liste sınırına ulaşıldığı için bazı olaylar gösterilmedi.",
    filtersTitle: "Filtreler",
    dateFrom: "Başlangıç tarihi",
    dateTo: "Bitiş tarihi",
    applyFilters: "Filtreleri uygula",
    clearFilters: "Filtreleri temizle",
    includeRiskSnapshot: "Güncel risk anlık görüntüsünü dahil et",
    sourceKind: "Kaynak",
    severity: "Önem",
    disclaimer:
      "Bu klinik zaman tüneli, kayıtlı verilerin bilgilendirme amaçlı salt okunur özetidir. Tıbbi tanı, tedavi önerisi veya profesyonel tıbbi değerlendirmenin yerine geçmez. Türetilmiş öğeler, kayıtlı ölçüm ve randevuların kural tabanlı yorumlarıdır. Risk anlık görüntüleri, saklanan klinik geçmiş değil; yalnızca oluşturulma anındaki tek seferlik değerlendirmeyi yansıtır.",
    patientSummary: {
      ageSuffix: "yaş",
    },
    syntheticDemoBanner: "Sentetik demo verileri — gerçek hasta değildir.",
    evaluatedDataPeriod: "Değerlendirilen veri dönemi",
    headlines: {
      "Diagnosis recorded": "Tanı kaydı",
      "Treatment noted": "Tedavi kaydı",
      "Medications noted": "İlaç kaydı",
      "Health measurement": "Sağlık ölçümü",
      "Appointment completed": "Randevu tamamlandı",
      "Appointment scheduled": "Planlanmış randevu",
      "Follow-up overdue": "Gecikmiş takip",
      "Blood glucose trend increasing": "Kan şekeri yükseliş eğiliminde",
      "Blood Glucose trend increasing": "Kan şekeri yükseliş eğiliminde",
      "Comparable measurements insufficient for trend":
        "Karşılaştırılabilir ölçüm sayısı yetersiz",
      "Laboratory result": "Laboratuvar sonucu",
      "Imaging report": "Tetkik raporu",
      "Systolic Pressure trend increasing": "Sistolik tansiyon yükseliş eğiliminde",
      "Diastolic Pressure trend increasing": "Diyastolik tansiyon yükseliş eğiliminde",
      "Clinical record": "Klinik kayıt",
      "Hospitalization recorded": "Hastaneye yatış kaydı",
      "Diabetes risk snapshot (current)": "Diyabet riski (güncel anlık görüntü)",
      "Heart disease risk snapshot (current)": "Kalp hastalığı riski (güncel anlık görüntü)",
      "Stroke risk snapshot (current)": "İnme riski (güncel anlık görüntü)",
    },
    sourceKinds: {
      medical_record: "Tıbbi kayıt",
      health_measurement: "Sağlık ölçümü",
      appointment: "Randevu",
      derived: "Türetilmiş analiz",
      risk_assessment_current_snapshot: "Güncel risk değerlendirmesi",
    },
    severityLevels: {
      info: "Bilgi",
      warning: "Uyarı",
      critical: "Kritik",
    },
    detailPhrases: {
      "Lifestyle modification and blood pressure monitoring":
        "Yaşam tarzı düzenlemesi ve tansiyon takibi",
      "Appointment recorded": "Randevu kaydedildi",
      "Health measurement recorded": "Sağlık ölçümü kaydedildi",
      Hypertension: "Hipertansiyon",
    },
    eventTypes: {
      medical_record_diagnosis: "Tanı kaydı",
      medical_record_lab_result: "Laboratuvar sonucu",
      medical_record_imaging_report: "Tetkik raporu",
      medical_record_treatment: "Tedavi",
      medical_record_medication: "İlaç",
      medical_record_hospitalization: "Hastaneye yatış",
      health_measurement: "Ölçüm",
      appointment_scheduled: "Randevu",
      appointment_completed: "Tamamlandı",
      appointment_cancelled: "İptal",
      appointment_status: "Randevu",
      appointment_overdue: "Geciken takip",
      measurement_trend_derived: "Trend analizi",
      measurement_trend_insufficient_comparable: "Karşılaştırılabilir ölçüm",
      risk_current_snapshot: "Risk anlık görüntüsü",
    },
  },
  management: {
    title: "Klinik yönetimi",
    description:
      "Organizasyonunuza hasta kaydedin, onam durumunu kaydedin ve doktor atamalarını yönetin.",
    forbiddenTitle: "Erişim engellendi",
    forbiddenDescription:
      "Bu yönetim ekranı yalnızca klinik yöneticisi (clinic_admin) hesapları içindir.",
    organizationSection: "Organizasyon üyeliği",
    doctorsSection: "Aktif doktorlar",
    patientsSection: "Hasta seçimi",
    assignmentsSection: "Mevcut atamalar",
    assignDoctor: "Doktor ata",
    removeAssignment: "Atamayı kaldır",
    removingAssignment: "Atama kaldırılıyor…",
    selectPatient: "Hasta seçin",
    selectDoctor: "Doktor seçin",
    noPatientSelected: "Atamaları görmek için listeden bir hasta seçin.",
    organizationName: "Organizasyon",
    membershipStatus: "Üyelik durumu",
    membershipId: "Üyelik kimliği",
    organizationId: "Organizasyon kimliği",
    membershipRole: "Üyelik rolü",
    joinedAt: "Katılım tarihi",
    doctorName: "Doktor",
    doctorEmail: "E-posta",
    assignedDoctor: "Atanan doktor",
    technicalDetails: "Teknik tanımlayıcılar",
    userId: "Kullanıcı kimliği",
    patientLabel: "Hasta",
    isPrimary: "Birincil atama",
    status: "Durum",
    assignedAt: "Atama tarihi",
    endedAt: "Bitiş tarihi",
    assignmentId: "Atama kimliği",
    assigneeUserId: "Atanan doktor kimliği",
    emptyDoctors: "Organizasyonda listelenecek aktif doktor yok.",
    emptyAssignments: "Bu hasta için kayıtlı atama yok.",
    loadError: "Yönetim verileri yüklenemedi.",
    createSuccess: "Atama oluşturuldu.",
    deactivateSuccess: "Atama devre dışı bırakıldı.",
    membershipRoles: {
      doctor: "Doktor",
      clinic_admin: "Klinik yöneticisi",
    },
    membershipStatuses: {
      active: "Aktif",
      inactive: "Pasif",
    },
    assignmentStatuses: {
      active: "Aktif",
      inactive: "Pasif",
    },
    errors: {
      duplicateAssignment:
        "Bu doktor ve hasta için zaten aktif bir atama var.",
      duplicatePrimary: "Bu hasta için zaten aktif bir birincil atama var.",
      duplicateConsent: "Bu hasta için zaten aktif bir onam kaydı var.",
      patientNotFound: "Hasta bulunamadı veya organizasyonunuz dışında.",
      assignmentNotFound: "Atama bulunamadı.",
      doctorNotFound: "Doktor bulunamadı veya organizasyonunuz dışında.",
      generic: "İşlem tamamlanamadı. Lütfen tekrar deneyin.",
    },
    onboarding: {
      createSection: "Hasta kaydı",
      createHint:
        "Hastalar otomatik olarak organizasyonunuza bağlanır. Yalnızca sentetik demo verisi kullanın.",
      consentSection: "Klinik veri onamı",
      consentHint:
        "Klinik veri işleme onamının alınıp alınmadığını kaydedin (KVKK / pilot karar destek).",
      firstName: "Ad",
      lastName: "Soyad",
      dateOfBirth: "Doğum tarihi",
      gender: "Cinsiyet",
      genderOptions: {
        female: "Kadın",
        male: "Erkek",
        other: "Diğer",
      },
      demoNotesDefault:
        "Sentetik pilot kayıt — gerçek hasta verisi kullanmayın.",
      consentGrantFailedWarning:
        "Hasta oluşturuldu ancak klinik veri işleme onamı kaydedilemedi.",
      phoneOptional: "Telefon (isteğe bağlı)",
      notesOptional: "Notlar (isteğe bağlı)",
      grantConsentOnCreate: "Kayıttan sonra klinik veri işleme onamını kaydet",
      submitCreate: "Hastayı oluştur",
      submitting: "Hasta oluşturuluyor…",
      createSuccess: "Hasta başarıyla oluşturuldu.",
      selectPatientForConsent: "Onamı görüntülemek veya güncellemek için hasta seçin.",
      consentStatusGranted: "Aktif onam: verildi",
      consentStatusNotGranted: "Kayıtlı aktif onam yok.",
      grantConsent: "Onam kaydet",
      revokeConsent: "Onamı geri al",
      noConsentHistory: "Henüz onam kaydı yok.",
      consentTypes: {
        clinical_data_processing: "Klinik veri işleme",
      },
      consentStatuses: {
        granted: "Verildi",
        revoked: "Geri alındı",
      },
    },
  },
};
