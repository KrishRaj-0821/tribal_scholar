import React from 'react';
import { HelpCircle, PhoneCall, Mail } from 'lucide-react';

export const HelpView: React.FC = () => {

  const faqs = [
    {
      q: 'Who is eligible to apply for MoTA ST Scholarships?',
      a: 'Students belonging to Scheduled Tribes (ST) and Particularly Vulnerable Tribal Groups (PVTG) who possess an authentic community certificate issued by a competent revenue authority.'
    },
    {
      q: 'What is the Document Vault and why should I use it?',
      a: 'The Document Vault is your personal secure digital locker on the MoTA portal. Upload your certificates (ST, Income, Marksheet) once, and the system securely processes them with ClamAV security scans and OCR text extraction. When applying for multiple schemes, you can auto-fill verified parameters with a single click without re-uploading.'
    },
    {
      q: 'How does the AI / OCR extraction work?',
      a: 'OCR acts as an assistant to read your uploaded document and pre-fill fields like certificate numbers and gross annual income to eliminate repetitive typing. All extracted information is marked as provisional until verified by an authorized scrutiny officer.'
    },
    {
      q: 'How are scholarships disbursed?',
      a: 'All sanctioned scholarships and maintenance stipends are disbursed 100% directly to your Aadhaar-seeded bank account through the National Automated Clearing House (NACH) / NPCI Direct Benefit Transfer (DBT) gateway.'
    }
  ];

  return (
    <div className="bg-[#F4F6F8] min-h-screen pb-20">
      <div className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] py-8">
        <div className="gov-container">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-white/10 flex items-center justify-center text-[#FFC107]">
              <HelpCircle className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs text-[#FFC107] font-bold">CITIZEN SUPPORT & GUIDELINES</div>
              <h1 className="text-2xl font-bold font-serif">Help Desk & FAQs</h1>
              <p className="text-xs text-[#EBEAEA]/80 mt-0.5">
                Guidance for ST students, institutions, and nodal scrutiny officers
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="gov-container py-8 max-w-4xl mx-auto space-y-6">
        {/* Contact Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white p-5 rounded-xl border border-[#CFD8DC] shadow-xs flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E8EAF6] text-[#1D0A69] flex items-center justify-center flex-shrink-0">
              <PhoneCall className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-[#546E7A] font-medium">National Toll-Free Helpline</div>
              <div className="text-base font-bold text-[#1D0A69]">1800-11-7788</div>
              <div className="text-[10px] text-[#78909C]">Monday – Friday, 09:30 AM to 06:00 PM IST</div>
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-[#CFD8DC] shadow-xs flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E8F5E9] text-[#2E7D32] flex items-center justify-center flex-shrink-0">
              <Mail className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-[#546E7A] font-medium">Direct Support Email</div>
              <div className="text-base font-bold text-[#1D0A69]">support-scholarship@mota.gov.in</div>
              <div className="text-[10px] text-[#78909C]">Ministry of Tribal Affairs, Shastri Bhawan, New Delhi</div>
            </div>
          </div>
        </div>

        {/* FAQs */}
        <div className="bg-white rounded-xl shadow-xs border border-[#CFD8DC] p-6 space-y-4">
          <h2 className="text-base font-bold text-[#1D0A69] border-b border-[#ECEFF1] pb-3">
            Frequently Asked Questions (FAQs)
          </h2>
          <div className="space-y-4">
            {faqs.map((faq, idx) => (
              <div key={idx} className="border-b border-[#ECEFF1] pb-4 last:border-b-0">
                <h3 className="text-xs font-bold text-[#1D0A69] flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-[#E8EAF6] text-[#1D0A69] flex items-center justify-center text-[10px]">
                    Q{idx + 1}
                  </span>
                  <span>{faq.q}</span>
                </h3>
                <p className="text-xs text-[#37474F] mt-2 ml-7 leading-relaxed">
                  {faq.a}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
