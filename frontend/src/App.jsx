import { useState } from "react";
import Dashboard from "./components/Dashboard.jsx";
import Header from "./components/Header.jsx";
import History from "./components/History.jsx";
import Settings from "./components/Settings.jsx";

export default function App() {
  const [bankroll, setBankroll] = useState(2500);

  return (
    <div className="min-h-screen bg-edge-bg text-white">
      <Header />
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 pb-16 pt-8 sm:px-6">
        <Dashboard bankroll={bankroll} />
        <div className="grid gap-8 lg:grid-cols-[1.4fr_0.6fr]">
          <History />
          <Settings bankroll={bankroll} setBankroll={setBankroll} />
        </div>
      </main>
    </div>
  );
}
