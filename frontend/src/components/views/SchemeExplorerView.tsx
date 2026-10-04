import React, { useState, useEffect } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { OFFICIAL_MOTA_SCHEMES, SchemeInfo } from '../../theme/tokens';
import { schemesApi } from '../../services/api';
import { TribalPattern, TribalPatternVariant } from '../common/TribalPattern';
import { 
  Filter, Search, FileText, ArrowRight, 
  Calendar, ChevronRight, RefreshCw, CheckCircle2
} from 'lucide-react';

interface SchemeExplorerViewProps {
  onSelectScheme: (scheme: SchemeInfo) => void;
  onApplyScheme: (scheme: SchemeInfo) => void;
}

export const SchemeExplorerView: React.FC<SchemeExplorerViewProps> = ({
  onSelectScheme,
  onApplyScheme
}) => {
  const { language } = useLanguage();
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [incomeFilter, setIncomeFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [backendSynced, setBackendSynced] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const fetchLiveSchemes = async () => {
      setLoading(true);
      try {
        const res = await schemesApi.list();
        if (isMounted && res) {
          setBackendSynced(true);
        }
      } catch (e) {
        console.warn('Backend schemes synchronization fallback:', e);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchLiveSchemes();
    return () => { isMounted = false; };
  }, []);

  const getSchemePattern = (code: string): TribalPatternVariant => {
    switch (code) {
      case 'PRE-01': return 'forest';
      case 'PMS-02': return 'river';
      case 'TOP-05': return 'woven';
      case 'NFST-03': return 'earth';
      case 'NOS-04': return 'mountain';
      default: return 'community';
    }
  };

  const filteredSchemes = OFFICIAL_MOTA_SCHEMES.filter(scheme => {
    // Category Filter
    if (selectedCategory !== 'ALL' && scheme.category !== selectedCategory) {
      return false;
    }
    // Income Filter
    if (incomeFilter === '2.5L' && !scheme.incomeCeilingEn.includes('2,50,000')) {
      return false;
    }
    if (incomeFilter === '6L' && !scheme.incomeCeilingEn.includes('6,00,000')) {
      return false;
    }
    if (incomeFilter === '8L' && !scheme.incomeCeilingEn.includes('8,00,000')) {
      return false;
    }
    if (incomeFilter === 'NONE' && !scheme.incomeCeilingEn.includes('No Income Ceiling')) {
      return false;
    }
    // Search Query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchEn = scheme.titleEn.toLowerCase().includes(q) || scheme.officialCode.toLowerCase().includes(q);
      const matchHi = scheme.titleHi.includes(q);
      if (!matchEn && !matchHi) return false;
    }
    return true;
  });

  return (
    <div className="gov-container py-6 space-y-6">
      {/* Breadcrumb Navigation */}
      <nav className="text-xs text-[#546E7A] flex items-center gap-1.5" aria-label="Breadcrumb">
        <a href="#home" className="hover:underline text-[#0F4C81]">
          {language === 'hi' ? 'मुख्य पृष्ठ' : 'Home'}
        </a>
        <ChevronRight className="w-3 h-3 text-[#90A4AE]" />
        <span className="text-[#150202] font-semibold">
          {language === 'hi' ? 'योजना खोज एवं विवरण (Scheme Explorer)' : 'Scheme Explorer & Guidelines'}
        </span>
      </nav>

      {/* Page Header */}
      <div className="border-b border-[#CFD8DC] pb-4">
        <h1 className="text-2xl sm:text-3xl text-[#1D0A69] font-serif font-bold">
          {language === 'hi' 
            ? 'अनुसूचित जनजाति छात्रवृत्ति योजनाएं (सत्र 2026-27)' 
            : 'Statutory ST Scholarships & Fellowships Directory (AY 2026-27)'}
        </h1>
        <p className="text-xs sm:text-sm text-[#546E7A] mt-1">
          {language === 'hi'
            ? 'जनजातीय कार्य मंत्रालय, भारत सरकार द्वारा प्रशासित 5 केंद्रीय क्षेत्र एवं केंद्र प्रायोजित योजनाएं।'
            : 'Official directory of Central Sector and Centrally Sponsored ST Welfare Schemes governed by the Ministry of Tribal Affairs.'}
        </p>
      </div>

      {/* Two Column Layout: Filter Sidebar (28%) + Scheme Cards (72%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Filter Sidebar */}
        <aside className="lg:col-span-4 space-y-4">
          <div className="gov-card">
            <div className="gov-card-header">
              <h2 className="text-sm font-bold text-[#1D0A69] flex items-center gap-1.5 font-serif">
                <Filter className="w-4 h-4 text-[#1D0A69]" />
                {language === 'hi' ? 'योजना फिल्टर (Filters)' : 'Filter Statutory Schemes'}
              </h2>
              <button 
                onClick={() => {
                  setSelectedCategory('ALL');
                  setIncomeFilter('ALL');
                  setSearchQuery('');
                }}
                className="text-[11px] text-[#0F4C81] hover:underline"
              >
                {language === 'hi' ? 'रीसेट करें' : 'Reset All'}
              </button>
            </div>

            {/* Keyword Search */}
            <div className="space-y-3 text-xs">
              <div>
                <label className="gov-label text-xs">
                  {language === 'hi' ? 'कीवर्ड खोज (Search)' : 'Keyword / Scheme Code'}
                </label>
                <div className="relative">
                  <input
                    type="text"
                    className="gov-input text-xs pl-8"
                    placeholder="e.g. Top Class, NFST, 2.5L"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  <Search className="w-3.5 h-3.5 text-[#546E7A] absolute left-2.5 top-3" />
                </div>
              </div>

              {/* Education Level */}
              <div>
                <label className="gov-label text-xs">
                  {language === 'hi' ? 'शिक्षा स्तर (Education Level)' : 'Education Level'}
                </label>
                <select 
                  className="gov-select text-xs"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                >
                  <option value="ALL">{language === 'hi' ? 'सभी स्तर (All Levels)' : 'All Education Levels'}</option>
                  <option value="PRE_MATRIC">{language === 'hi' ? 'प्री-मैट्रिक (कक्षा 9 व 10)' : 'Pre-Matric (Class IX & X)'}</option>
                  <option value="POST_MATRIC">{language === 'hi' ? 'पोस्ट-मैट्रिक (कक्षा 11 से स्नातकोत्तर)' : 'Post-Matric (Class XI to PG)'}</option>
                  <option value="TOP_CLASS">{language === 'hi' ? 'शीर्ष संस्थान (IIT/IIM/AIIMS/NIT)' : 'Top Class Premier Institutes'}</option>
                  <option value="FELLOWSHIP">{language === 'hi' ? 'अध्येतावृत्ति (M.Phil / Ph.D.)' : 'National Fellowship (M.Phil / Ph.D.)'}</option>
                  <option value="OVERSEAS">{language === 'hi' ? 'विदेश में उच्च अध्ययन (Overseas)' : 'National Overseas (Masters / Ph.D. Abroad)'}</option>
                </select>
              </div>

              {/* Annual Family Income Ceiling */}
              <div>
                <label className="gov-label text-xs">
                  {language === 'hi' ? 'वार्षिक पारिवारिक आय सीमा (Income Cap)' : 'Annual Family Income Limit'}
                </label>
                <div className="space-y-1.5 pt-1">
                  {[
                    { id: 'ALL', labelEn: 'All Income Levels', labelHi: 'सभी आय वर्ग' },
                    { id: '2.5L', labelEn: 'Up to ₹2,50,000 / year', labelHi: '₹2,50,000 तक (Pre/Post Matric)' },
                    { id: '6L', labelEn: 'Up to ₹6,00,000 / year', labelHi: '₹6,00,000 तक (Top Class)' },
                    { id: '8L', labelEn: 'Up to ₹8,00,000 / year', labelHi: '₹8,00,000 तक (Overseas NOS)' },
                    { id: 'NONE', labelEn: 'No Income Cap (Fellowship)', labelHi: 'कोई आय सीमा नहीं (NFST)' }
                  ].map((option) => (
                    <label key={option.id} className="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="radio" 
                        name="incomeFilter" 
                        value={option.id}
                        checked={incomeFilter === option.id}
                        onChange={(e) => setIncomeFilter(e.target.value)}
                        className="text-[#1D0A69]"
                      />
                      <span className="text-xs text-[#263238]">
                        {language === 'hi' ? option.labelHi : option.labelEn}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Statutory Aadhaar Direct DBT Alert */}
              <div className="bg-[#E8F5E9] border border-[#A5D6A7] p-2.5 rounded text-[11px] text-[#1B5E20] leading-relaxed">
                <strong>{language === 'hi' ? 'अनिवार्य डीबीटी नियम:' : 'Mandatory DBT Clause:'}</strong>{' '}
                {language === 'hi'
                  ? 'सभी छात्रवृत्ति राशियों का भुगतान सीधे छात्र के आधार से जुड़े सक्रिय बैंक खाते में ही किया जाता है।'
                  : 'All scholarship stipends are disbursed exclusively into Aadhaar-seeded student bank accounts via PFMS.'}
              </div>
            </div>
          </div>
        </aside>

        {/* Right Scheme Directory (8 Cols) */}
        <main className="lg:col-span-8 space-y-4">
          <div className="flex items-center justify-between text-xs text-[#546E7A] bg-white p-2.5 rounded border border-[#CFD8DC]">
            <div className="flex items-center gap-2">
              <span>
                {language === 'hi' 
                  ? `कुल ${filteredSchemes.length} योजनाएं उपलब्ध` 
                  : `Showing ${filteredSchemes.length} Statutory MoTA Schemes`}
              </span>
              {loading ? (
                <span className="flex items-center gap-1 text-[11px] text-[#0F4C81]">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  <span>Syncing...</span>
                </span>
              ) : backendSynced ? (
                <span className="flex items-center gap-1 text-[10px] text-[#198754] font-semibold bg-[#E8F5E9] px-2 py-0.5 rounded">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Backend Live</span>
                </span>
              ) : null}
            </div>
            <div className="font-semibold text-[#1D0A69]">
              Academic Year: 2026-2027
            </div>
          </div>

          {filteredSchemes.length === 0 ? (
            <div className="gov-card text-center py-12 space-y-3">
              <FileText className="w-10 h-10 text-[#CFD8DC] mx-auto" />
              <div className="text-base font-bold text-[#1D0A69]">
                {language === 'hi' ? 'कोई योजना नहीं मिली' : 'No Schemes Match Your Filter'}
              </div>
              <p className="text-xs text-[#546E7A]">
                {language === 'hi' 
                  ? 'कृपया अन्य फिल्टर विकल्पों का चयन करें अथवा रीसेट करें।' 
                  : 'Please adjust your filter parameters or reset filters.'}
              </p>
              <button
                onClick={() => {
                  setSelectedCategory('ALL');
                  setIncomeFilter('ALL');
                  setSearchQuery('');
                }}
                className="gov-btn gov-btn-secondary text-xs"
              >
                Reset All Filters
              </button>
            </div>
          ) : (
            filteredSchemes.map((scheme) => (
              <article 
                key={scheme.code} 
                className="bg-[#FFFFFF] border border-[#CFD8DC] hover:border-[#1D0A69] transition-all overflow-hidden shadow-sm flex flex-col justify-between"
              >
                <div>
                  <TribalPattern variant={getSchemePattern(scheme.code)} height={8} color="#1D0A69" opacity={0.85} />
                  <div className="p-5 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#ECEFF1] pb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold bg-[#1D0A69] text-white px-2 py-0.5 rounded">
                      {scheme.officialCode}
                    </span>
                    <span className="text-[11px] text-[#546E7A]">
                      {scheme.gazetteRef}
                    </span>
                  </div>
                  <span className="gov-badge gov-badge-success text-xs">
                    {language === 'hi' ? 'आवेदन खुले हैं' : 'Applications Open'}
                  </span>
                </div>

                <div>
                  <h2 className="text-lg font-bold text-[#1D0A69] font-serif leading-snug">
                    {language === 'hi' ? scheme.titleHi : scheme.titleEn}
                  </h2>
                  <p className="text-xs text-[#546E7A] mt-1 leading-relaxed">
                    {language === 'hi' ? scheme.targetGroupHi : scheme.targetGroupEn}
                  </p>
                </div>

                {/* Key Attributes Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-[#F4F6F8] p-3 rounded border border-[#CFD8DC]">
                  <div>
                    <div className="text-[11px] text-[#546E7A] uppercase font-bold">
                      {language === 'hi' ? 'आय पात्रता सीमा' : 'Annual Income Ceiling'}
                    </div>
                    <div className="font-semibold text-[#150202] mt-0.5">
                      {language === 'hi' ? scheme.incomeCeilingHi : scheme.incomeCeilingEn}
                    </div>
                  </div>

                  <div>
                    <div className="text-[11px] text-[#546E7A] uppercase font-bold">
                      {language === 'hi' ? 'वित्तीय लाभ विवरण' : 'Financial Coverage'}
                    </div>
                    <div className="font-semibold text-[#150202] mt-0.5">
                      {language === 'hi' ? scheme.benefitsSummaryHi : scheme.benefitsSummaryEn}
                    </div>
                  </div>

                  <div>
                    <div className="text-[11px] text-[#546E7A] uppercase font-bold">
                      {language === 'hi' ? 'वार्षिक बजटीय आवंटन' : 'Central Budget Outlay'}
                    </div>
                    <div className="font-semibold text-[#198754] mt-0.5">
                      ₹{scheme.annualBudgetCr}.00 Crore / Year
                    </div>
                  </div>

                  <div>
                    <div className="text-[11px] text-[#546E7A] uppercase font-bold">
                      {language === 'hi' ? 'आवेदन की अंतिम तिथि' : 'Application Deadline'}
                    </div>
                    <div className="font-semibold text-[#C85A17] mt-0.5 flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{scheme.deadline}</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                  <button
                    onClick={() => onSelectScheme(scheme)}
                    className="text-xs font-bold text-[#0F4C81] hover:underline flex items-center gap-1"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>{language === 'hi' ? 'पूर्ण वैधानिक दिशानिर्देश देखें' : 'View Full Statutory Guidelines'}</span>
                  </button>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onSelectScheme(scheme)}
                      className="gov-btn gov-btn-secondary text-xs py-1.5 px-3"
                    >
                      {language === 'hi' ? 'विवरण' : 'Scheme Details'}
                    </button>
                    <button
                      onClick={() => onApplyScheme(scheme)}
                      className="gov-btn gov-btn-primary text-xs py-1.5 px-4 font-bold"
                    >
                      <span>{language === 'hi' ? 'आवेदन करें' : 'Apply Now'}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  </div>
                </div>
              </div>
            </article>
            ))
          )}
        </main>
      </div>
    </div>
  );
};
