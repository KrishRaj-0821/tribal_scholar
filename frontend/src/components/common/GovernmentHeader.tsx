import React from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { TribalPattern } from './TribalPattern';
import { ShieldCheck, PhoneCall } from 'lucide-react';

export const GovernmentHeader: React.FC = () => {
  const { language } = useLanguage();

  return (
    <header className="w-full bg-[#FFFFFF] border-b border-[#CFD8DC] select-none" role="banner">
      {/* Top Tricolor Micro Stripe */}
      <div className="h-1 w-full flex" aria-hidden="true">
        <div className="w-1/3 bg-[#FF9933]"></div>
        <div className="w-1/3 bg-[#FFFFFF]"></div>
        <div className="w-1/3 bg-[#138808]"></div>
      </div>

      {/* Main Sovereign Ministry Header */}
      <div className="gov-container py-3">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          {/* Left: Official Ministry of Tribal Affairs Identity Lockup */}
          <div className="flex items-center gap-3">
            <img 
              src="/mota-logo.png" 
              alt="Ministry of Tribal Affairs | जनजातीय कार्य मंत्रालय | Government of India" 
              className="h-12 sm:h-16 w-auto object-contain flex-shrink-0"
            />
            <div className="border-l-2 border-[#1D0A69] pl-3 py-0.5">
              <div className="text-[11px] font-bold uppercase tracking-wider text-[#C85A17]">
                {language === 'hi' ? 'भारत सरकार • राष्ट्रीय छात्रवृत्ति' : 'Government of India • Sovereign Portal'}
              </div>
              <div className="text-base sm:text-xl font-extrabold text-[#1D0A69] tracking-tight font-serif leading-tight">
                <span>Tribal Scholar Portal</span>
              </div>
              <div className="text-[11px] sm:text-xs font-medium text-[#546E7A] line-clamp-1">
                {language === 'hi' ? 'जनजातीय राष्ट्रीय छात्रवृत्ति एवं अध्येतावृत्ति प्रबंधन प्रणाली' : 'National Scholarship & Fellowship Management System'}
              </div>
            </div>
          </div>

          {/* Right: Statutory Direct DBT Badge & National Helpline */}
          <div className="hidden lg:flex items-center gap-4 text-xs">
            {/* DBT Seeding Badge */}
            <div className="flex items-center gap-2 bg-[#E8F5E9] border border-[#A5D6A7] px-3 py-1.5 rounded">
              <ShieldCheck className="w-4 h-4 text-[#198754]" />
              <div>
                <div className="font-bold text-[#198754] leading-tight">100% Direct DBT</div>
                <div className="text-[10px] text-[#263238]">Aadhaar-NPCI Seeded Disbursal</div>
              </div>
            </div>

            {/* National Toll-Free Helpline */}
            <div className="flex items-center gap-2 bg-[#F4F6F8] border border-[#CFD8DC] px-3 py-1.5 rounded">
              <PhoneCall className="w-4 h-4 text-[#0F4C81]" />
              <div>
                <div className="font-bold text-[#0F4C81] leading-tight">1800-11-7788</div>
                <div className="text-[10px] text-[#546E7A]">Toll-Free (09:30 - 18:00 IST)</div>
              </div>
            </div>

            {/* Prototype Indicator */}
            <div className="border border-[#FFE082] bg-[#FFF9C4] px-2.5 py-1 rounded text-center">
              <div className="text-[10px] font-extrabold text-[#7A5E00]">SIH 2026 PROTOTYPE</div>
              <div className="text-[9px] text-[#263238]">Ministry of Tribal Affairs</div>
            </div>
          </div>
        </div>
      </div>

      {/* Sovereign Cultural Divider Band (Woven Loom Geometric Motif) */}
      <TribalPattern variant="woven" height={10} color="#1D0A69" opacity={0.9} />
    </header>
  );
};
