import React, { createContext, useContext, useState, ReactNode } from 'react';

export type Language = 'en' | 'hi';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const DICTIONARY: Record<string, { en: string; hi: string }> = {
  // Sovereign Headers & Branding
  'gov.name': { en: 'Government of India', hi: 'भारत सरकार' },
  'mota.name': { en: 'Ministry of Tribal Affairs', hi: 'जनजातीय कार्य मंत्रालय' },
  'portal.title': { en: 'Tribal Scholar Portal', hi: 'जनजातीय छात्रवृत्ति पोर्टल' },
  'portal.subtitle': { en: 'Central Sector & Centrally Sponsored ST Scholarship Gateway', hi: 'केंद्रीय क्षेत्र एवं केंद्र प्रायोजित एसटी छात्रवृत्ति पोर्टल' },
  'prototype.badge': { en: 'SIH 2026 PROTOTYPE', hi: 'एसआईएच 2026 प्रोटोटाइप' },
  'dbt.verified': { en: '100% Aadhaar-NPCI Direct DBT', hi: '100% आधार-एनपीसीआई प्रत्यक्ष डीबीटी' },
  'helpline.tollfree': { en: 'National ST Helpline: 1800-11-7788', hi: 'राष्ट्रीय एसटी हेल्पलाइन: 1800-11-7788' },

  // Navigation
  'nav.home': { en: 'Home', hi: 'मुख्य पृष्ठ' },
  'nav.schemes': { en: 'Schemes', hi: 'योजनाएं' },
  'nav.apply': { en: 'Apply Now', hi: 'आवेदन करें' },
  'nav.track': { en: 'Track Status', hi: 'स्थिति जांचें' },
  'nav.login': { en: 'Login / Register', hi: 'लॉगिन / पंजीकरण' },
  'nav.dashboard': { en: 'Applicant Dashboard', hi: 'आवेदक डैशबोर्ड' },
  'nav.officer': { en: 'Officer Workbench', hi: 'जांच कार्यक्षेत्र' },
  'nav.admin': { en: 'Admin Portal', hi: 'प्रशासनिक पोर्टल' },
  'nav.grievance': { en: 'Grievance / CPGRAMS', hi: 'शिकायत निवारण' },

  // Accessibility
  'a11y.skipToContent': { en: 'Skip to Main Content', hi: 'मुख्य सामग्री पर जाएं' },
  'a11y.screenReader': { en: 'Screen Reader Access', hi: 'स्क्रीन रीडर पहुंच' },
  'a11y.decreaseFont': { en: 'A-', hi: 'अ-' },
  'a11y.normalFont': { en: 'A', hi: 'अ' },
  'a11y.increaseFont': { en: 'A+', hi: 'अ+' },
  'a11y.contrast': { en: 'High Contrast', hi: 'उच्च कंट्रास्ट' },

  // Common Actions
  'action.viewDetails': { en: 'View Guidelines (PDF)', hi: 'दिशानिर्देश देखें (PDF)' },
  'action.applyScheme': { en: 'Apply for Scheme', hi: 'योजना हेतु आवेदन करें' },
  'action.saveContinue': { en: 'Save & Continue', hi: 'सुरक्षित करें और आगे बढ़ें' },
  'action.back': { en: 'Back', hi: 'पिछला' },
  'action.submit': { en: 'Submit Application', hi: 'आवेदन जमा करें' },
  'action.resolveDeficiency': { en: 'Resolve Deficiency', hi: 'कमी का समाधान करें' },
  'action.uploadDoc': { en: 'Upload Document', hi: 'दस्तावेज़ अपलोड करें' },
  'action.replaceDoc': { en: 'Replace Document', hi: 'दस्तावेज़ बदलें' },
  'action.download': { en: 'Download Receipt', hi: 'रसीद डाउनलोड करें' },

  // Status Labels
  'status.submitted': { en: 'Submitted', hi: 'जमा किया गया' },
  'status.underVerification': { en: 'Under Scrutiny', hi: 'जांच जारी है' },
  'status.verified': { en: 'Verified & Validated', hi: 'सत्यापित एवं वैध' },
  'status.deficiency': { en: 'Action Required', hi: 'कमी सुधार अपेक्षित' },
  'status.disbursed': { en: 'DBT Disbursed', hi: 'डीबीटी अंतरित' },
  'status.rejected': { en: 'Rejected with Grounds', hi: 'अस्वीकृत' },
  
  // Footer
  'footer.address': { en: 'Shastri Bhawan, Dr. Rajendra Prasad Road, New Delhi - 110001', hi: 'शास्त्री भवन, डॉ. राजेंद्र प्रसाद रोड, नई दिल्ली - 110001' },
  'footer.designedBy': { en: 'Designed, Developed and Hosted by National Informatics Centre (NIC). Content Owned by Ministry of Tribal Affairs.', hi: 'राष्ट्रीय सूचना विज्ञान केंद्र (एनआईसी) द्वारा डिजाइन, विकसित और होस्ट किया गया। सामग्री जनजातीय कार्य मंत्रालय के स्वामित्व में है।' },
  'footer.disclaimer': { en: 'This portal is a Smart India Hackathon (SIH 2026) prototype demonstration and does not constitute an officially launched legal declaration of the Government of India.', hi: 'यह पोर्टल स्मार्ट इंडिया हैकाथॉन (SIH 2026) का एक प्रोटोटाइप प्रदर्शन है और भारत सरकार की कानूनी घोषणा का दावा नहीं करता।' }
};

const LanguageContext = createContext<LanguageContextType>({
  language: 'en',
  setLanguage: () => {},
  t: (key) => key
});

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguage] = useState<Language>('en');

  const t = (key: string): string => {
    const entry = DICTIONARY[key];
    if (!entry) return key;
    return entry[language] || entry.en;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
