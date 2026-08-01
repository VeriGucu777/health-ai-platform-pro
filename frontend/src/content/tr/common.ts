import type { CommonContent } from "@/lib/i18n/types";

export const commonContent: CommonContent = {
  brandName: "Health AI Platform Pro",
  brandTagline: "Modern sağlık ekipleri için klinik karar destek platformu",
  nav: {
    home: "Ana sayfa",
    login: "Giriş yap",
    register: "Hesap oluştur",
    skipToContent: "Ana içeriğe geç",
    openMenu: "Menüyü aç",
    closeMenu: "Menüyü kapat",
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
    badge: "Sağlık SaaS altyapısı",
    heroTitle: "Sağlık ekipleri için daha akıllı klinik iş akışları",
    heroDescription:
      "Sağlık profesyonelleri için tasarlanmış güvenli bir çalışma alanında hasta kayıtlarını, sağlık içgörülerini ve risk değerlendirmelerini yönetin.",
    primaryCta: "Başlayın",
    secondaryCta: "Giriş yap",
    featuresTitle: "Sorumlu sağlık yapay zekası için tasarlandı",
    features: [
      {
        title: "Yapılandırılmış hasta verileri",
        description:
          "Randevuları, tıbbi kayıtları ve sağlık ölçümlerini sahip odaklı erişim kontrolleriyle düzenleyin.",
      },
      {
        title: "Karar destek analitiği",
        description:
          "Tanı sunmadan klinik değerlendirmeyi destekleyen trendleri ve içgörüleri inceleyin.",
      },
      {
        title: "Üretime hazır temel",
        description:
          "JWT kimlik doğrulama, gözlemlenebilirlik ve PostgreSQL kalıcılığı ile FastAPI backend'e bağlanın.",
      },
    ],
    trustTitle: "Klinik güvenlik öncelikli tasarım",
    trustPoints: [
      "Demo içeriğinde hasta tanımlayıcı bilgisi yok",
      "Karar destek çıktılarında açık tıbbi feragatnameler",
      "Ortam yapılandırması üzerinden güvenli API entegrasyonu",
    ],
  },
  auth: {
    loginTitle: "Giriş yap",
    loginDescription:
      "Çalışma alanınıza erişin. Kimlik doğrulama sonraki aşamada FastAPI backend'e bağlanacaktır.",
    registerTitle: "Hesap oluştur",
    registerDescription:
      "Profesyonel bir hesap oluşturun. Hesap oluşturma sonraki aşamada FastAPI backend'e bağlanacaktır.",
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
      "Önizleme: Bu form yalnızca sunum amaçlıdır ve kimlik bilgilerini göndermez.",
  },
};
