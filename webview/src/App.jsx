import { Route, Routes } from "react-router-dom";
import AppShell, { LangProvider } from "./components/AppShell.jsx";
import ChatPage from "./chat/ChatPage.jsx";
import PassPage from "./yatri/PassPage.jsx";
import MapPage from "./yatri/MapPage.jsx";
import LogisticsPage from "./yatri/LogisticsPage.jsx";
import DrillsPage from "./yatri/DrillsPage.jsx";
import AdvisoriesPage from "./yatri/AdvisoriesPage.jsx";

export default function App() {
  return (
    <LangProvider>
      <AppShell>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/yatri/pass" element={<PassPage />} />
          <Route path="/yatri/map" element={<MapPage />} />
          <Route path="/yatri/logistics" element={<LogisticsPage />} />
          <Route path="/yatri/drills" element={<DrillsPage />} />
          <Route path="/yatri/advisories" element={<AdvisoriesPage />} />
        </Routes>
      </AppShell>
    </LangProvider>
  );
}
