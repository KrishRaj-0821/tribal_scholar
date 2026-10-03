import React from 'react';
import { Award } from 'lucide-react';

export const AboutView: React.FC = () => {

  return (
    <div className="bg-[#F4F6F8] min-h-screen pb-20">
      <div className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] py-8">
        <div className="gov-container">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-white/10 flex items-center justify-center text-[#FFC107]">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs text-[#FFC107] font-bold">SOVEREIGN MISSION & GOVERNANCE</div>
              <h1 className="text-2xl font-bold font-serif">Ministry of Tribal Affairs (MoTA)</h1>
              <p className="text-xs text-[#EBEAEA]/80 mt-0.5">
                Empowering Scheduled Tribe Scholars under Article 342 of the Constitution of India
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="gov-container py-8 max-w-4xl mx-auto space-y-6">
        <div className="bg-white rounded-xl shadow-xs border border-[#CFD8DC] p-6 space-y-4 text-xs leading-relaxed text-[#37474F]">
          <h2 className="text-base font-bold text-[#1D0A69] border-b border-[#ECEFF1] pb-2">
            About the Tribal Scholar Platform
          </h2>
          <p>
            The Ministry of Tribal Affairs (MoTA), Government of India, is the nodal authority responsible for overall policy, planning, and coordination of programs for the development of Scheduled Tribes.
          </p>
          <p>
            The <strong>Unified Tribal Scholar Platform</strong> modernizes national scholarship and fellowship administration. It eliminates document forgery, reduces processing delays, and provides an end-to-end transparent workflow from application filing to Direct Benefit Transfer (DBT) bank disbursal.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-[#ECEFF1]">
            <div className="p-4 bg-[#F8F9FA] rounded-lg border border-[#ECEFF1]">
              <div className="font-bold text-sm text-[#1D0A69] mb-1">Deterministic Rules</div>
              <div className="text-[11px] text-[#546E7A]">
                Cryptographically bound eligibility evaluation based on official gazette guidelines.
              </div>
            </div>

            <div className="p-4 bg-[#F8F9FA] rounded-lg border border-[#ECEFF1]">
              <div className="font-bold text-sm text-[#1D0A69] mb-1">Document Vault</div>
              <div className="text-[11px] text-[#546E7A]">
                Secure one-time certificate storage with reusable verified metadata across schemes.
              </div>
            </div>

            <div className="p-4 bg-[#F8F9FA] rounded-lg border border-[#ECEFF1]">
              <div className="font-bold text-sm text-[#1D0A69] mb-1">100% Direct DBT</div>
              <div className="text-[11px] text-[#546E7A]">
                Zero-leakage stipend transfer directly into Aadhaar-seeded student bank accounts.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
