import React, { useState } from 'react';
import { useDemo } from '../../context/DemoContext';
import { useLanguage } from '../../context/LanguageContext';
import { 
  UploadCloud, FileText, 
  AlertTriangle, ArrowRight, ZoomIn, ZoomOut,
  Info, Lock
} from 'lucide-react';

export const DocumentUploadOcrView: React.FC = () => {
  const { language } = useLanguage();
  const { 
    applicant, uploadProgress, simulateUploadAndOcr, 
    ocrData, setCurrentStep 
  } = useDemo();

  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [selectedField, setSelectedField] = useState<string>('annual_family_income');

  const boundingBoxes = [
    { id: 'box-title', text: 'आय प्रमाण पत्र (INCOME CERTIFICATE)', x: 18, y: 16, width: 64, height: 6, field: null },
    { id: 'box-auth', text: 'कार्यालय तहसीलदार, मंडला (मध्य प्रदेश)', x: 15, y: 26, width: 70, height: 5, field: 'district' },
    { id: 'box-cert', text: 'प्रमाण पत्र संख्या: TEST-2026-001', x: 15, y: 36, width: 70, height: 5, field: 'certificate_number' },
    { id: 'box-name', text: 'नाम: Demo ST Applicant', x: 15, y: 46, width: 70, height: 5, field: null },
    { id: 'box-income', text: 'वार्षिक पारिवारिक आय: 450000 रुपये', x: 15, y: 56, width: 70, height: 6, field: 'annual_family_income' },
    { id: 'box-date', text: 'दिनांक: 15/01/2026', x: 15, y: 68, width: 35, height: 5, field: null },
    { id: 'box-seal', text: '[राजकीय मुहर / SDM Mandla]', x: 55, y: 76, width: 35, height: 10, field: null },
  ];

  return (
    <div className="gov-container py-6 space-y-6">
      {/* 1. Header Banner */}
      <div className="gov-card flex flex-wrap items-center justify-between gap-4 border-l-4 border-l-[#1D0A69]">
        <div>
          <div className="flex items-center gap-2 text-xs text-[#546E7A] mb-1">
            <span className="font-mono text-[#1D0A69] font-bold">{applicant.applicationId}</span>
            <span>•</span>
            <span>Candidate: <strong>{applicant.name} ({applicant.category})</strong></span>
            <span>•</span>
            <span className="text-[#C85A17] font-semibold">{applicant.district}, {applicant.state}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold font-serif text-[#1D0A69]">
            {language === 'hi' 
              ? 'दस्तावेज़ अंतर्ग्रहण, ClamAV सुरक्षा जांच एवं बहुभाषी OCR' 
              : 'Evidentiary Document Ingestion, ClamAV Security Gate & Multi-Lingual OCR'}
          </h1>
          <p className="text-xs text-[#546E7A] mt-0.5">
            Synthetic ST Dossier • Family Income Certificate Review for AY 2026-27
          </p>
        </div>

        <div className="flex items-center gap-2">
          {uploadProgress === 'ocr_complete' && (
            <button
              onClick={() => setCurrentStep('officer_queue')}
              className="bg-[#1D0A69] hover:bg-[#15074D] text-[#FFC107] font-bold px-4 py-2 rounded text-xs flex items-center gap-1.5 shadow-sm border border-[#C85A17]"
            >
              <span>Go to Officer Review Queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* 2. Multi-Stage Pipeline Progress Strip (Non-Fake Polled Visualizer) */}
      <div className="gov-card bg-[#FAFAFA] border border-[#CFD8DC] p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <span className="text-xs font-bold text-[#1D0A69] uppercase tracking-wider flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-[#C85A17]" />
            Continuous Security & Extraction Pipeline
          </span>
          <span className="text-xs font-mono text-[#546E7A]">
            File: <code>income_cert_mandla_2026.png</code> (248 KB)
          </span>
        </div>

        {/* Pipeline Nodes */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
          {/* Stage 1 */}
          <div className={`p-2.5 rounded border text-center transition-all ${
            uploadProgress !== 'idle' 
              ? 'bg-[#E8F5E9] border-[#A5D6A7] text-[#1B5E20] font-bold' 
              : 'bg-white border-[#E0E0E0] text-gray-500'
          }`}>
            <div className="text-[10px] uppercase text-gray-500 font-medium">Stage 1</div>
            <div className="flex items-center justify-center gap-1 mt-0.5">
              {uploadProgress !== 'idle' && <span>✓</span>}
              <span>UPLOADING</span>
            </div>
          </div>

          {/* Stage 2 */}
          <div className={`p-2.5 rounded border text-center transition-all ${
            uploadProgress === 'security_check' || uploadProgress === 'clamav_scan' || uploadProgress === 'safe' || uploadProgress === 'ocr_running' || uploadProgress === 'ocr_complete'
              ? 'bg-[#E8F5E9] border-[#A5D6A7] text-[#1B5E20] font-bold' 
              : uploadProgress === 'uploading' 
              ? 'bg-[#FFF8E1] border-[#FFE082] text-[#E65100] animate-pulse font-bold'
              : 'bg-white border-[#E0E0E0] text-gray-500'
          }`}>
            <div className="text-[10px] uppercase text-gray-500 font-medium">Stage 2</div>
            <div className="flex items-center justify-center gap-1 mt-0.5">
              {uploadProgress !== 'idle' && uploadProgress !== 'uploading' && <span>✓</span>}
              <span>SECURITY CHECK</span>
            </div>
          </div>

          {/* Stage 3 */}
          <div className={`p-2.5 rounded border text-center transition-all ${
            uploadProgress === 'clamav_scan' 
              ? 'bg-[#FFF8E1] border-[#FFE082] text-[#E65100] animate-pulse font-bold'
              : uploadProgress === 'safe' || uploadProgress === 'ocr_running' || uploadProgress === 'ocr_complete'
              ? 'bg-[#E8F5E9] border-[#A5D6A7] text-[#1B5E20] font-bold'
              : 'bg-white border-[#E0E0E0] text-gray-500'
          }`}>
            <div className="text-[10px] uppercase text-gray-500 font-medium">Stage 3</div>
            <div className="flex items-center justify-center gap-1 mt-0.5">
              {(uploadProgress === 'safe' || uploadProgress === 'ocr_running' || uploadProgress === 'ocr_complete') && <span>✓</span>}
              <span>CLAMAV SCAN</span>
            </div>
          </div>

          {/* Stage 4 */}
          <div className={`p-2.5 rounded border text-center transition-all ${
            uploadProgress === 'safe' || uploadProgress === 'ocr_running' || uploadProgress === 'ocr_complete'
              ? 'bg-[#E8F5E9] border-[#A5D6A7] text-[#1B5E20] font-bold'
              : 'bg-white border-[#E0E0E0] text-gray-500'
          }`}>
            <div className="text-[10px] uppercase text-gray-500 font-medium">Stage 4</div>
            <div className="flex items-center justify-center gap-1 mt-0.5">
              {(uploadProgress === 'safe' || uploadProgress === 'ocr_running' || uploadProgress === 'ocr_complete') && <span>✓</span>}
              <span>SAFE GATE</span>
            </div>
          </div>

          {/* Stage 5 */}
          <div className={`p-2.5 rounded border text-center transition-all ${
            uploadProgress === 'ocr_running' 
              ? 'bg-[#E1F5FE] border-[#81D4FA] text-[#0277BD] animate-pulse font-bold'
              : uploadProgress === 'ocr_complete'
              ? 'bg-[#E8F5E9] border-[#A5D6A7] text-[#1B5E20] font-bold'
              : 'bg-white border-[#E0E0E0] text-gray-500'
          }`}>
            <div className="text-[10px] uppercase text-gray-500 font-medium">Stage 5</div>
            <div className="flex items-center justify-center gap-1 mt-0.5">
              {uploadProgress === 'ocr_complete' && <span>✓</span>}
              <span>PADDLE OCR</span>
            </div>
          </div>

          {/* Stage 6 */}
          <div className={`p-2.5 rounded border text-center transition-all ${
            uploadProgress === 'ocr_complete'
              ? 'bg-[#1D0A69] border-[#C85A17] text-[#FFC107] font-bold shadow-xs'
              : 'bg-white border-[#E0E0E0] text-gray-500'
          }`}>
            <div className="text-[10px] uppercase text-gray-400 font-medium">Stage 6</div>
            <div className="flex items-center justify-center gap-1 mt-0.5">
              {uploadProgress === 'ocr_complete' && <span>✓</span>}
              <span>OCR COMPLETE</span>
            </div>
          </div>
        </div>

        {uploadProgress === 'idle' && (
          <div className="mt-4 text-center">
            <button
              onClick={simulateUploadAndOcr}
              className="bg-[#1D0A69] hover:bg-[#15074D] text-white px-6 py-2.5 rounded text-xs font-bold shadow-md inline-flex items-center gap-2"
            >
              <UploadCloud className="w-4 h-4 text-[#FFC107]" />
              <span>Simulate Document Ingestion & Asynchronous OCR</span>
            </button>
          </div>
        )}
      </div>

      {/* 3. Main Split View: Scanned Certificate Canvas vs Provisional OCR & Conflict */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* LEFT COLUMN: Document Canvas with Interactive SVG Bounding Boxes */}
        <div className="gov-card lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between border-b border-[#CFD8DC] pb-3">
            <div>
              <h3 className="font-bold text-sm text-[#1D0A69] flex items-center gap-2 font-serif">
                <FileText className="w-4 h-4 text-[#C85A17]" />
                <span>Document Scrutiny Canvas</span>
              </h3>
              <span className="text-[11px] text-[#546E7A]">
                Revenue Authority Certificate • Mandla District, Madhya Pradesh
              </span>
            </div>

            {/* Zoom Controls */}
            <div className="flex items-center gap-1 text-xs">
              <button
                onClick={() => setZoomLevel(prev => Math.max(80, prev - 10))}
                className="px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
              >
                <ZoomOut className="w-3 h-3 text-gray-700" />
              </button>
              <span className="font-mono text-xs px-1.5">{zoomLevel}%</span>
              <button
                onClick={() => setZoomLevel(prev => Math.min(140, prev + 10))}
                className="px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
              >
                <ZoomIn className="w-3 h-3 text-gray-700" />
              </button>
            </div>
          </div>

          {/* Interactive Document Simulation */}
          <div className="bg-[#263238] p-4 rounded-md overflow-auto min-h-[460px]">
            <div 
              style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top left' }}
              className="bg-[#FCFCFC] text-[#1E293B] p-6 rounded shadow-lg relative min-h-[420px] font-sans transition-transform"
            >
              {/* Certificate Header */}
              <div className="text-center border-b-2 border-gray-400 pb-3 mb-4">
                <div className="font-extrabold text-sm text-gray-900 tracking-wide">
                  भारत सरकार / GOVERNMENT OF INDIA
                </div>
                <div className="font-bold text-base text-[#1D0A69]">
                  आय प्रमाण पत्र (INCOME CERTIFICATE)
                </div>
                <div className="text-xs text-gray-600">
                  कार्यालय तहसीलदार, मंडला, मध्य प्रदेश / Office of Tehsildar, Mandla (M.P.)
                </div>
              </div>

              {/* Certificate Body Lines */}
              <div className="space-y-3 text-xs leading-relaxed">
                <div>
                  प्रमाण पत्र संख्या / Certificate No: <strong>{ocrData.certificateNumber}</strong>
                </div>
                <div>
                  आवेदक का नाम / Applicant Name: <strong>{applicant.name}</strong>
                </div>
                <div>
                  पिता का नाम / Father's Name: <strong>श्री रामेश्वर मुंडा (Shri Rameshwar Munda)</strong>
                </div>
                <div>
                  समुदाय / Category: <strong>अनुसूचित जनजाति (ST - Scheduled Tribe)</strong>
                </div>
                <div className={`p-2 rounded inline-block transition-colors ${
                  selectedField === 'annual_family_income' 
                    ? 'bg-amber-100 border-2 border-amber-500 font-bold' 
                    : 'bg-blue-50 border border-blue-200'
                }`}>
                  वार्षिक पारिवारिक आय / Annual Family Income: <strong>₹4,50,000/- (रुपये चार लाख पचास हजार मात्र)</strong>
                </div>
                <div>
                  जारी करने का दिनांक / Date of Issue: <strong>15/01/2026</strong>
                </div>
              </div>

              {/* Digital Seal / Signature */}
              <div className="mt-8 flex items-end justify-between text-xs pt-4 border-t border-gray-300">
                <div className="border border-gray-300 p-2 rounded text-center bg-gray-50 text-[10px]">
                  [GOV DIGITAL SEAL]<br/>
                  <span className="font-mono text-emerald-700 font-bold">DIGITALLY SIGNED</span>
                </div>
                <div className="text-right">
                  <div className="font-bold">तहसीलदार / Tehsildar</div>
                  <div className="text-gray-600">मंडला, मध्य प्रदेश (Mandla, MP)</div>
                </div>
              </div>

              {/* SVG OCR Bounding Boxes */}
              {uploadProgress === 'ocr_complete' && (
                <svg className="absolute inset-0 w-full h-full pointer-events-none">
                  {boundingBoxes.map(box => {
                    const isSelected = box.field === selectedField;
                    return (
                      <rect
                        key={box.id}
                        x={`${box.x}%`}
                        y={`${box.y}%`}
                        width={`${box.width}%`}
                        height={`${box.height}%`}
                        fill={isSelected ? 'rgba(59, 130, 246, 0.2)' : 'transparent'}
                        stroke={isSelected ? '#1D0A69' : 'rgba(200, 90, 23, 0.5)'}
                        strokeWidth={isSelected ? 2 : 1}
                        strokeDasharray={isSelected ? 'none' : '3 2'}
                        rx={2}
                      />
                    );
                  })}
                </svg>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-[#546E7A]">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-[#1D0A69]"></span>
                <span>Active Focused Field</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded border border-[#C85A17] border-dashed"></span>
                <span>PaddleOCR Block (700px Bound)</span>
              </span>
            </div>
            <span className="font-mono">SHA-256 Verified Clean</span>
          </div>
        </div>

        {/* RIGHT COLUMN: Extracted Fields & Real Material Conflict */}
        <div className="gov-card lg:col-span-5 space-y-4">
          <div className="border-b border-[#CFD8DC] pb-3">
            <h3 className="font-bold text-sm text-[#1D0A69] font-serif">
              Provisional Extraction & Provenance Audit
            </h3>
            <p className="text-[11px] text-[#546E7A]">
              PaddleOCR 3.7.0 CPU multi-lingual extraction output.
            </p>
          </div>

          {/* Statutory Principle Note */}
          <div className="p-3 bg-[#FFF8E1] border-l-4 border-l-[#C85A17] border border-[#FFE082] rounded text-xs text-[#5D4037] space-y-1">
            <div className="font-bold text-[#C85A17] flex items-center gap-1">
              <Info className="w-3.5 h-3.5" />
              <span>STATUTORY EVIDENCE GUARANTEE</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              Automatically extracted information is strictly <strong>OCR_PROVISIONAL (Trust Rank 10)</strong> and must be validated by an authorized officer. OCR confidence score never equates to legal truth and cannot silently overwrite applicant declarations.
            </p>
          </div>

          {/* Extracted Fields List */}
          <div className="space-y-3">
            {/* Field 1: Certificate Number */}
            <div className="p-3 rounded border border-gray-200 bg-white space-y-1">
              <div className="flex justify-between items-center text-xs">
                <span className="text-[#546E7A] uppercase text-[10px] font-bold">Certificate Number</span>
                <span className="font-mono text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-bold">
                  OCR Conf: 98%
                </span>
              </div>
              <div className="font-bold text-xs text-[#1D0A69] font-mono">
                {ocrData.certificateNumber}
              </div>
              <div className="text-[10px] text-[#546E7A]">Source: OCR_PROVISIONAL (Rank 10)</div>
            </div>

            {/* Field 2: Annual Family Income (THE CONFLICT FIELD) */}
            <div 
              onClick={() => setSelectedField('annual_family_income')}
              className="p-3.5 rounded border-2 border-[#C85A17] bg-[#FFF5F5] space-y-2 cursor-pointer shadow-xs"
            >
              <div className="flex justify-between items-center text-xs">
                <span className="text-[#C85A17] uppercase text-[11px] font-extrabold flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-[#C85A17]" />
                  <span>Annual Family Income (Discrepancy)</span>
                </span>
                <span className="bg-[#C85A17] text-white text-[10px] font-extrabold px-1.5 py-0.5 rounded">
                  MATERIAL CONFLICT
                </span>
              </div>

              {/* Comparison Box */}
              <div className="grid grid-cols-2 gap-2 bg-white p-2.5 rounded border border-red-200 text-xs">
                <div>
                  <span className="text-[10px] text-[#546E7A] block font-semibold">Applicant Declared:</span>
                  <div className="font-extrabold text-[#150202] text-sm">
                    ₹{applicant.declaredIncome.toLocaleString('en-IN')}
                  </div>
                  <span className="text-[9px] text-[#546E7A] font-mono">Rank 20: APPLICANT_DECLARED</span>
                </div>
                <div>
                  <span className="text-[10px] text-[#546E7A] block font-semibold">OCR Extracted (Prov):</span>
                  <div className="font-extrabold text-[#C85A17] text-sm">
                    ₹{ocrData.income.toLocaleString('en-IN')}
                  </div>
                  <span className="text-[9px] text-amber-800 font-mono">Rank 10: OCR_PROVISIONAL</span>
                </div>
              </div>

              <div className="text-[11px] text-[#C85A17] font-medium">
                Discrepancy of ₹50,000 detected. Statutory policy prohibits automatic rejection or blind overwrite. A human review item has been created in the Officer Verification Queue.
              </div>
            </div>

            {/* Field 3: District & State */}
            <div className="p-3 rounded border border-gray-200 bg-white space-y-1">
              <div className="flex justify-between items-center text-xs">
                <span className="text-[#546E7A] uppercase text-[10px] font-bold">Issuing District & State</span>
                <span className="font-mono text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-bold">
                  OCR Conf: 95%
                </span>
              </div>
              <div className="font-bold text-xs text-[#1D0A69]">
                {ocrData.district}, {ocrData.state}
              </div>
              <div className="text-[10px] text-[#546E7A]">Source: OCR_PROVISIONAL (Rank 10)</div>
            </div>
          </div>

          {/* Action Button: Proceed to Officer Verification */}
          <div className="pt-2">
            <button
              onClick={() => setCurrentStep('officer_queue')}
              className="w-full bg-[#1D0A69] hover:bg-[#15074D] text-[#FFC107] font-bold py-3 px-4 rounded text-xs flex items-center justify-center gap-2 shadow-md border-2 border-[#C85A17] transition-all"
            >
              <span>Open Officer Verification Desk to Resolve Conflict</span>
              <ArrowRight className="w-4 h-4 text-[#FFC107]" />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
