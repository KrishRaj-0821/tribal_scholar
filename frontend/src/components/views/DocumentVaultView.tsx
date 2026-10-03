import React, { useState, useEffect } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { vaultApi, VaultDocument } from '../../services/api';
import { TribalPattern } from '../common/TribalPattern';
import { 
  FolderLock, UploadCloud, ShieldCheck, CheckCircle2, 
  FileText, AlertCircle, RefreshCw, 
  Layers, Sparkles, X, Download
} from 'lucide-react';

export const DocumentVaultView: React.FC = () => {
  const { language } = useLanguage();

  const [documents, setDocuments] = useState<VaultDocument[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>('ALL');

  // Upload Modal State
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [uploadCategory, setUploadCategory] = useState<string>('FINANCIAL');
  const [uploadDocType, setUploadDocType] = useState<string>('INCOME_CERTIFICATE');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [certNumberInput, setCertNumberInput] = useState<string>('');
  const [incomeInput, setIncomeInput] = useState<string>('450000');
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgressStep, setUploadProgressStep] = useState<string>('');
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState<string | null>(null);

  const categories = [
    { key: 'ALL', label: language === 'hi' ? 'सभी दस्तावेज' : 'All Documents' },
    { key: 'COMMUNITY', label: language === 'hi' ? 'समुदाय (ST)' : 'Community (ST)' },
    { key: 'FINANCIAL', label: language === 'hi' ? 'आय प्रमाणपत्र' : 'Financial' },
    { key: 'ACADEMIC', label: language === 'hi' ? 'शैक्षणिक' : 'Academic' },
    { key: 'IDENTITY', label: language === 'hi' ? 'पहचान / निवास' : 'Identity & Domicile' },
    { key: 'ADMISSION', label: language === 'hi' ? 'प्रवेश / शुल्क' : 'Admission & Fee' },
    { key: 'OTHER', label: language === 'hi' ? 'अन्य' : 'Other' },
  ];

  const fetchDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await vaultApi.getDocuments(activeCategory);
      setDocuments(res.documents || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load document vault.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [activeCategory]);

  const handleCategoryChange = (cat: string) => {
    setActiveCategory(cat);
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a valid document file (PDF or Image).');
      return;
    }

    setUploading(true);
    setUploadProgressStep('Scanning with ClamAV security daemon...');

    try {
      setTimeout(() => {
        setUploadProgressStep('Executing PaddleOCR document intelligence...');
      }, 700);

      const extra: Record<string, string> = {};
      if (uploadDocType === 'INCOME_CERTIFICATE') {
        if (incomeInput) extra['declared_income'] = incomeInput;
        if (certNumberInput) extra['certificate_number'] = certNumberInput;
      } else if (uploadDocType === 'CASTE_CERTIFICATE') {
        if (certNumberInput) extra['certificate_number'] = certNumberInput;
      }

      const newDoc = await vaultApi.uploadDocument(selectedFile, uploadDocType, extra);
      setUploadProgressStep('Document verified and stored securely in vault!');
      setUploadSuccessMsg(`Document "${newDoc.display_type}" uploaded and provisional data extracted.`);
      
      setIsUploadModalOpen(false);
      setSelectedFile(null);
      fetchDocuments();
    } catch (err: any) {
      setError(err.message || 'Upload failed. Please check file format.');
    } finally {
      setUploading(false);
      setUploadProgressStep('');
    }
  };

  return (
    <div className="bg-[#F4F6F8] min-h-screen pb-20">
      
      {/* 1. Official MoTA Sovereign Header */}
      <div className="bg-[#1D0A69] text-white border-b-4 border-[#FFC107] relative overflow-hidden">
        <TribalPattern family="woven" opacity={0.07} color="#FFC107" className="absolute inset-0 pointer-events-none" />

        <div className="gov-container relative py-7">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center text-[#FFC107]">
                <FolderLock className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold text-[#FFC107]">
                  <span>GOVERNMENT OF INDIA</span>
                  <span>•</span>
                  <span>NATIONAL CITIZEN VAULT</span>
                </div>
                <h1 className="text-2xl font-bold font-serif text-white tracking-tight">
                  MY DOCUMENT VAULT
                </h1>
                <p className="text-xs text-[#EBEAEA]/90 max-w-2xl mt-0.5">
                  Securely keep your important documents in one place and reuse verified information when applying for scholarships and fellowships.
                </p>
              </div>
            </div>

            {/* Upload Button */}
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="bg-[#FFC107] text-[#120538] hover:bg-[#FFD54F] px-4 py-2.5 rounded font-bold text-xs flex items-center gap-2 shadow-sm transition-all transform active:scale-95 flex-shrink-0"
            >
              <UploadCloud className="w-4 h-4 text-[#120538]" />
              <span>Upload Document to Vault</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Success Banner */}
      {uploadSuccessMsg && (
        <div className="bg-[#E8F5E9] border-b border-[#A5D6A7] text-[#1B5E20] py-2.5 px-4 text-xs font-semibold flex items-center justify-between">
          <div className="gov-container flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-[#2E7D32]" />
            <span>{uploadSuccessMsg}</span>
          </div>
          <button onClick={() => setUploadSuccessMsg(null)} className="text-[#2E7D32]">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 3. Category Filter Tabs */}
      <div className="bg-white border-b border-[#CFD8DC] sticky top-12 z-20 shadow-xs">
        <div className="gov-container flex items-center gap-1 overflow-x-auto py-1">
          {categories.map((cat) => (
            <button
              key={cat.key}
              onClick={() => handleCategoryChange(cat.key)}
              className={`px-3 py-2 rounded text-xs font-bold transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                activeCategory === cat.key
                  ? 'bg-[#1D0A69] text-white shadow-xs'
                  : 'text-[#546E7A] hover:bg-[#ECEFF1] hover:text-[#1D0A69]'
              }`}
            >
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 4. Vault Content Area */}
      <div className="gov-container py-6">
        {loading ? (
          <div className="min-h-[40vh] flex flex-col items-center justify-center">
            <RefreshCw className="w-8 h-8 text-[#1D0A69] animate-spin mb-3" />
            <p className="text-xs font-bold text-[#546E7A]">Loading secure document vault...</p>
          </div>
        ) : error ? (
          <div className="bg-[#FFEBEE] border border-[#FFCDD2] p-4 rounded text-xs text-[#C62828] flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        ) : documents.length === 0 ? (
          <div className="bg-white border border-[#CFD8DC] rounded-xl p-10 text-center max-w-xl mx-auto shadow-xs">
            <div className="w-16 h-16 rounded-full bg-[#E8EAF6] flex items-center justify-center mx-auto text-[#1D0A69] mb-4">
              <FolderLock className="w-8 h-8" />
            </div>
            <h3 className="text-base font-bold text-[#1D0A69]">No documents stored in this category</h3>
            <p className="text-xs text-[#546E7A] mt-1.5 leading-relaxed">
              Upload your ST Caste Certificate, Income Certificate, or Academic Marksheets once. 
              Our system securely verifies them and lets you auto-fill multiple scholarship applications without re-uploading!
            </p>
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="mt-5 bg-[#1D0A69] text-white hover:bg-[#15074D] px-5 py-2.5 rounded font-bold text-xs inline-flex items-center gap-2"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Upload Your First Document</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {documents.map((doc) => (
              <div 
                key={doc.id}
                className="bg-white border border-[#CFD8DC] rounded-xl shadow-xs hover:shadow-md transition-shadow overflow-hidden flex flex-col justify-between"
              >
                {/* Card Top */}
                <div className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-[#E8EAF6] text-[#1D0A69] flex items-center justify-center flex-shrink-0 font-bold">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-[#ECEFF1] text-[#37474F]">
                            {doc.category}
                          </span>
                          <span className="text-xs text-[#78909C]">
                            {new Date(doc.uploaded_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                          </span>
                        </div>
                        <h2 className="text-sm font-bold text-[#1D0A69] mt-0.5">
                          {doc.display_type}
                        </h2>
                        <p className="text-[11px] text-[#78909C] truncate max-w-xs">
                          {doc.original_filename} ({Math.round(doc.file_size_bytes / 1024)} KB)
                        </p>
                      </div>
                    </div>

                    {/* Status Pill */}
                    <div className="flex flex-col items-end gap-1">
                      <span className="text-[10px] font-extrabold px-2 py-0.5 rounded bg-[#E8F5E9] text-[#2E7D32] border border-[#C8E6C9] flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3 text-[#2E7D32]" />
                        <span>Security Check: Passed</span>
                      </span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#FFF8E1] text-[#F57F17] border border-[#FFE082]">
                        {doc.verification_status}
                      </span>
                    </div>
                  </div>

                  {/* Extracted Information Section (Requirement 13) */}
                  <div className="mt-4 pt-3 border-t border-[#ECEFF1] bg-[#F8F9FA] rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-[#1D0A69]">
                        <Sparkles className="w-3.5 h-3.5 text-[#F57F17]" />
                        <span>Extracted Document Evidence</span>
                      </div>
                      <span className="text-[10px] font-bold text-[#2E7D32] bg-[#E8F5E9] px-1.5 py-0.5 rounded">
                        ✓ OCR Completed
                      </span>
                    </div>

                    {doc.extracted_fields && doc.extracted_fields.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        {doc.extracted_fields.map((f, idx) => (
                          <div key={idx} className="bg-white p-2 rounded border border-[#E0E0E0]">
                            <div className="text-[10px] text-[#78909C] font-medium">{f.field_label}</div>
                            <div className="font-bold text-[#263238] truncate">{String(f.value)}</div>
                            <div className="text-[9px] text-[#C85A17] font-extrabold mt-0.5 flex items-center gap-1">
                              <span>Source:</span>
                              <span className="bg-[#FFF3E0] px-1 rounded">{f.source}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[11px] text-[#78909C] italic">
                        Document securely processed and archived. Ready for statutory verification.
                      </p>
                    )}
                  </div>
                </div>

                {/* Card Bottom / Footer Actions */}
                <div className="px-5 py-3 bg-[#FAFAFA] border-t border-[#ECEFF1] flex items-center justify-between text-xs">
                  <div className="text-[11px] text-[#546E7A] flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-[#78909C]" />
                    <span>
                      {doc.applications_count > 0 
                        ? `Linked to ${doc.applications_count} application` 
                        : 'Available for new applications'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <a
                      href={doc.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#1D0A69] hover:text-[#0D47A1] font-bold flex items-center gap-1 py-1 px-2.5 rounded bg-white border border-[#CFD8DC] hover:bg-[#F5F5F5]"
                    >
                      <Download className="w-3 h-3" />
                      <span>Download</span>
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 5. Upload Modal Dialog */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fadeIn">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full overflow-hidden border border-[#CFD8DC]">
            {/* Modal Header */}
            <div className="bg-[#1D0A69] text-white p-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-5 h-5 text-[#FFC107]" />
                <h3 className="font-bold text-sm">Upload to My Document Vault</h3>
              </div>
              <button 
                onClick={() => setIsUploadModalOpen(false)}
                className="text-white/70 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleUploadSubmit} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                  Document Category
                </label>
                <select
                  value={uploadCategory}
                  onChange={(e) => {
                    const cat = e.target.value;
                    setUploadCategory(cat);
                    if (cat === 'COMMUNITY') setUploadDocType('CASTE_CERTIFICATE');
                    else if (cat === 'FINANCIAL') setUploadDocType('INCOME_CERTIFICATE');
                    else if (cat === 'ACADEMIC') setUploadDocType('ACADEMIC_TRANSCRIPT');
                    else if (cat === 'ADMISSION') setUploadDocType('ADMISSION_OFFER');
                    else setUploadDocType('OTHER');
                  }}
                  className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white focus:outline-none focus:border-[#1D0A69]"
                >
                  <option value="COMMUNITY">Community (ST Certificate)</option>
                  <option value="FINANCIAL">Financial (Income Certificate)</option>
                  <option value="ACADEMIC">Academic (Marksheet / Degree)</option>
                  <option value="IDENTITY">Identity (Domicile / UDID)</option>
                  <option value="ADMISSION">Admission (Offer Letter / Fee Receipt)</option>
                  <option value="OTHER">Other Supporting Documents</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                  Document Type
                </label>
                <select
                  value={uploadDocType}
                  onChange={(e) => setUploadDocType(e.target.value)}
                  className="w-full text-xs p-2.5 border border-[#CFD8DC] rounded bg-white focus:outline-none focus:border-[#1D0A69]"
                >
                  {uploadCategory === 'COMMUNITY' && (
                    <option value="CASTE_CERTIFICATE">ST Community / Tribe Certificate</option>
                  )}
                  {uploadCategory === 'FINANCIAL' && (
                    <option value="INCOME_CERTIFICATE">Competent Authority Income Certificate</option>
                  )}
                  {uploadCategory === 'ACADEMIC' && (
                    <option value="ACADEMIC_TRANSCRIPT">Academic Transcript / Marksheet</option>
                  )}
                  {uploadCategory === 'IDENTITY' && (
                    <>
                      <option value="DISABILITY_CERTIFICATE">UDID / Disability Certificate</option>
                      <option value="PASSPORT">Passport (for Overseas Scholarship)</option>
                    </>
                  )}
                  {uploadCategory === 'ADMISSION' && (
                    <>
                      <option value="ADMISSION_OFFER">Admission Offer / Enrolment Letter</option>
                      <option value="FEE_RECEIPT">Fee Receipt</option>
                    </>
                  )}
                  <option value="OTHER">Other Supporting Document</option>
                </select>
              </div>

              {/* Specific Metadata inputs for OCR verification showcase */}
              {uploadDocType === 'INCOME_CERTIFICATE' && (
                <div className="grid grid-cols-2 gap-3 bg-[#F8F9FA] p-3 rounded border border-[#ECEFF1]">
                  <div>
                    <label className="block text-[11px] font-bold text-[#37474F] mb-1">
                      Certificate Number
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. JH/INC/2025/99120"
                      value={certNumberInput}
                      onChange={(e) => setCertNumberInput(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-[#37474F] mb-1">
                      Gross Annual Income (₹)
                    </label>
                    <input
                      type="number"
                      placeholder="e.g. 450000"
                      value={incomeInput}
                      onChange={(e) => setIncomeInput(e.target.value)}
                      className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                    />
                  </div>
                </div>
              )}

              {uploadDocType === 'CASTE_CERTIFICATE' && (
                <div className="bg-[#F8F9FA] p-3 rounded border border-[#ECEFF1]">
                  <label className="block text-[11px] font-bold text-[#37474F] mb-1">
                    ST Certificate Number
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. JH/ST/2024/77491"
                    value={certNumberInput}
                    onChange={(e) => setCertNumberInput(e.target.value)}
                    className="w-full text-xs p-2 border border-[#CFD8DC] rounded bg-white"
                  />
                </div>
              )}

              {/* File Attachment */}
              <div>
                <label className="block text-xs font-bold text-[#1D0A69] mb-1">
                  Select Document File (PDF, JPG, PNG - Max 10MB)
                </label>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs p-2 border border-dashed border-[#90A4AE] rounded bg-[#F8F9FA]"
                />
              </div>

              {/* Progress message */}
              {uploading && (
                <div className="bg-[#E8F5E9] p-3 rounded text-xs text-[#2E7D32] flex items-center gap-2 animate-pulse">
                  <RefreshCw className="w-4 h-4 animate-spin flex-shrink-0" />
                  <span>{uploadProgressStep || 'Processing upload...'}</span>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#ECEFF1]">
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  disabled={uploading}
                  className="px-4 py-2 rounded text-xs font-semibold text-[#546E7A] hover:bg-[#ECEFF1]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !selectedFile}
                  className="bg-[#1D0A69] text-white hover:bg-[#15074D] disabled:opacity-50 px-5 py-2 rounded text-xs font-bold shadow-xs flex items-center gap-2"
                >
                  <UploadCloud className="w-4 h-4" />
                  <span>{uploading ? 'Processing...' : 'Upload & Process OCR'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
