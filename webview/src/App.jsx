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
import GrievancePage from "./yatri/GrievancePage.jsx";
import TransportPage from "./yatri/TransportPage.jsx";
import AlertsPage from "./yatri/AlertsPage.jsx";
import RouteQrPage from "./yatri/RouteQrPage.jsx";
import GalleryPage from "./yatri/GalleryPage.jsx";
import OfficerChatPage from "./officer/OfficerChatPage.jsx";
import OfficerGrievances from "./officer/OfficerGrievances.jsx";
import OfficerAlerts from "./officer/OfficerAlerts.jsx";
import OfficerSos from "./officer/OfficerSos.jsx";
import OfficerRegistry from "./officer/OfficerRegistry.jsx";
import OfficerHeatmap from "./officer/OfficerHeatmap.jsx";
import OfficerActivitiesPage from "./officer/OfficerActivitiesPage.jsx";

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
        <Route path="/yatri/grievance" element={<GrievancePage />} />
        <Route path="/yatri/transport" element={<TransportPage />} />
        <Route path="/yatri/alerts" element={<AlertsPage />} />
        <Route path="/yatri/route-qr" element={<RouteQrPage />} />
        <Route path="/yatri/gallery" element={<GalleryPage />} />
        <Route path="/yatri/map" element={<MapPage />} />
        <Route path="/yatri/logistics" element={<LogisticsPage />} />
        <Route path="/yatri/drills" element={<DrillsPage />} />
        <Route path="/yatri/advisories" element={<AdvisoriesPage />} />
        <Route path="/voice" element={<CallPage />} />

        {/* Officer war-room — a chat agent (mirrors the yatri agent) whose
            quick-activities open webview dashboards. Gated by the admin key
            (a separate SwiftChat officer bot in production). */}
        <Route path="/officer" element={<OfficerChatPage />} />
        <Route path="/officer/grievances" element={<OfficerGrievances />} />
        <Route path="/officer/alerts" element={<OfficerAlerts />} />
        <Route path="/officer/sos" element={<OfficerSos />} />
        <Route path="/officer/registry" element={<OfficerRegistry />} />
        <Route path="/officer/heatmap" element={<OfficerHeatmap />} />
        <Route path="/officer/activities" element={<OfficerActivitiesPage />} />
      </Routes>
    </LangProvider>
  );
}
