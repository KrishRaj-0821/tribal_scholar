import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { OFFICIAL_MOTA_SCHEMES, SchemeInfo } from '../../theme/tokens';
import { TribalPattern, TribalPatternVariant } from '../common/TribalPattern';
import { 
  Search, ShieldCheck, ArrowRight, 
  Award, Calendar, HelpCircle, PhoneCall
} from 'lucide-react';

interface HomeViewProps {
  onSelectScheme: (scheme: SchemeInfo) => void;
  onNavigateTab: (tab: string) => void;
}

export const HomeView: React.FC<HomeViewProps> = ({
  onSelectScheme,
  onNavigateTab
}) => {
  const { language } = useLanguage();
  const [trackAppNo, setTrackAppNo] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<string>('ALL');

  // Map scheme codes to authentic regional pattern motifs
  const getSchemePattern = (code: string): TribalPatternVariant => {
    switch (code) {
      case 'PMS-01': return 'forest';
      case 'PMS-02': return 'river';
      case 'TOP-05': return 'woven';
      case 'NFST-03': return 'earth';
      case 'NOS-04': return 'mountain';
      default: return 'community';
    }
  };

  const filteredSchemes = OFFICIAL_MOTA_SCHEMES.filter(s => {
    const matchesSearch = 
      s.titleEn.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.titleHi.includes(searchQuery) ||
      s.code.toLowerCase().includes(searchQuery.toLowerCase());

    if (selectedLevel === 'ALL') return matchesSearch;
    if (selectedLevel === 'PRE') return matchesSearch && s.code === 'PMS-01';
    if (selectedLevel === 'POST') return matchesSearch && s.code === 'PMS-02';
    if (selectedLevel === 'TOP') return matchesSearch && s.code === 'TOP-05';
    if (selectedLevel === 'RESEARCH') return matchesSearch && (s.code === 'NFST-03' || s.code === 'NOS-04');
    return matchesSearch;
  });

  return (
    <div className="space-y-0 text-[#150202]">
      {/* ─────────────────────────────────────────────────────────────
          01. EDITORIAL SOVEREIGN HERO (Asymmetric & Authoritative)
          ───────────────────────────────────────────────────────────── */}
      <section className="relative bg-[#FFFFFF] border-b border-[#CFD8DC] overflow-hidden pt-8 pb-12 sm:pt-14 sm:pb-16">
        {/* Authentic Background Geometry (Strict 6% opacity) */}
        <TribalPattern variant="woven" asBackground opacity={0.06} color="#1D0A69" />

        <div className="gov-container relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
            {/* Left 7 Columns: Editorial Narrative & Mandate */}
            <div className="lg:col-span-7 space-y-6">
              {/* Sovereign Mandate Chip */}
              <div className="inline-flex items-center gap-2 bg-[#EBEAEA] border-l-4 border-l-[#1D0A69] px-3 py-1.5 text-xs font-bold text-[#1D0A69]">
                <Award className="w-3.5 h-3.5 text-[#1D0A69]" />
                <span className="tracking-wide uppercase text-[11px]">
                  {language === 'hi' 
                    ? 'शैक्षणिक सत्र 2026-27 | भारत सरकार केंद्रीय योजनाएं' 
                    : 'Academic Cycle 2026-27 | Ministry of Tribal Affairs'}
                </span>
              </div>

              {/* Large Editorial Headline */}
              <div className="space-y-3">
                <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1D0A69] font-serif leading-[1.15] tracking-tight">
                  {language === 'hi' ? (
                    <>
                      अनुसूचित जनजाति के छात्रों हेतु <br />
                      <span className="text-[#C85A17]">राष्ट्रीय छात्रवृत्ति एवं अध्येतावृत्ति</span>
                    </>
                  ) : (
                    <>
                      Scholarships & Fellowships <br />
                      <span className="text-[#C85A17]">for Scheduled Tribe Students</span>
                    </>
                  )}
                </h1>
                
                <p className="text-base sm:text-lg text-[#263238] font-normal leading-relaxed max-w-2xl">
                  {language === 'hi'
                    ? 'एकल पारदर्शी डिजिटल यात्रा — योजना खोज, ऑनलाइन आवेदन, बहुभाषी ओसीआर दस्तावेज़ सत्यापन एवं शत-प्रतिशत आधार-एनपीसीआई प्रत्यक्ष लाभ अंतरण (DBT)।'
                    : 'A single sovereign digital journey for discovery, application, cryptographic evidence verification, and 100% Aadhaar-NPCI direct benefit disbursal.'}
                </p>
              </div>

              {/* Primary & Secondary CTAs */}
              <div className="flex flex-wrap items-center gap-4 pt-2">
                <button
                  id="cta-find-scholarship"
                  onClick={() => onNavigateTab('schemes')}
                  className="gov-btn gov-btn-primary px-6 py-3 text-sm font-bold shadow-sm flex items-center gap-2"
                >
                  <Search className="w-4 h-4 text-[#FFC107]" />
                  <span>{language === 'hi' ? 'मेरी छात्रवृत्ति खोजें' : 'Find My Scholarship'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <button
                  id="cta-track-application"
                  onClick={() => onNavigateTab('applicant_status')}
                  className="gov-btn gov-btn-secondary px-6 py-3 text-sm font-bold flex items-center gap-2"
                >
                  <span>{language === 'hi' ? 'आवेदन स्थिति ट्रैक करें' : 'Track Application'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <button
                  onClick={() => onNavigateTab('wizard')}
                  className="bg-[#1D0A69] border border-[#FFC107] text-[#FFC107] hover:bg-[#FFC107] hover:text-[#1D0A69] px-4 py-3 text-xs font-bold rounded flex items-center gap-1.5 transition-colors"
                >
                  <span>{language === 'hi' ? 'सिंथेटिक डेमो आवेदन शुरू करें' : 'Start Demo Application (Mandla ST)'}</span>
                </button>
              </div>

              {/* Direct Benefit Transfer Assurance */}
              <div className="flex items-center gap-2 text-xs text-[#546E7A] pt-2">
                <ShieldCheck className="w-4 h-4 text-[#198754]" />
                <span className="font-semibold text-[#150202]">
                  {language === 'hi' 
                    ? 'शून्य बिचौलिया • प्रत्यक्ष बैंक अंतरण (DBT) • आधार ई-केवाईसी अनिवार्य' 
                    : 'Zero Intermediaries • 100% Direct DBT to Student Accounts • Aadhaar Mandated'}
                </span>
              </div>
            </div>

            {/* Right 5 Columns: Official Application Quick-Desk Ledger */}
            <div className="lg:col-span-5">
              <div className="bg-[#FFFFFF] border-2 border-[#1D0A69] p-6 shadow-sm relative">
                {/* Top Corner Motif Accent */}
                <div className="absolute top-0 right-0 w-16 h-1 bg-[#C85A17]" />
                
                <div className="border-b border-[#CFD8DC] pb-3 mb-4">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono font-bold tracking-wider uppercase text-[#0F4C81]">
                      OFFICIAL PUBLIC DESK
                    </span>
                    <span className="gov-badge gov-badge-success text-[10px]">
                      LIVE SYSTEM
                    </span>
                  </div>
                  <h2 className="text-lg font-bold text-[#1D0A69] font-serif mt-1">
                    {language === 'hi' ? 'आवेदन स्थिति त्वरित जांच' : 'Track Application Status'}
                  </h2>
                  <p className="text-xs text-[#546E7A]">
                    {language === 'hi' ? 'आवेदन संख्या अथवा ओटीआर दर्ज करें' : 'Enter Application Ref No or OTR ID'}
                  </p>
                </div>

                <form 
                  onSubmit={(e) => {
                    e.preventDefault();
                    onNavigateTab('applicant_status');
                  }} 
                  className="space-y-4"
                >
                  <div>
                    <label className="gov-label text-xs">
                      {language === 'hi' ? 'आवेदन संदर्भ संख्या / OTR संख्या' : 'Application Ref No / OTR ID'}
                      <span className="gov-req">*</span>
                    </label>
                    <input
                      type="text"
                      className="gov-input text-xs"
                      placeholder="e.g. MOTA/2026/TC/09841"
                      value={trackAppNo}
                      onChange={(e) => setTrackAppNo(e.target.value)}
                      required
                    />
                  </div>

                  <div>
                    <label className="gov-label text-xs">
                      {language === 'hi' ? 'जन्म तिथि (आधार अनुसार)' : 'Date of Birth (as per Aadhaar)'}
                      <span className="gov-req">*</span>
                    </label>
                    <input
                      type="date"
                      className="gov-input text-xs"
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    className="gov-btn gov-btn-primary w-full text-xs font-bold py-2.5"
                  >
                    <span>{language === 'hi' ? 'स्थिति देखें (Check Status)' : 'View Live Dossier & Status'}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </form>

                <div className="mt-4 pt-3 border-t border-[#ECEFF1] flex items-center justify-between text-[11px] text-[#546E7A]">
                  <span className="flex items-center gap-1">
                    <PhoneCall className="w-3 h-3 text-[#0F4C81]" />
                    <span>Toll-Free: <strong>1800-11-7788</strong></span>
                  </span>
                  <span className="text-[#1D0A69] font-semibold">NIC-MoTA Gateway</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          02. PUBLIC SERVICE ACTION RIBBON (Full-Width, Non-Card)
          ───────────────────────────────────────────────────────────── */}
      <nav 
        className="bg-[#15074D] text-[#FFFFFF] border-y border-[#0F4C81] select-none"
        aria-label="Public Service Quick Navigation"
      >
        <div className="gov-container flex items-center justify-between overflow-x-auto py-2.5 text-xs font-bold tracking-wide">
          <button
            onClick={() => onNavigateTab('wizard')}
            className="flex items-center gap-2 py-1 px-3 hover:text-[#FFC107] whitespace-nowrap transition-colors"
          >
            <span className="text-[#FFC107] font-bold">01</span>
            <span>{language === 'hi' ? 'ऑनलाइन आवेदन' : 'APPLY ONLINE'}</span>
          </button>
          <span className="text-[#546E7A] hidden sm:inline">|</span>

          <button
            onClick={() => onNavigateTab('dashboard')}
            className="flex items-center gap-2 py-1 px-3 hover:text-[#FFC107] whitespace-nowrap transition-colors"
          >
            <span className="text-[#FFC107] font-bold">02</span>
            <span>{language === 'hi' ? 'आवेदक डॉसियर' : 'APPLICANT DOSSIER'}</span>
          </button>
          <span className="text-[#546E7A] hidden sm:inline">|</span>

          <button
            onClick={() => onNavigateTab('schemes')}
            className="flex items-center gap-2 py-1 px-3 hover:text-[#FFC107] whitespace-nowrap transition-colors"
          >
            <span className="text-[#FFC107] font-bold">03</span>
            <span>{language === 'hi' ? 'योजना नियम एवं पात्रता' : 'SCHEME GUIDELINES'}</span>
          </button>
          <span className="text-[#546E7A] hidden sm:inline">|</span>

          <button
            onClick={() => onNavigateTab('deficiency')}
            className="flex items-center gap-2 py-1 px-3 hover:text-[#FFC107] whitespace-nowrap transition-colors"
          >
            <span className="text-[#FFC107] font-bold">04</span>
            <span>{language === 'hi' ? 'दस्तावेज़ कमी निवारण' : 'RESOLVE DEFICIENCY'}</span>
          </button>
          <span className="text-[#546E7A] hidden sm:inline">|</span>

          <button
            onClick={() => onNavigateTab('grievance')}
            className="flex items-center gap-2 py-1 px-3 hover:text-[#FFC107] whitespace-nowrap transition-colors"
          >
            <span className="text-[#FFC107] font-bold">05</span>
            <span>{language === 'hi' ? 'सीपीग्राम्स शिकायत' : 'GRIEVANCE (CPGRAMS)'}</span>
          </button>

        </div>
      </nav>

      {/* ─────────────────────────────────────────────────────────────
          03. NATIONAL STATUTORY IMPACT (Typographic Numbers, Non-Card)
          ───────────────────────────────────────────────────────────── */}
      <section className="bg-[#EBEAEA] border-b border-[#CFD8DC] py-8 sm:py-10 relative overflow-hidden">
        <TribalPattern variant="earth" asBackground opacity={0.05} color="#150202" />

        <div className="gov-container relative z-10">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8 divide-y sm:divide-y-0 sm:divide-x divide-[#CFD8DC]">
            <div className="pt-4 sm:pt-0 sm:pl-4 first:pl-0">
              <div className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-[#1D0A69] font-serif">
                ₹2,815 Cr
              </div>
              <div className="text-xs font-bold text-[#150202] mt-1">
                {language === 'hi' ? 'वार्षिक बजटीय आवंटन' : 'Annual MoTA Budget'}
              </div>
              <p className="text-[11px] text-[#546E7A] mt-0.5">
                {language === 'hi' ? 'केंद्रीय क्षेत्र एवं राज्य अंशदान' : 'Direct statutory outlay (AY 2026-27)'}
              </p>
            </div>

            <div className="pt-4 sm:pt-0 sm:pl-4">
              <div className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-[#198754] font-serif">
                16.3 Lakh+
              </div>
              <div className="text-xs font-bold text-[#150202] mt-1">
                {language === 'hi' ? 'सक्रिय एसटी छात्र' : 'Active ST Scholars'}
              </div>
              <p className="text-[11px] text-[#546E7A] mt-0.5">
                {language === 'hi' ? 'कक्षा 9 से शोध अध्येताओं तक' : 'From Class IX to doctoral fellows'}
              </p>
            </div>

            <div className="pt-4 sm:pt-0 sm:pl-4">
              <div className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-[#0F4C81] font-serif">
                265
              </div>
              <div className="text-xs font-bold text-[#150202] mt-1">
                {language === 'hi' ? 'अधिसूचित शीर्ष संस्थान' : 'Notified Premier Institutes'}
              </div>
              <p className="text-[11px] text-[#546E7A] mt-0.5">
                {language === 'hi' ? 'आईआईटी, आईआईएम, एम्स एवं एनआईटी' : 'Empanelled under Top Class Scheme'}
              </p>
            </div>

            <div className="pt-4 sm:pt-0 sm:pl-4">
              <div className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-[#C85A17] font-serif">
                100%
              </div>
              <div className="text-xs font-bold text-[#150202] mt-1">
                {language === 'hi' ? 'प्रत्यक्ष डीबीटी बैंक अंतरण' : 'Direct DBT to Bank Accounts'}
              </div>
              <p className="text-[11px] text-[#546E7A] mt-0.5">
                {language === 'hi' ? 'आधार-एनपीसीआई सीडिंग अनिवार्य' : 'Zero manual cheque / cash handling'}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          04. CURATED SCHEMES DIRECTORY (Distinct Cultural Motifs)
          ───────────────────────────────────────────────────────────── */}
      <section className="bg-[#FFFFFF] border-b border-[#CFD8DC] py-10 sm:py-14">
        <div className="gov-container space-y-8">
          {/* Section Header with 30-Second Filter Chips */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#CFD8DC] pb-4">
            <div>
              <div className="text-xs font-bold text-[#C85A17] tracking-wider uppercase">
                {language === 'hi' ? 'केंद्रीय एवं केंद्र प्रायोजित योजनाएं' : 'Statutory Schemes Portfolio'}
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-[#1D0A69] font-serif mt-0.5">
                {language === 'hi' ? 'जनजातीय कार्य मंत्रालय की प्रमुख योजनाएं' : 'Ministry of Tribal Affairs Schemes'}
              </h2>
              <p className="text-xs text-[#546E7A] mt-0.5">
                {language === 'hi' 
                  ? 'अपनी शैक्षिक योग्यता के अनुसार उपयुक्त छात्रवृत्ति योजना चुनें' 
                  : 'Select the verified affirmative action scheme suited to your current academic pursuit'}
              </p>
            </div>

            {/* Search Input & Quick Matcher Filter Chips */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#90A4AE]" />
                <input
                  type="text"
                  placeholder={language === 'hi' ? 'योजना खोजें...' : 'Search scheme or code...'}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="gov-input text-xs pl-8 py-1.5 w-44 sm:w-52"
                />
              </div>

              <div className="flex flex-wrap items-center gap-1.5 text-xs font-bold">
              <button
                onClick={() => setSelectedLevel('ALL')}
                className={`px-3 py-1.5 rounded transition-colors ${
                  selectedLevel === 'ALL'
                    ? 'bg-[#1D0A69] text-white'
                    : 'bg-[#F4F6F8] text-[#546E7A] hover:bg-[#EBEAEA]'
                }`}
              >
                All (5)
              </button>
              <button
                onClick={() => setSelectedLevel('PRE')}
                className={`px-3 py-1.5 rounded transition-colors ${
                  selectedLevel === 'PRE'
                    ? 'bg-[#1D0A69] text-white'
                    : 'bg-[#F4F6F8] text-[#546E7A] hover:bg-[#EBEAEA]'
                }`}
              >
                Class 9-10
              </button>
              <button
                onClick={() => setSelectedLevel('POST')}
                className={`px-3 py-1.5 rounded transition-colors ${
                  selectedLevel === 'POST'
                    ? 'bg-[#1D0A69] text-white'
                    : 'bg-[#F4F6F8] text-[#546E7A] hover:bg-[#EBEAEA]'
                }`}
              >
                Post-Matric
              </button>
              <button
                onClick={() => setSelectedLevel('TOP')}
                className={`px-3 py-1.5 rounded transition-colors ${
                  selectedLevel === 'TOP'
                    ? 'bg-[#1D0A69] text-white'
                    : 'bg-[#F4F6F8] text-[#546E7A] hover:bg-[#EBEAEA]'
                }`}
              >
                Top Class (IIT/IIM)
              </button>
              <button
                onClick={() => setSelectedLevel('RESEARCH')}
                className={`px-3 py-1.5 rounded transition-colors ${
                  selectedLevel === 'RESEARCH'
                    ? 'bg-[#1D0A69] text-white'
                    : 'bg-[#F4F6F8] text-[#546E7A] hover:bg-[#EBEAEA]'
                }`}
              >
                Fellowship & Overseas
              </button>
            </div>
          </div>
        </div>

          {/* Scheme Collection: Distinct Pattern Accent for Each */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredSchemes.map((scheme) => {
              const patternVariant = getSchemePattern(scheme.code);

              return (
                <div 
                  key={scheme.code} 
                  className="bg-[#FFFFFF] border border-[#CFD8DC] hover:border-[#1D0A69] transition-all flex flex-col justify-between group shadow-sm hover:shadow"
                >
                  {/* Scheme Header with Cultural Accent Motif */}
                  <div>
                    {/* Top Subtle Regional Pattern Band (10px) */}
                    <TribalPattern variant={patternVariant} height={8} color="#1D0A69" opacity={0.8} />

                    <div className="p-5 space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs font-bold text-[#1D0A69] bg-[#EBEAEA] px-2 py-0.5 rounded">
                          {scheme.officialCode}
                        </span>
                        <span className="gov-badge gov-badge-success text-[10px]">
                          {language === 'hi' ? 'आवेदन खुले हैं' : 'Applications Open'}
                        </span>
                      </div>

                      <h3 className="text-base font-bold text-[#1D0A69] font-serif group-hover:text-[#0F4C81] transition-colors leading-snug">
                        {language === 'hi' ? scheme.titleHi : scheme.titleEn}
                      </h3>

                      <p className="text-xs text-[#546E7A] line-clamp-2 leading-relaxed">
                        {language === 'hi' ? scheme.benefitsSummaryHi : scheme.benefitsSummaryEn}
                      </p>

                      {/* Editorial Specification Ledger */}
                      <div className="border-t border-[#ECEFF1] pt-3 space-y-1.5 text-xs text-[#263238]">
                        <div className="flex justify-between items-center">
                          <span className="text-[#546E7A]">Income Ceiling:</span>
                          <span className="font-semibold text-[#150202]">
                            {language === 'hi' ? scheme.incomeCeilingHi : scheme.incomeCeilingEn}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-[#546E7A]">Target Group:</span>
                          <span className="font-semibold text-[#150202]">
                            {language === 'hi' ? scheme.targetGroupHi : scheme.targetGroupEn}
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-[#C85A17] font-semibold pt-1">
                          <span className="flex items-center gap-1 text-[11px]">
                            <Calendar className="w-3 h-3" />
                            <span>Deadline:</span>
                          </span>
                          <span className="font-mono text-[11px]">{scheme.deadline}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Scheme Action Ribbon */}
                  <div className="p-4 bg-[#F4F6F8] border-t border-[#CFD8DC] flex items-center justify-between gap-2">
                    <button
                      onClick={() => onSelectScheme(scheme)}
                      className="text-xs font-bold text-[#0F4C81] hover:underline"
                    >
                      {language === 'hi' ? 'दिशानिर्देश देखें →' : 'View Guidelines →'}
                    </button>

                    <button
                      onClick={() => onNavigateTab('wizard')}
                      className="gov-btn gov-btn-primary text-xs py-1.5 px-3.5 font-bold"
                    >
                      <span>{language === 'hi' ? 'आवेदन करें' : 'Apply Online'}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          05. VISUAL NARRATIVE: 6-STAGE DISBURSAL JOURNEY (Non-Card)
          ───────────────────────────────────────────────────────────── */}
      <section className="bg-[#F4F6F8] border-b border-[#CFD8DC] py-12 sm:py-16 relative overflow-hidden">
        <TribalPattern variant="river" asBackground opacity={0.04} color="#0F4C81" />

        <div className="gov-container relative z-10 space-y-10">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-xs font-bold text-[#C85A17] tracking-wider uppercase">
              {language === 'hi' ? 'पारदर्शी डिजिटल कार्यप्रणाली' : 'End-to-End Statutory Workflow'}
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1D0A69] font-serif">
              {language === 'hi' ? '6-चरणीय प्रत्यक्ष लाभ अंतरण (DBT) यात्रा' : 'The 6-Stage Sovereign Disbursal Journey'}
            </h2>
            <p className="text-xs sm:text-sm text-[#546E7A]">
              {language === 'hi'
                ? 'कागजरहित सत्यापन, बहुभाषी ओसीआर एवं सर्वर-साइड पात्रता नियम इंजन द्वारा संरक्षित'
                : 'Cryptographically protected, zero physical paper friction, with automated separation of duties.'}
            </p>
          </div>

          {/* Timeline Structure with Connecting Geometry */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                num: '01',
                titleEn: 'One-Time Registration (OTR)',
                titleHi: 'एकल पंजीकरण (OTR) एवं ई-केवाईसी',
                descEn: 'Aadhaar demographic authentication & DigiLocker integration. Generates permanent ST student identity.',
                descHi: 'आधार जनसांख्यिकी ई-केवाईसी एवं डिजिलॉकर से डिजिटल जाति प्रमाण पत्र का स्वतः सत्यापन।'
              },
              {
                num: '02',
                titleEn: 'Digital Scheme Application',
                titleHi: 'ऑनलाइन आवेदन एवं संस्था चयन',
                descEn: 'Select eligible scheme, course AISHE code, declared family income, and institutional fee particulars.',
                descHi: 'संस्थान कोड (AISHE), पाठ्यक्रम एवं आय विवरण के साथ ऑनलाइन घोषणा पत्र जमा करें।'
              },
              {
                num: '03',
                titleEn: 'OCR Extraction & SHA-256 Check',
                titleHi: 'बहुभाषी ओसीआर एवं मैलवेयर स्कैन',
                descEn: 'ClamAV antivirus quarantine, tamper detection, and provisional field extraction with bounding boxes.',
                descHi: 'दस्तावेज़ की हैश सत्यता, वायरस स्कैन एवं आय-प्रमाण पत्र से अंक व तिथियों का डिजिटल निष्कर्षण।'
              },
              {
                num: '04',
                titleEn: 'Separation-of-Duties Scrutiny',
                titleHi: 'संस्थान एवं जिला नोडल जांच',
                descEn: 'Empanelled college nodal officer and District Welfare Officer scrutinize evidence independently.',
                descHi: 'कॉलेज नोडल अधिकारी एवं जिला कल्याण अधिकारी द्वारा डिजिटल साक्ष्यों की स्वायत्त जांच।'
              },
              {
                num: '05',
                titleEn: 'Deterministic Eligibility Engine',
                titleHi: 'स्वचालित केंद्रीय नियम इंजन',
                descEn: 'Zero discretionary bias. Scheme rules evaluate income cutoffs, academic criteria, and state quotas.',
                descHi: 'बिना किसी मानवीय पक्षपात के, नियम इंजन द्वारा स्वतः मेरिट एवं पात्रता सूची का निर्धारण।'
              },
              {
                num: '06',
                titleEn: 'Direct PFMS Bank Disbursal',
                titleHi: 'आधार-एनपीसीआई प्रत्यक्ष डीबीटी',
                descEn: 'Sanctioned funds transferred directly to the student Aadhaar-seeded bank account with zero middlemen.',
                descHi: 'मंत्रालय द्वारा स्वीकृत छात्रवृत्ति सीधे छात्र के आधार-लिंक बैंक खाते में पीएफएमएस द्वारा अंतरित।'
              }
            ].map((step, idx) => (
              <div 
                key={step.num}
                className="bg-[#FFFFFF] border-l-4 border-l-[#1D0A69] border-t border-r border-b border-[#CFD8DC] p-5 relative"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xl font-extrabold text-[#1D0A69]">
                    {step.num}
                  </span>
                  <span className="text-[10px] font-bold text-[#C85A17] uppercase tracking-wider">
                    STAGE {idx + 1}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-[#1D0A69] font-serif mb-1">
                  {language === 'hi' ? step.titleHi : step.titleEn}
                </h3>
                <p className="text-xs text-[#546E7A] leading-relaxed">
                  {language === 'hi' ? step.descHi : step.descEn}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          06. GAZETTE CIRCULARS & GRIEVANCE (Editorial Dual Column)
          ───────────────────────────────────────────────────────────── */}
      <section className="bg-[#FFFFFF] border-b border-[#CFD8DC] py-10 sm:py-14">
        <div className="gov-container">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left 6 Columns: Gazette & Circulars Ledger */}
            <div className="lg:col-span-6 space-y-4">
              <div className="border-b-2 border-[#1D0A69] pb-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#C85A17]">
                  OFFICIAL GAZETTE
                </span>
                <h2 className="text-xl font-bold text-[#1D0A69] font-serif">
                  {language === 'hi' ? 'महत्वपूर्ण सूचनाएं एवं आधिकारिक परिपत्र' : 'Important Circulars & Gazette Directives'}
                </h2>
              </div>

              <div className="divide-y divide-[#ECEFF1] border border-[#CFD8DC] bg-[#FFFFFF]">
                {[
                  {
                    date: '15-Sep-2026',
                    tag: 'GAZETTE',
                    title: 'Top Class Education: Official gazette list of 265 notified premier institutions (IIT/IIM/NIT) published for AY 2026-27.',
                    titleHi: 'शीर्ष श्रेणी शिक्षा योजना: 265 राष्ट्रीय उत्कृष्ट संस्थानों की आधिकारिक सूची प्रकाशित।'
                  },
                  {
                    date: '01-Aug-2026',
                    tag: 'ADMISSION',
                    title: 'Online applications opened for all 5 central ST scholarship schemes for Academic Year 2026-27.',
                    titleHi: 'सत्र 2026-27 हेतु सभी 5 केंद्रीय छात्रवृत्ति योजनाओं हेतु ऑनलाइन आवेदन प्रारंभ।'
                  },
                  {
                    date: '12-Jun-2026',
                    tag: 'RULE 4.2',
                    title: 'Rule 4.2 Directive: Family income certificates must be issued on or after 01-April-2025 by competent revenue authority.',
                    titleHi: 'नियम 4.2: आय प्रमाण पत्र चालू वित्तीय वर्ष के उपरांत सक्षम प्राधिकारी द्वारा जारी होना अनिवार्य।'
                  }
                ].map((item, idx) => (
                  <div key={idx} className="p-4 hover:bg-[#F8F9FA] transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono font-bold text-[#C85A17]">
                        {item.date}
                      </span>
                      <span className="text-[9px] font-bold bg-[#EBEAEA] text-[#1D0A69] px-1.5 py-0.5 rounded">
                        {item.tag}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-[#150202] leading-snug">
                      {language === 'hi' ? item.titleHi : item.title}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Right 6 Columns: Sovereign Grievance & Student Support */}
            <div className="lg:col-span-6 space-y-4">
              <div className="border-b-2 border-[#C85A17] pb-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#C85A17]">
                  CITIZEN CHARTER
                </span>
                <h2 className="text-xl font-bold text-[#1D0A69] font-serif">
                  {language === 'hi' ? 'छात्र सहायता एवं शिकायत निवारण (CPGRAMS)' : 'Student Helpdesk & Grievance Resolution'}
                </h2>
              </div>

              <div className="bg-[#F8F9FA] border border-[#CFD8DC] p-5 space-y-4">
                <p className="text-xs text-[#263238] leading-relaxed">
                  {language === 'hi'
                    ? 'यदि आपके आवेदन, आय प्रमाण पत्र सत्यापन अथवा बैंक खाते में डीबीटी संबंधी कोई समस्या है, तो आप सीधे राष्ट्रीय एसटी हेल्पडेस्क अथवा सीपीग्राम्स (CPGRAMS) पर शिकायत दर्ज कर सकते हैं।'
                    : 'For grievances concerning document scrutiny, income certificate validity, or PFMS Aadhaar seeding status, raise a formal query with the National ST Helpdesk.'}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="bg-[#FFFFFF] p-3 border border-[#CFD8DC]">
                    <div className="text-[10px] text-[#546E7A] uppercase font-bold">National ST Toll-Free</div>
                    <div className="text-sm font-bold text-[#0F4C81] font-mono mt-0.5">1800-11-7788</div>
                    <div className="text-[10px] text-[#546E7A]">09:30 - 18:00 IST (Mon - Sat)</div>
                  </div>

                  <div className="bg-[#FFFFFF] p-3 border border-[#CFD8DC]">
                    <div className="text-[10px] text-[#546E7A] uppercase font-bold">CPGRAMS Portal</div>
                    <div className="text-sm font-bold text-[#C85A17] font-mono mt-0.5">pgportal.gov.in</div>
                    <div className="text-[10px] text-[#546E7A]">Central Grievance Redressal</div>
                  </div>
                </div>

                <button
                  onClick={() => onNavigateTab('grievance')}
                  className="gov-btn gov-btn-secondary text-xs font-bold w-full py-2.5"
                >
                  <HelpCircle className="w-4 h-4 text-[#C85A17]" />
                  <span>{language === 'hi' ? 'शिकायत दर्ज करें / स्थिति देखें' : 'Register Formal Grievance / Track Status'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Sovereign Cultural Motif Signature Band Before Footer */}
      <TribalPattern variant="mountain" height={10} color="#1D0A69" opacity={0.8} />
    </div>
  );
};
