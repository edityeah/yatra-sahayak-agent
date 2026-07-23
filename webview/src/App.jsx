import { Route, Routes } from "react-router-dom";
import AppShell, { LangProvider } from "./components/AppShell.jsx";
import ChatPage from "./chat/ChatPage.jsx";
import PassPage from "./yatri/PassPage.jsx";
import MapPage from "./yatri/MapPage.jsx";
import LogisticsPage from "./yatri/LogisticsPage.jsx";
import DrillsPage from "./yatri/DrillsPage.jsx";
import AdvisoriesPage from "./yatri/AdvisoriesPage.jsx";
import CallPage from "./voice/CallPage.jsx";

export default function App() {
  return (
    <LangProvider>
      <Routes>
        {/* New Pravasi-Setu-style chat landing — owns its own full-page
            header/composer chrome, so it skips the old AppShell wrapper. */}
        <Route path="/" element={<ChatPage />} />

        {/* Inner yatri + voice pages keep the old AppShell (header + nav)
            until they're re-skinned in a separate task. */}
        <Route path="/yatri/pass" element={<AppShell><PassPage /></AppShell>} />
        <Route path="/yatri/map" element={<AppShell><MapPage /></AppShell>} />
        <Route path="/yatri/logistics" element={<AppShell><LogisticsPage /></AppShell>} />
        <Route path="/yatri/drills" element={<AppShell><DrillsPage /></AppShell>} />
        <Route path="/yatri/advisories" element={<AppShell><AdvisoriesPage /></AppShell>} />
        <Route path="/voice" element={<AppShell><CallPage /></AppShell>} />
      </Routes>
    </LangProvider>
  );
}
