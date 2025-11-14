// src/components/public/LandingPage.tsx
export default function LandingPage() {
  return (
    <div className="container mx-auto px-4 py-12 text-center">
      <h1 className="text-5xl font-bold text-white mb-6">BullsBears</h1>
      <p className="text-xl text-gray-300 mb-8">AI-Powered Stock Picks. Real-Time. No BS.</p>
      <div className="space-x-4">
        <button className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-3 rounded-lg font-semibold">
          Get Started
        </button>
        <button className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-3 rounded-lg font-semibold">
          Learn More
        </button>
      </div>
    </div>
  );
}