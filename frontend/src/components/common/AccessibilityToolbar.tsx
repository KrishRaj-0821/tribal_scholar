import React from 'react';
import { useAccessibility } from '../../context/AccessibilityContext';
import { useLanguage } from '../../context/LanguageContext';
import { Eye, Globe } from 'lucide-react';

export const AccessibilityToolbar: React.FC = () => {
  const { textScale, setTextScale, highContrast, toggleHighContrast } = useAccessibility();
  const { language, setLanguage, t } = useLanguage();

  return (
    <div 
      className="bg-[#150202] text-[#FFFFFF] text-xs py-1 px-3 border-b border-[#263238]"
      role="region"
      aria-label="Accessibility & Language Controls"
    >
      <div className="gov-container flex flex-wrap items-center justify-between gap-2">
        {/* Left: Skip to Main Content & Sovereign Statement */}
        <div className="flex items-center gap-3">
          <a 
            href="#main-content" 
            className="sr-only focus:not-sr-only focus:inline-block bg-[#FFC107] text-[#150202] px-2 py-0.5 font-bold rounded"
          >
            {t('a11y.skipToContent')}
          </a>
          <span className="hidden sm:inline text-[#CFD8DC] font-medium">
            {language === 'en' ? 'भारत सरकार | Government of India' : 'Government of India | भारत सरकार'}
          </span>
          <span className="hidden md:inline-block bg-[#FFC107] text-[#150202] text-[10px] font-bold px-1.5 py-0.5 rounded">
            SIH 2026 PROTOTYPE
          </span>
        </div>

        {/* Right: Accessibility Controls & Language Toggle */}
        <div className="flex items-center gap-3 ml-auto">
          {/* Font Sizer */}
          <div className="flex items-center gap-1 bg-[#263238] rounded px-1.5 py-0.5" aria-label="Text Size Controls">
            <button
              onClick={() => setTextScale('normal')}
              className={`px-1.5 py-0.5 rounded text-xs font-bold transition-colors ${
                textScale === 'normal' ? 'bg-[#1D0A69] text-white' : 'text-[#CFD8DC] hover:text-white'
              }`}
              title="Standard Font Size"
              aria-pressed={textScale === 'normal'}
            >
              A-
            </button>
            <button
              onClick={() => setTextScale('large')}
              className={`px-1.5 py-0.5 rounded text-xs font-bold transition-colors ${
                textScale === 'large' ? 'bg-[#1D0A69] text-white' : 'text-[#CFD8DC] hover:text-white'
              }`}
              title="Large Font Size"
              aria-pressed={textScale === 'large'}
            >
              A
            </button>
            <button
              onClick={() => setTextScale('xlarge')}
              className={`px-1.5 py-0.5 rounded text-xs font-bold transition-colors ${
                textScale === 'xlarge' ? 'bg-[#1D0A69] text-white' : 'text-[#CFD8DC] hover:text-white'
              }`}
              title="Extra Large Font Size"
              aria-pressed={textScale === 'xlarge'}
            >
              A+
            </button>
          </div>

          {/* High Contrast Toggle */}
          <button
            onClick={toggleHighContrast}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
              highContrast 
                ? 'bg-[#FFFF00] text-[#000000] border-[#FFFF00] font-bold' 
                : 'border-[#546E7A] text-[#CFD8DC] hover:text-white'
            }`}
            aria-pressed={highContrast}
            title="Toggle High Contrast Mode for Screen Accessibility"
          >
            <Eye className="w-3 h-3" />
            <span className="hidden sm:inline">{t('a11y.contrast')}</span>
          </button>

          {/* Bilingual Toggle: English / हिन्दी */}
          <div className="flex items-center gap-1 bg-[#263238] rounded px-1.5 py-0.5">
            <Globe className="w-3 h-3 text-[#CFD8DC]" />
            <button
              onClick={() => setLanguage('en')}
              className={`px-1 py-0.5 rounded text-xs font-semibold ${
                language === 'en' ? 'bg-[#1D0A69] text-white' : 'text-[#CFD8DC] hover:text-white'
              }`}
              aria-pressed={language === 'en'}
            >
              English
            </button>
            <span className="text-[#546E7A]">|</span>
            <button
              onClick={() => setLanguage('hi')}
              className={`px-1 py-0.5 rounded text-xs font-semibold ${
                language === 'hi' ? 'bg-[#1D0A69] text-white' : 'text-[#CFD8DC] hover:text-white'
              }`}
              aria-pressed={language === 'hi'}
            >
              हिन्दी
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
