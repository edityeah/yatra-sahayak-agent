import { Route, Routes } from "react-router-dom";
import { LangProvider } from "./components/AppShell.jsx";
import ChatPage from "./chat/ChatPage.jsx";
import QuickActivitiesPage from "./quick/QuickActivitiesPage.jsx";
import PassPage from "./yatri/PassPage.jsx";
import WalletPage from "./yatri/WalletPage.jsx";
import LostFoundPage from "./yatri/LostFoundPage.jsx";
import MapPage from "./yatri/MapPage.jsx";
import LogisticsPage from "./yatri/LogisticsPage.jsx";
import DrillsPage from "./yatri/DrillsPage.jsx";
import AdvisoriesPage from "./yatri/AdvisoriesPage.jsx";
import CallPage from "./voice/CallPage.jsx";
import OfficerDashboard from "./officer/OfficerDashboard.jsx";

export default function App() {
  return (
    <LangProvider>
      <Routes>
        {/* New Pravasi-Setu-style chat landing — owns its own full-page
            header/composer chrome. */}
        <Route path="/" element={<ChatPage />} />
        <Route path="/quick-activities" element={<QuickActivitiesPage />} />

        {/* Inner yatri + voice pages now bring their own PageShell (same
            blue-avatar header, back arrow, MenuDrawer) so every route
            feels like one product. */}
        <Route path="/yatri/pass" element={<PassPage />} />
        <Route path="/yatri/passes" element={<WalletPage />} />
        <Route path="/yatri/lostfound" element={<LostFoundPage />} />
        <Route path="/yatri/map" element={<MapPage />} />
        <Route path="/yatri/logistics" element={<LogisticsPage />} />
        <Route path="/yatri/drills" element={<DrillsPage />} />
        <Route path="/yatri/advisories" element={<AdvisoriesPage />} />
        <Route path="/voice" element={<CallPage />} />

        {/* Officer war-room — gated by the admin key (separate SwiftChat
            officer bot in production). */}
        <Route path="/officer" element={<OfficerDashboard />} />
      </Routes>
    </LangProvider>
  );
}
