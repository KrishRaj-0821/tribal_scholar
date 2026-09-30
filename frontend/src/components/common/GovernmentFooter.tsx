import React from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { TribalPattern } from './TribalPattern';
import { ExternalLink, ShieldAlert, ArrowUpRight } from 'lucide-react';

export const GovernmentFooter: React.FC = () => {
  const { language } = useLanguage();

  return (
    <footer className="w-full bg-[#150202] text-[#FFFFFF] mt-16 border-t-2 border-[#1D0A69]" role="contentinfo">
      {/* 1. Continuous Indian Tribal-Inspired Signature Line Pattern */}
      <TribalPattern variant="community" height={10} color="#FF9933" opacity={0.8} />

      <div className="gov-container py-10">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 text-xs border-b border-[#263238] pb-8">
          {/* Col 1: Platform Sovereign Statement (4 cols) */}
          <div className="md:col-span-4 space-y-3">
            <div className="flex items-center gap-3">
              <div className="bg-[#FFFFFF] p-1.5 rounded">
                <img 
                  src="/mota-logo.png" 
                  alt="Ministry of Tribal Affairs Logo" 
                  className="h-10 w-auto object-contain"
                />
              </div>
              <div>
                <div className="font-extrabold text-[#FFFFFF] text-base font-serif tracking-tight">
                  Tribal Scholar Portal
                </div>
                <div className="text-[10px] text-[#FFC107] font-mono uppercase tracking-wider">
                  Ministry of Tribal Affairs • GoI
                </div>
              </div>
            </div>

            <p className="text-[#CFD8DC] leading-relaxed text-xs">
              {language === 'hi' 
                ? 'जनजातीय कार्य मंत्रालय, भारत सरकार की आधिकारिक छात्रवृत्ति एवं अध्येतावृत्ति प्रबंधन प्रणाली। 100% पारदर्शी, सुरक्षित एवं प्रत्यक्ष बैंक अंतरण (DBT) समर्थित।'
                : 'A single sovereign digital platform for scholarship and fellowship access. Empowering Scheduled Tribe scholars across India through certified affirmative action and 100% direct DBT disbursal.'}
            </p>

            <div className="pt-1 text-[#CFD8DC] space-y-1 text-[11px]">
              <div><strong className="text-white">National ST Helpline:</strong> 1800-11-7788 (Toll-Free)</div>
              <div><strong className="text-white">Support Email:</strong> support-tribalscholar@nic.in</div>
              <div><strong className="text-white">Hours:</strong> 09:30 - 17:30 IST (Mon - Fri)</div>
            </div>
          </div>

          {/* Col 2: Useful Public Links (2 cols) */}
          <div className="md:col-span-2 space-y-2">
            <div className="font-bold text-[#FFC107] text-xs font-mono uppercase tracking-wider">
              {language === 'hi' ? 'महत्वपूर्ण सेवाएं' : 'Useful Services'}
            </div>
            <ul className="space-y-2 text-[#CFD8DC]">
              <li><a href="#main-content" className="hover:text-white flex items-center gap-1">All 5 ST Schemes <ArrowUpRight className="w-2.5 h-2.5 opacity-60" /></a></li>
              <li><a href="#main-content" className="hover:text-white flex items-center gap-1">OTR Registration <ArrowUpRight className="w-2.5 h-2.5 opacity-60" /></a></li>
              <li><a href="#main-content" className="hover:text-white flex items-center gap-1">Document Checklist <ArrowUpRight className="w-2.5 h-2.5 opacity-60" /></a></li>
              <li><a href="#main-content" className="hover:text-white flex items-center gap-1">Notified Institutes List <ArrowUpRight className="w-2.5 h-2.5 opacity-60" /></a></li>
              <li><a href="#main-content" className="hover:text-white flex items-center gap-1">CPGRAMS Grievance <ArrowUpRight className="w-2.5 h-2.5 opacity-60" /></a></li>
            </ul>
          </div>

          {/* Col 3: Government Portals (3 cols) */}
          <div className="md:col-span-3 space-y-2">
            <div className="font-bold text-[#FFC107] text-xs font-mono uppercase tracking-wider">
              {language === 'hi' ? 'संबद्ध सरकारी पोर्टल' : 'Government Portals'}
            </div>
            <ul className="space-y-2 text-[#CFD8DC]">
              <li>
                <a href="https://tribal.nic.in" target="_blank" rel="noopener noreferrer" className="hover:text-white flex items-center gap-1">
                  MoTA Official (tribal.nic.in) <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                </a>
              </li>
              <li>
                <a href="https://scholarships.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-white flex items-center gap-1">
                  National Scholarship Portal (NSP) <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                </a>
              </li>
              <li>
                <a href="https://dbtbharat.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-white flex items-center gap-1">
                  Direct Benefit Transfer (DBT Bharat) <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                </a>
              </li>
              <li>
                <a href="https://pfms.nic.in" target="_blank" rel="noopener noreferrer" className="hover:text-white flex items-center gap-1">
                  PFMS Financial System <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                </a>
              </li>
              <li>
                <a href="https://www.india.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-white flex items-center gap-1">
                  National Portal of India (india.gov.in) <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                </a>
              </li>
            </ul>
          </div>

          {/* Col 4: Compliance & Disclaimer (3 cols) */}
          <div className="md:col-span-3 space-y-3">
            <div className="font-bold text-[#FFC107] text-xs font-mono uppercase tracking-wider flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5 text-[#FFC107]" />
              <span>Statutory Compliance</span>
            </div>
            <p className="text-[#90A4AE] text-[11px] leading-relaxed">
              Designed in compliance with Guidelines for Indian Government Websites (GIGW 3.0), WCAG 2.1 AA, and Aadhaar Act 2016 data privacy standards.
            </p>
            <div className="bg-[#263238] p-2.5 rounded border border-[#546E7A] text-[10px] text-[#CFD8DC]">
              <span className="font-bold text-[#FFC107] block mb-0.5">SIH 2026 PROTOTYPE EVALUATION</span>
              Ministry of Tribal Affairs Problem Statement 26239.
            </div>
          </div>
        </div>

        {/* 2. Secondary Cultural Divider Line */}
        <div className="my-6">
          <TribalPattern variant="woven" height={6} color="#CFD8DC" opacity={0.25} />
        </div>

        {/* 3. Bottom Credits & National Sovereignty Strip */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-[#90A4AE]">
          <div className="flex items-center gap-2">
            <span>© 2026 Ministry of Tribal Affairs, Government of India.</span>
            <span className="hidden sm:inline">•</span>
            <span className="text-white font-medium">जनजातीय कार्य मंत्रालय, भारत सरकार</span>
          </div>
          <div>
            Built with Django 5.1 • React • PostgreSQL • PWA GIGW 3.0
          </div>
        </div>
      </div>
    </footer>
  );
};
