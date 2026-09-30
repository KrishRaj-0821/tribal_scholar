import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { TribalPattern } from '../common/TribalPattern';
import { 
  UploadCloud, CheckCircle2, 
  ArrowLeft, RefreshCw, ArrowRight, ShieldCheck, 
  FileText, Clock, FileWarning, Check
} from 'lucide-react';

interface DeficiencyResolutionViewProps {
  onBack: () => void;
  onResolved: () => void;
}

export const DeficiencyResolutionView: React.FC<DeficiencyResolutionViewProps> = ({
  onBack,
  onResolved
}) => {
  const { language } = useLanguage();
  const [fileSelected, setFileSelected] = useState<File | null>(null);
  const [uploadStage, setUploadStage] = useState<'IDLE' | 'UPLOADING' | 'SCANNING' | 'OCR_PROCESSING' | 'COMPLETED'>('IDLE');
  const [extractedIncome, setExtractedIncome] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFileSelected(e.target.files[0]);
    }
  };

  const handleStartProcessing = () => {
    setUploadStage('UPLOADING');
    setTimeout(() => {
      setUploadStage('SCANNING'); // ClamAV scan
      setTimeout(() => {
        setUploadStage('OCR_PROCESSING'); // PaddleOCR entity extraction
        setTimeout(() => {
          setUploadStage('COMPLETED');
          setExtractedIncome('₹2,40,000 (FY 2025-26)');
        }, 1100);
      }, 1100);
    }, 900);
  };

  return (
    <div className="bg-[#EBEAEA]/50 min-h-screen pb-20">
      
      {/* 1. Sovereign Breadcrumb & Statutory Authority Ribbon */}
      <div className="bg-white border-b border-[#CFD8DC]">
        <div className="gov-container py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <nav className="text-[#546E7A] flex items-center gap-1.5" aria-label="Breadcrumb">
            <button 
              onClick={onBack} 
              className="hover:underline text-[#1D0A69] font-bold flex items-center gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'डैशबोर्ड' : 'Dashboard'}</span>
            </button>
            <span>/</span>
            <span className="font-mono text-[#546E7A]">MOTA/2026/TC/09841</span>
            <span>/</span>
            <span className="text-[#150202] font-semibold">Deficiency Rectification Desk</span>
          </nav>

          <div className="flex items-center gap-2 text-[11px] text-[#C85A17] font-bold">
            <Clock className="w-3.5 h-3.5" />
            <span>Rectification Cutoff: 15-Nov-2026 (14 Days Remaining)</span>
          </div>
        </div>
      </div>

      {/* 2. Editorial Header with Tribal Pattern Accent */}
      <header className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="woven" opacity={0.08} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-7">
          <div className="max-w-3xl space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono text-[#FFC107]">
              <span>STATUTORY SCRUTINY MEMO #DEF-2026-JH-8821</span>
              <span>•</span>
              <span>RULE 4.2 ENFORCEMENT</span>
            </div>
            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold font-serif text-white tracking-tight">
              {language === 'hi' 
                ? 'दस्तावेज़ कमी सुधार कार्यक्षेत्र — वार्षिक पारिवारिक आय प्रमाण पत्र' 
                : 'Deficiency Rectification Desk — Annual Family Income Certificate'}
            </h1>
            <p className="text-xs sm:text-sm text-[#EBEAEA]/85 font-sans leading-relaxed">
              Official Scrutiny Notice issued under Section 4.2 of the Ministry of Tribal Affairs Top Class Scholarship Scheme Guidelines for Academic Year 2026-27.
            </p>
          </div>
        </div>
      </header>

      {/* 3. Main Split Ledger Comparison Terminal */}
      <main className="gov-container py-8 space-y-6">
        
        {/* Split Ledger: Left = Flagged Discrepancy, Right = Statutory Mandate */}
        <div className="grid grid-cols-1 lg:grid-cols-12 border border-[#CFD8DC] rounded-lg overflow-hidden bg-white shadow-sm">
          
          {/* Flagged Document Ledger (6 cols) */}
          <div className="lg:col-span-6 p-6 border-b lg:border-b-0 lg:border-r border-[#CFD8DC] bg-[#FFFDE7]/40 space-y-4">
            <div className="flex items-center justify-between border-b border-[#FFE082] pb-2">
              <div className="flex items-center gap-2">
                <FileWarning className="w-5 h-5 text-[#C85A17]" />
                <span className="font-bold font-serif text-sm text-[#150202]">
                  1. Current Flagged Document on Record
                </span>
              </div>
              <span className="bg-[#C85A17] text-white text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                Deficiency Raised
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-3 gap-1">
                <span className="text-[#546E7A]">Uploaded File:</span>
                <span className="col-span-2 font-mono font-bold text-[#150202]">JH-INC-2024-1102.pdf</span>
              </div>
              <div className="grid grid-cols-3 gap-1">
                <span className="text-[#546E7A]">Issuance Date:</span>
                <span className="col-span-2 text-[#C85A17] font-bold font-mono">14-August-2024 (Prior FY)</span>
              </div>
              <div className="grid grid-cols-3 gap-1">
                <span className="text-[#546E7A]">Scrutiny Officer:</span>
                <span className="col-span-2 text-[#150202]">S. K. Mahapatra (District Scrutiny Officer, Ranchi)</span>
              </div>
              <div className="grid grid-cols-3 gap-1">
                <span className="text-[#546E7A]">Discrepancy Note:</span>
                <span className="col-span-2 text-[#5D4037] leading-relaxed">
                  "Certificate date is 14-Aug-2024. For AY 2026-27, MoTA Rule 4.2 strictly stipulates that income certificates must be issued on or after 01-April-2025. Please upload a fresh current financial year certificate."
                </span>
              </div>
            </div>
          </div>

          {/* Statutory Requirement Ledger (6 cols) */}
          <div className="lg:col-span-6 p-6 bg-[#E8F5E9]/30 space-y-4">
            <div className="flex items-center justify-between border-b border-[#A5D6A7] pb-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-[#198754]" />
                <span className="font-bold font-serif text-sm text-[#1B5E20]">
                  2. Mandatory Statutory Rule 4.2 Standard
                </span>
              </div>
              <span className="bg-[#198754] text-white text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                Required Spec
              </span>
            </div>

            <div className="space-y-3 text-xs text-[#263238]">
              <div className="grid grid-cols-3 gap-1">
                <span className="text-[#546E7A]">Valid Validity Window:</span>
                <span className="col-span-2 text-[#198754] font-bold">Issued on or after 01-April-2025</span>
              </div>
              <div className="grid grid-cols-3 gap-1">
                <span className="text-[#546E7A]">Authorized Issuer:</span>
                <span className="col-span-2 text-[#150202]">Tehsildar / Circle Officer / SDO / DC (Revenue Dept)</span>
              </div>
              <div className="grid grid-cols-3 gap-1">
                <span className="text-[#546E7A]">Income Ceiling:</span>
                <span className="col-span-2 text-[#150202] font-semibold">₹6,00,000 per annum (Composite family total)</span>
              </div>
              <div className="grid grid-cols-3 gap-1">
                <span className="text-[#546E7A]">Accepted Formats:</span>
                <span className="col-span-2 text-[#150202]">Digital PDF or scan with verifiable QR code (Max 2MB)</span>
              </div>
            </div>
          </div>

        </div>

        {/* 4. Evidentiary Ingestion & Scrutiny Scanner Desk */}
        <div className="bg-white border border-[#CFD8DC] rounded-lg shadow-sm p-6 sm:p-8 space-y-6">
          <div className="border-b border-[#ECEFF1] pb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-bold text-[#1D0A69] font-serif">
                Upload Replacement Income Certificate
              </h2>
              <p className="text-xs text-[#546E7A] mt-0.5">
                The uploaded document will instantly pass through ClamAV Antivirus, SHA-256 integrity hashing, and PaddleOCR text extraction.
              </p>
            </div>
            <span className="text-[11px] font-mono text-[#546E7A]">SHA-256 Audit Trail Enabled</span>
          </div>

          {/* UPLOAD IDLE STATE */}
          {uploadStage === 'IDLE' && (
            <div className="space-y-5">
              <div className="border-2 border-dashed border-[#CFD8DC] hover:border-[#1D0A69] rounded-lg p-8 text-center space-y-3 bg-[#F8F9FA] transition-colors">
                <UploadCloud className="w-10 h-10 text-[#0F4C81] mx-auto" />
                <div>
                  <div className="font-bold text-sm text-[#1D0A69]">
                    Select or Drag & Drop Replacement Certificate
                  </div>
                  <p className="text-xs text-[#546E7A] mt-1">
                    Accepted: PDF, JPEG, PNG (Strictly under 2MB)
                  </p>
                </div>

                <input
                  type="file"
                  id="deficiency-file-input"
                  onChange={handleFileChange}
                  accept=".pdf,.jpg,.jpeg,.png"
                  className="hidden"
                />
                
                <div className="pt-2">
                  <label
                    htmlFor="deficiency-file-input"
                    className="gov-btn gov-btn-secondary text-xs font-bold inline-flex items-center gap-2 cursor-pointer px-5 py-2"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Choose File from Device</span>
                  </label>
                </div>

                {fileSelected && (
                  <div className="p-3 bg-[#E8F5E9] border border-[#A5D6A7] rounded text-xs text-[#198754] font-semibold flex items-center justify-center gap-2 max-w-md mx-auto mt-3">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                    <span>Selected: {fileSelected.name} ({(fileSelected.size / 1024).toFixed(1)} KB)</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={onBack}
                  className="gov-btn gov-btn-secondary text-xs font-bold"
                >
                  Cancel & Return to Dashboard
                </button>
                <button
                  type="button"
                  disabled={!fileSelected}
                  onClick={handleStartProcessing}
                  className={`text-xs font-bold px-6 py-2.5 rounded transition-all flex items-center gap-2 ${
                    fileSelected 
                      ? 'bg-[#1D0A69] hover:bg-[#15074D] text-white shadow-sm' 
                      : 'bg-[#CFD8DC] text-[#546E7A] cursor-not-allowed'
                  }`}
                >
                  <span>Ingest & Run Pipeline Verification</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* SCANNING & PROCESSING PIPELINE */}
          {(uploadStage === 'UPLOADING' || uploadStage === 'SCANNING' || uploadStage === 'OCR_PROCESSING') && (
            <div className="py-10 space-y-6 text-center max-w-md mx-auto">
              <div className="w-14 h-14 rounded-full bg-[#1D0A69]/10 text-[#1D0A69] flex items-center justify-center mx-auto animate-spin">
                <RefreshCw className="w-7 h-7" />
              </div>

              <div className="space-y-2">
                <div className="text-base font-bold text-[#1D0A69] font-serif">
                  {uploadStage === 'UPLOADING' && 'Ingesting file into encrypted memory buffer...'}
                  {uploadStage === 'SCANNING' && 'ClamAV 1.5.4 Antivirus Sandbox Scanning...'}
                  {uploadStage === 'OCR_PROCESSING' && 'PaddleOCR v4 Sovereign Entity Extraction...'}
                </div>
                <p className="text-xs text-[#546E7A]">
                  Computing SHA-256 cryptographic digest and verifying revenue seal...
                </p>
              </div>

              <div className="space-y-2 text-left bg-[#F4F6F8] p-4 rounded border border-[#CFD8DC] text-xs">
                <div className="flex items-center justify-between">
                  <span>SHA-256 Digest:</span>
                  <span className="font-mono text-[#1D0A69] font-bold">e7a8...42f9</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Antivirus Sandbox:</span>
                  <span className="text-[#198754] font-bold">Passed (Zero Threats)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Issuance Date Check:</span>
                  <span className="text-[#198754] font-bold">12-Jul-2025 (Rule 4.2 Satisfied)</span>
                </div>
              </div>
            </div>
          )}

          {/* COMPLETED SUCCESS STATE */}
          {uploadStage === 'COMPLETED' && (
            <div className="space-y-6">
              <div className="p-4 bg-[#E8F5E9] border border-[#A5D6A7] rounded-lg text-xs space-y-3">
                <div className="flex items-center gap-2 font-bold text-sm text-[#1B5E20]">
                  <CheckCircle2 className="w-5 h-5 text-[#198754]" />
                  <span>Deficiency Resolved — Document Successfully Validated</span>
                </div>
                <p className="text-[#2E7D32] leading-relaxed">
                  The replacement income certificate has passed security checks and satisfied statutory Rule 4.2. Extracted entities match the applicant record.
                </p>
                <div className="bg-white p-3 rounded border border-[#A5D6A7] grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className="text-[#546E7A] block text-[11px]">Extracted Income:</span>
                    <strong className="text-[#150202]">{extractedIncome}</strong>
                  </div>
                  <div>
                    <span className="text-[#546E7A] block text-[11px]">Issuing Authority:</span>
                    <strong className="text-[#150202]">Circle Officer, Ranchi</strong>
                  </div>
                  <div>
                    <span className="text-[#546E7A] block text-[11px]">Rule 4.2 Status:</span>
                    <strong className="text-[#198754]">VALID & COMPLIANT</strong>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={onResolved}
                  className="bg-[#198754] hover:bg-[#157347] text-white font-bold text-xs px-8 py-3 rounded shadow-md flex items-center gap-2 transition-all"
                >
                  <Check className="w-4 h-4" />
                  <span>Transmit Rectification to Scrutiny Officer</span>
                </button>
              </div>
            </div>
          )}

        </div>

      </main>
    </div>
  );
};
