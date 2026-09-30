import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { TribalPattern } from '../common/TribalPattern';
import { 
  HelpCircle, PhoneCall, CheckCircle2, 
  ChevronDown, ChevronUp, Send, ExternalLink
} from 'lucide-react';

export const GrievanceView: React.FC = () => {
  const { language } = useLanguage();
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [grievanceSubmitted, setGrievanceSubmitted] = useState(false);

  const faqs = [
    {
      q: 'Why was my Income Certificate marked deficient under Rule 4.2?',
      a: 'Under MoTA Statutory Guidelines for Academic Year 2026-27, family income certificates must reflect current earnings and must be issued on or after 01-April-2025 by a competent Revenue Authority (Tehsildar/Circle Officer/SDO). Certificates dated prior to this financial year cutoff are invalid.'
    },
    {
      q: 'What should I do if my bank account is not seeded with Aadhaar on NPCI?',
      a: 'Visit your home bank branch immediately and submit an Aadhaar-NPCI DBT mandate form. Ensure your account is marked as the primary receiving account for Direct Benefit Transfer. You can verify your live seeding status on the UIDAI portal.'
    },
    {
      q: 'How long does the scrutiny process take after resolving a deficiency?',
      a: 'Once you re-upload the valid certificate, it undergoes automated virus scanning and OCR verification within seconds, after which it enters the Institutional Nodal Officer queue. Scrutiny is typically completed within 3 to 5 business days.'
    },
    {
      q: 'Can I apply for multiple MoTA schemes simultaneously?',
      a: 'Under Government of India scholarship guidelines, a student may receive benefits from only one central government scholarship scheme for the same academic degree course.'
    }
  ];

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-20">
      
      {/* 1. Sovereign Masthead with Tribal Identity */}
      <header className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="river" opacity={0.07} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-7">
          <div className="max-w-3xl space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono text-[#FFC107]">
              <span>CENTRAL CITIZEN SUPPORT DESK</span>
              <span>•</span>
              <span>CPGRAMS INTEGRATED</span>
            </div>
            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold font-serif text-white tracking-tight">
              {language === 'hi' 
                ? 'छात्र सहायता एवं शिकायत निवारण पोर्टल' 
                : 'Student Support Desk & Statutory Grievance Redressal'}
            </h1>
            <p className="text-xs text-[#EBEAEA]/80">
              Ministry of Tribal Affairs & Centralized Public Grievance Redress and Monitoring System (CPGRAMS)
            </p>
          </div>
        </div>
      </header>

      {/* 2. Public Service Action Ledger */}
      <main className="gov-container py-8 space-y-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Left Column: Formal Grievance Dossier (7 cols) */}
          <div className="lg:col-span-7 bg-white border border-[#CFD8DC] rounded-lg shadow-sm overflow-hidden">
            <div className="p-6 border-b border-[#ECEFF1] bg-[#F8F9FA] flex items-center justify-between">
              <div>
                <span className="text-[11px] font-bold text-[#C85A17] uppercase tracking-wider block">
                  Docket Submission Desk
                </span>
                <h2 className="text-base font-bold text-[#1D0A69] font-serif">
                  Register Formal Statutory Inquiry or Grievance
                </h2>
              </div>
              <span className="text-[11px] font-mono text-[#546E7A]">SLA: 48h Response</span>
            </div>

            <div className="p-6 sm:p-8">
              {grievanceSubmitted ? (
                <div className="p-6 bg-[#E8F5E9] border border-[#A5D6A7] rounded-lg text-xs text-[#1B5E20] space-y-3">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <CheckCircle2 className="w-5 h-5 text-[#198754]" />
                    <span>Grievance Registered Successfully</span>
                  </div>
                  <p className="leading-relaxed">
                    Official Docket Number: <strong className="font-mono text-[#150202]">MOTA/GRV/2026/09941</strong>. An official response from the Nodal Grievance Officer will be communicated to your registered email and SMS within 48 hours.
                  </p>
                  <div className="pt-2">
                    <button
                      onClick={() => setGrievanceSubmitted(false)}
                      className="gov-btn gov-btn-secondary text-xs font-bold"
                    >
                      Submit Another Query
                    </button>
                  </div>
                </div>
              ) : (
                <form onSubmit={(e) => { e.preventDefault(); setGrievanceSubmitted(true); }} className="space-y-4 text-xs">
                  <div>
                    <label className="gov-label text-xs">
                      One-Time Registration (OTR) / Application Reference Number <span className="gov-req">*</span>
                    </label>
                    <input
                      type="text"
                      className="gov-input text-xs font-mono font-bold text-[#1D0A69]"
                      defaultValue="OTR-2026-ST-884912"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="gov-label text-xs">Target Scheme</label>
                      <select className="gov-select text-xs">
                        <option>Top Class Education for ST Students (TOP-05)</option>
                        <option>Post-Matric Scholarship for ST (PMS-02)</option>
                        <option>National Fellowship for ST Students (NFST-03)</option>
                        <option>National Overseas Scholarship (NOS-04)</option>
                        <option>Pre-Matric Scholarship for ST</option>
                      </select>
                    </div>

                    <div>
                      <label className="gov-label text-xs">Category of Grievance <span className="gov-req">*</span></label>
                      <select className="gov-select text-xs">
                        <option>Rule 4.2 Income Certificate Clarification</option>
                        <option>Aadhaar / NPCI Bank Seeding Verification</option>
                        <option>PFMS DBT Remittance Status</option>
                        <option>Institutional Dean / AISHE Scrutiny Delay</option>
                        <option>Portal Technical / e-Sign Assistance</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="gov-label text-xs">
                      Detailed Submission & Grievance Context <span className="gov-req">*</span>
                    </label>
                    <textarea
                      rows={4}
                      className="gov-input h-auto py-2.5 text-xs font-sans leading-relaxed"
                      placeholder="Specify your application reference, issuing revenue authority, or specific challenge encountered..."
                      required
                    ></textarea>
                  </div>

                  <button
                    type="submit"
                    className="w-full bg-[#1D0A69] hover:bg-[#15074D] text-white font-bold py-3 px-4 rounded text-xs transition-colors flex items-center justify-center gap-2 shadow-xs"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Submit Grievance to MoTA Public Cell</span>
                  </button>
                </form>
              )}
            </div>
          </div>

          {/* Right Column: FAQs & Institutional Helpline (5 cols) */}
          <div className="lg:col-span-5 space-y-6 text-xs">
            
            {/* National Contacts */}
            <div className="bg-white border border-[#CFD8DC] rounded-lg p-5 space-y-3 shadow-xs">
              <div className="flex items-center gap-2 font-bold text-[#1D0A69] font-serif text-sm border-b border-[#ECEFF1] pb-2">
                <PhoneCall className="w-4 h-4 text-[#0F4C81]" />
                <span>Statutory MoTA Helpdesk Contacts</span>
              </div>
              <div className="space-y-2 text-[#263238]">
                <div className="flex justify-between border-b border-[#ECEFF1] pb-1.5">
                  <span className="text-[#546E7A]">Toll-Free Helpline:</span>
                  <strong className="text-[#1D0A69]">1800-11-7788</strong>
                </div>
                <div className="flex justify-between border-b border-[#ECEFF1] pb-1.5">
                  <span className="text-[#546E7A]">Operating Hours:</span>
                  <span>09:30 - 18:00 (Mon - Fri)</span>
                </div>
                <div className="flex justify-between border-b border-[#ECEFF1] pb-1.5">
                  <span className="text-[#546E7A]">Official Email:</span>
                  <strong className="text-[#0F4C81]">grievance-mota@nic.in</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#546E7A]">CPGRAMS Portal:</span>
                  <a href="https://pgportal.gov.in" target="_blank" rel="noopener noreferrer" className="text-[#0F4C81] hover:underline flex items-center gap-1 font-semibold">
                    <span>pgportal.gov.in</span>
                    <ExternalLink className="w-3 h-3 text-[#90A4AE]" />
                  </a>
                </div>
              </div>
            </div>

            {/* Accordion FAQs */}
            <div className="bg-white border border-[#CFD8DC] rounded-lg p-5 space-y-3 shadow-xs">
              <div className="flex items-center gap-2 font-bold text-[#1D0A69] font-serif text-sm border-b border-[#ECEFF1] pb-2">
                <HelpCircle className="w-4 h-4 text-[#0F4C81]" />
                <span>Frequently Answered Inquiries</span>
              </div>

              <div className="space-y-2">
                {faqs.map((faq, idx) => {
                  const isOpen = openFaq === idx;
                  return (
                    <div key={idx} className="border border-[#CFD8DC] rounded overflow-hidden">
                      <button
                        type="button"
                        onClick={() => setOpenFaq(isOpen ? null : idx)}
                        className="w-full p-3 text-left bg-[#F8F9FA] hover:bg-[#ECEFF1] flex items-center justify-between font-bold text-[#150202] transition-colors"
                      >
                        <span className="pr-2">{faq.q}</span>
                        {isOpen ? <ChevronUp className="w-4 h-4 text-[#546E7A] flex-shrink-0" /> : <ChevronDown className="w-4 h-4 text-[#546E7A] flex-shrink-0" />}
                      </button>
                      {isOpen && (
                        <div className="p-3 bg-white text-[#263238] border-t border-[#CFD8DC] leading-relaxed">
                          {faq.a}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

          </div>

        </div>
      </main>
    </div>
  );
};
