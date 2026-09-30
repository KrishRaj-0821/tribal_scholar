/**
 * Government of India DBIM 3.0 & MoTA Sovereign Design System Tokens
 * Strictly aligned with GIGW 3.0 (Guidelines for Indian Government Websites)
 * Stitch Asset: assets/18228296055994121637
 */

export const GOV_TOKENS = {
  colors: {
    // Primary Institutional Colors
    deepBlue: '#1D0A69',           // Sovereign Primary Navy
    ashokaBlue: '#0F4C81',         // Secondary Administrative Blue
    deepEarthyBrown: '#150202',    // Primary Text (Replaces harsh black, high legibility)
    inclusiveWhite: '#FFFFFF',     // Base Surface / Card Background
    linen: '#EBEAEA',              // Secondary Neutral / Card Tint
    neutralCanvas: '#F4F6F8',      // Institutional Cool Slate Canvas
    neutralSlate: '#263238',       // Neutral Charcoal / Muted Text
    neutralMuted: '#546E7A',       // Tertiary Helper / Label Text
    borderHairline: '#CFD8DC',     // Standard Structural 1px Border
    borderSubtle: '#ECEFF1',       // Table Row / Subtle Divider
    
    // Heritage & Cultural Accents (Restrained, derived from Indian earth pigments)
    terracottaOchre: '#C85A17',    // Heritage Accent / Attention Flag
    saffronTricolor: '#FF9933',    // Top Edge Tricolor Accent
    greenTricolor: '#138808',      // Top Edge Tricolor Green
    
    // Statutory Functional Status Colors
    libertyGreen: '#198754',       // Success / DBT Disbursed / Hash Verified
    libertyGreenBg: '#E8F5E9',     // Light container for success badge
    libertyGreenBorder: '#A5D6A7', // Border for success badge
    
    mustardYellow: '#FFC107',      // Warning / Deficiency Notice
    mustardYellowText: '#7A5E00',  // Accessible text on yellow container
    mustardYellowBg: '#FFF9C4',    // Light container for warning/deficiency
    mustardYellowBorder: '#FFE082',// Border for warning badge
    
    crimsonMaroon: '#A71D2A',      // Critical / Application Rejected / Conflict
    crimsonMaroonBg: '#FFEBEE',    // Light container for error
    crimsonMaroonBorder: '#FFCDD2',// Border for error badge
    
    infoBlue: '#0288D1',           // Informational Notice
    infoBlueBg: '#E1F5FE',         // Light container for info
    infoBlueBorder: '#B3E5FC'      // Border for info badge
  },
  
  typography: {
    fontSans: "'Noto Sans', 'Noto Sans Devanagari', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    fontSerif: "'Noto Serif', Georgia, 'Times New Roman', serif",
    fontMono: "'JetBrains Mono', 'Courier New', monospace"
  },
  
  radii: {
    none: '0px',
    sm: '2px',
    default: '4px',    // Preferred government range (4px - 10px)
    md: '6px',
    lg: '8px'
  },
  
  shadows: {
    none: 'none',
    subtle: '0 1px 2px 0 rgba(21, 2, 2, 0.05)',
    card: '0 1px 3px 0 rgba(29, 10, 105, 0.08), 0 1px 2px -1px rgba(29, 10, 105, 0.05)',
    dropdown: '0 4px 6px -1px rgba(29, 10, 105, 0.1), 0 2px 4px -2px rgba(29, 10, 105, 0.06)'
  },
  
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
    '2xl': '32px',
    '3xl': '48px',
    '4xl': '64px'
  }
} as const;

export type SchemeCode = 'PMS-01' | 'PMS-02' | 'TOP-05' | 'NFST-03' | 'NOS-04';

export interface SchemeInfo {
  code: SchemeCode;
  officialCode: string;
  titleEn: string;
  titleHi: string;
  category: 'PRE_MATRIC' | 'POST_MATRIC' | 'TOP_CLASS' | 'FELLOWSHIP' | 'OVERSEAS';
  gazetteRef: string;
  incomeCeilingEn: string;
  incomeCeilingHi: string;
  targetGroupEn: string;
  targetGroupHi: string;
  benefitsSummaryEn: string;
  benefitsSummaryHi: string;
  annualBudgetCr: number;
  totalBeneficiariesTarget: string;
  status: 'OPEN' | 'CLOSING_SOON' | 'UNDER_SCRUTINY';
  deadline: string;
}

export const OFFICIAL_MOTA_SCHEMES: SchemeInfo[] = [
  {
    code: 'PMS-01',
    officialCode: 'MOTA-SCH-PMS-01',
    titleEn: 'Pre-Matric Scholarship for ST Students (Class IX & X)',
    titleHi: 'अनुसूचित जनजाति के छात्रों हेतु प्री-मैट्रिक छात्रवृत्ति (कक्षा 9 एवं 10)',
    category: 'PRE_MATRIC',
    gazetteRef: 'Gazette of India Extra. Part II Sec 3(i) No. 412/2021',
    incomeCeilingEn: 'Up to ₹2,50,000 per annum',
    incomeCeilingHi: 'वार्षिक पारिवारिक आय ₹2,50,000 तक',
    targetGroupEn: 'Full-time regular ST students studying in Classes IX & X in recognized government or private schools.',
    targetGroupHi: 'मान्यता प्राप्त सरकारी अथवा निजी विद्यालयों में कक्षा 9 व 10 में अध्ययनरत नियमित एसटी छात्र।',
    benefitsSummaryEn: 'Day Scholars: ₹3,500/year; Hostellers: ₹7,000/year + Book grant ₹1,000/year paid directly via DBT.',
    benefitsSummaryHi: 'डे-स्कॉलर: ₹3,500/वर्ष; छात्रावास: ₹7,000/वर्ष + पुस्तक अनुदान ₹1,000 डीबीटी के माध्यम से।',
    annualBudgetCr: 450,
    totalBeneficiariesTarget: '4,50,000 Students PAN-India',
    status: 'OPEN',
    deadline: '31 Oct 2026'
  },
  {
    code: 'PMS-02',
    officialCode: 'MOTA-SCH-PMS-02',
    titleEn: 'Post-Matric Scholarship for ST Students (Class XI to Post-Graduate)',
    titleHi: 'अनुसूचित जनजाति के छात्रों हेतु पोस्ट-मैट्रिक छात्रवृत्ति (कक्षा 11 से स्नातकोत्तर)',
    category: 'POST_MATRIC',
    gazetteRef: 'Gazette Notification No. 11014/02/2022-Scholarship',
    incomeCeilingEn: 'Up to ₹2,50,000 per annum',
    incomeCeilingHi: 'वार्षिक पारिवारिक आय ₹2,50,000 तक',
    targetGroupEn: 'All ST candidates pursuing recognized post-matriculation or post-secondary courses in government-approved colleges and universities.',
    targetGroupHi: 'मान्यता प्राप्त संस्थानों में कक्षा 11, 12, आईटीआई, डिप्लोमा, डिग्री अथवा स्नातकोत्तर अध्ययनरत एसटी छात्र।',
    benefitsSummaryEn: '100% compulsory non-refundable fees reimbursement + monthly maintenance allowance up to ₹1,200/month.',
    benefitsSummaryHi: '100% गैर-वापसी योग्य अनिवार्य शिक्षण शुल्क प्रतिपूर्ति + निर्वाह भत्ता ₹1,200/माह तक।',
    annualBudgetCr: 2100,
    totalBeneficiariesTarget: '12,00,000 Students across all States/UTs',
    status: 'OPEN',
    deadline: '31 Oct 2026'
  },
  {
    code: 'TOP-05',
    officialCode: 'MOTA-SCH-TOP-05',
    titleEn: 'Scheme of Top Class Education for ST Students in Notified Institutes',
    titleHi: 'अधिसूचित उत्कृष्ट संस्थानों में एसटी छात्रों हेतु शीर्ष श्रेणी शिक्षा योजना',
    category: 'TOP_CLASS',
    gazetteRef: 'MoTA Notification No. 11017/01/2023-Education',
    incomeCeilingEn: 'Up to ₹6,00,000 per annum',
    incomeCeilingHi: 'वार्षिक पारिवारिक आय ₹6,00,000 तक',
    targetGroupEn: 'Meritorious ST students securing admission in 265 notified premier institutions (IITs, NITs, IIMs, AIIMS, NLUs, IIITs, NID).',
    targetGroupHi: '265 अधिसूचित राष्ट्रीय संस्थानों (आईआईटी, एनआईटी, आईआईएम, एम्स, एनएलयू) में प्रवेश प्राप्त एसटी छात्र।',
    benefitsSummaryEn: 'Full tuition fee reimbursement (up to ₹2.00 Lakh in private / actuals in Govt) + Living expenses ₹3,000/mo + Books & Stationery ₹5,000/yr + Computer grant ₹45,000 one-time.',
    benefitsSummaryHi: 'संपूर्ण शिक्षण शुल्क प्रतिपूर्ति + निर्वाह भत्ता ₹3,000/माह + पुस्तक अनुदान ₹5,000/वर्ष + कंप्यूटर अनुदान ₹45,000 एकमुश्त।',
    annualBudgetCr: 85,
    totalBeneficiariesTarget: '2,500 Fresh Slots / Year',
    status: 'OPEN',
    deadline: '31 Oct 2026'
  },
  {
    code: 'NFST-03',
    officialCode: 'MOTA-SCH-NFST-03',
    titleEn: 'National Fellowship for Higher Education of ST Students (M.Phil / Ph.D.)',
    titleHi: 'एसटी छात्रों के उच्च अध्ययन हेतु राष्ट्रीय अध्येतावृत्ति (एम.फिल / पीएच.डी.)',
    category: 'FELLOWSHIP',
    gazetteRef: 'Resolution No. 11019/04/2021-Tribal Welfare',
    incomeCeilingEn: 'No Income Ceiling (Pure Academic Merit & UGC NET/GATE)',
    incomeCeilingHi: 'कोई आय सीमा नहीं (विशुद्ध अकादमिक योग्यता एवं यूजीसी नेट/गेट)',
    targetGroupEn: 'ST scholars registered for regular and full-time M.Phil / Ph.D. in Sciences, Engineering, Humanities, and Social Sciences.',
    targetGroupHi: 'विश्वविद्यालयों में नियमित एवं पूर्णकालिक एम.फिल अथवा पीएच.डी. पंजीकृत एसटी शोध अध्येता।',
    benefitsSummaryEn: 'JRF: ₹31,000/month; SRF: ₹35,000/month + Contingency grant (₹10,000 - ₹20,500/year) + HRA as applicable + Escort/Reader allowance for Divyangjan.',
    benefitsSummaryHi: 'जेआरएफ: ₹31,000/माह; एसआरएफ: ₹35,000/माह + आकस्मिक व्यय अनुदान + एचआरए + दिव्यांग भत्ता।',
    annualBudgetCr: 120,
    totalBeneficiariesTarget: '750 New Fellowship Slots / Year',
    status: 'OPEN',
    deadline: '15 Nov 2026'
  },
  {
    code: 'NOS-04',
    officialCode: 'MOTA-SCH-NOS-04',
    titleEn: 'National Overseas Scholarship for Scheduled Tribe Candidates (NOS)',
    titleHi: 'अनुसूचित जनजाति के अभ्यर्थियों हेतु राष्ट्रीय प्रवासी छात्रवृत्ति (एनओएस)',
    category: 'OVERSEAS',
    gazetteRef: 'MoTA Guideline Ref. 11015/03/2024-Overseas',
    incomeCeilingEn: 'Up to ₹8,00,000 per annum',
    incomeCeilingHi: 'वार्षिक पारिवारिक आय ₹8,00,000 तक',
    targetGroupEn: 'ST candidates selected for Masters, Ph.D. or Post-Doctoral research programs in QS World Top 500 accredited foreign universities.',
    targetGroupHi: 'क्यूएस विश्व शीर्ष 500 विदेशी विश्वविद्यालयों में स्नातकोत्तर अथवा डॉक्टरेट हेतु चयनित एसटी छात्र।',
    benefitsSummaryEn: '100% actual tuition fees paid directly to foreign university + Annual Maintenance Allowance (£9,900 UK / $15,400 USA) + Return Airfare + Visa fees + Medical Insurance.',
    benefitsSummaryHi: '100% वास्तविक विदेशी शिक्षण शुल्क + वार्षिक निर्वाह भत्ता (£9,900 / $15,400) + हवाई यात्रा + वीजा व स्वास्थ्य बीमा।',
    annualBudgetCr: 60,
    totalBeneficiariesTarget: '20 Awardees / Year (30% Reserved for ST Women)',
    status: 'OPEN',
    deadline: '30 Nov 2026'
  }
];
