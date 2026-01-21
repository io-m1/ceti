'use client'

import { useState, useRef, useEffect } from 'react'
import { verifyWithCETI, CETIResponse } from '@/lib/ceti'
import toast, { Toaster } from 'react-hot-toast'

export default function CETIConsole() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<CETIResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const resultRef = useRef<HTMLDivElement>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setResult(null)
    const toastId = toast.loading('Submitting to CETI for authorization...')

    try {
      const res = await verifyWithCETI(query, 'MEDIUM')
      setResult(res)
      if (res.authorization === 'GRANTED') {
        toast.success('Authorized', { id: toastId })
      } else {
        toast.error('Refused', { id: toastId })
      }
    } catch (err: any) {
      toast.error(err.message || 'CETI unreachable', { id: toastId })
      setResult({
        authorization: 'DENIED',
        response_content: null,
        refusal_diagnostics: {
          failure_type: 'network_error',
          details: err.message,
          requirements_for_certification: 'Check backend connection',
        },
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [result])

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 via-gray-900 to-black text-gray-100 flex flex-col">
      <Toaster position="top-center" toastOptions={{ duration: 5000 }} />

      <header className="p-6 border-b border-gray-800/50 backdrop-blur-sm">
        <h1 className="text-3xl font-bold text-center tracking-tight">CETI Console</h1>
        <p className="text-center text-sm text-gray-400 mt-2">
          All outputs must be authorized — no raw model responses
        </p>
      </header>

      <main className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="mb-8">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your request for CETI authorization..."
              className="w-full p-5 bg-gray-900/60 border border-gray-700 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 text-white placeholder-gray-500 resize-y min-h-[140px] font-mono text-sm"
              disabled={loading}
            />
            <div className="mt-4 flex justify-end">
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg transition-all"
              >
                {loading ? 'Authorizing...' : 'Submit to CETI'}
              </button>
            </div>
          </form>

          {result && (
            <section
              ref={resultRef}
              className="border border-gray-700/50 rounded-xl overflow-hidden bg-gray-900/40 backdrop-blur-sm shadow-2xl"
            >
              <div className="p-6 border-b border-gray-800/50">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold">Authorization Result</h2>
                  <span
                    className={`px-4 py-1 rounded-full text-sm font-medium ${
                      result.authorization === 'GRANTED'
                        ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                        : 'bg-red-500/20 text-red-400 border border-red-500/30'
                    }`}
                  >
                    {result.authorization}
                  </span>
                </div>
              </div>

              <div className="p-6 space-y-4">
                {result.authorization === 'GRANTED' ? (
                  <>
                    <div className="bg-gray-950/50 p-5 rounded-lg border border-gray-800">
                      <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-gray-200">
                        {result.response_content}
                      </pre>
                    </div>
                    {result.certification_id && (
                      <p className="text-xs text-gray-500">
                        Certification ID: <code className="font-mono">{result.certification_id}</code>
                      </p>
                    )}
                  </>
                ) : (
                  <div className="space-y-4 text-sm">
                    <div className="bg-red-950/30 p-5 rounded-lg border border-red-900/40">
                      <p className="font-medium text-red-300 mb-2">Refusal Triggered</p>
                      <p className="text-red-200/90">{result.refusal_diagnostics?.failure_type}</p>
                      <p className="mt-3 text-gray-300">{result.refusal_diagnostics?.details}</p>
                    </div>

                    <div className="bg-gray-950/50 p-5 rounded-lg border border-gray-800">
                      <p className="font-medium mb-2 text-gray-400">Requirements for future authorization:</p>
                      <p className="text-gray-300 italic">
                        {result.refusal_diagnostics?.requirements_for_certification}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      </main>

      <footer className="p-4 border-t border-gray-800/50 text-center text-xs text-gray-500">
        All interactions gated by CETI — no uncertified model output allowed
      </footer>
    </div>
  )
}
