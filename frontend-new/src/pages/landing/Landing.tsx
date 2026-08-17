export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-white flex flex-col">
      <header className="px-8 py-6">
        <h1 className="text-2xl font-bold text-blue-700">NáborováApka</h1>
      </header>

      <main className="flex-1 flex items-center justify-center px-4">
        <div className="text-center max-w-xl">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">Nájdite si prácu v najlepších firmách</h2>
          <p className="text-lg text-gray-500 mb-10">
            Vyberte si firmu a prezrite si voľné pracovné pozície. Náš AI asistent vám pomôže zorientovať sa a odpovedá na vaše otázky.
          </p>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
            <h3 className="font-semibold text-gray-700 mb-4 text-sm uppercase tracking-wide">Naše firmy</h3>
            <p className="text-gray-400 text-sm">Zoznam partnerských firiem bude zverejnený čoskoro.</p>
          </div>
        </div>
      </main>

      <footer className="text-center text-xs text-gray-400 py-6">
        © {new Date().getFullYear()} NáborováApka
      </footer>
    </div>
  )
}
