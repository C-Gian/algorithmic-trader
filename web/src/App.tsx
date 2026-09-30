import { useSection } from "./lib/route";
import { AppShell } from "./shell/AppShell";
import { HealthProvider } from "./shell/health";
import { DataWorkspace } from "./views/DataWorkspace";
import { Overview } from "./views/Overview";
import { Recorder } from "./views/Recorder";
import { ReplayLab } from "./views/ReplayLab";

export function App() {
  const section = useSection();
  return (
    <HealthProvider>
      <AppShell section={section}>
        {section === "market" && <Overview />}
        {section === "replay" && <ReplayLab />}
        {section === "data" && <DataWorkspace />}
        {section === "recorder" && <Recorder />}
      </AppShell>
    </HealthProvider>
  );
}
