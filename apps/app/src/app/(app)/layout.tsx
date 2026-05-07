import { AuthGate } from "@/components/AuthGate";
import { Sidebar } from "@/components/Sidebar";

export default function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <AuthGate>
      <div className="flex min-h-screen bg-surface">
        <Sidebar />
        <main className="flex-1 p-8">{children}</main>
      </div>
    </AuthGate>
  );
}
