import { useState } from "react";
import BacktestDashboard from "./components/BacktestDashboard.jsx";
import Dashboard from "./components/Dashboard.jsx";
import Header from "./components/Header.jsx";
import History from "./components/History.jsx";
import Settings from "./components/Settings.jsx";

export default function App() {
  const [bankroll, setBankroll] = useState(2500);
  const [activeTab, setActiveTab] = useState("live");

  return (
    <div className="min-h-screen bg-edge-bg text-white">
      <Header />
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 pb-16 pt-8 sm:px-6">
        <div className="flex flex-wrap items-center gap-3">
          {[
            { key: "live", label: "Live" },
            { key: "backtest", label: "Backtest" }
          ].map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] transition ${
                activeTab === tab.key
                  ? "bg-edge-green/20 text-edge-green"
                  : "border border-white/10 text-edge-muted hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "live" ? (
          <>
            <Dashboard bankroll={bankroll} />
            <div className="grid gap-8 lg:grid-cols-[1.4fr_0.6fr]">
              <History />
              <Settings bankroll={bankroll} setBankroll={setBankroll} />
            </div>
          </>
        ) : (
          <BacktestDashboard />
        )}
      </main>
    </div>
  );
}
