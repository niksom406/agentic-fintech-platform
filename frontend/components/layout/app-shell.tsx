import type { ReactNode } from "react";

import { SidebarNav } from "@/components/layout/sidebar-nav";
import { TopNav } from "@/components/layout/top-nav";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen relative z-10">
      <div className="mx-auto flex max-w-[1700px] gap-5 px-4 py-5 lg:px-6">
        <SidebarNav />
        <main className="flex-1 min-w-0 space-y-5 animate-fade-in-up">
          <TopNav />
          {children}
        </main>
      </div>
    </div>
  );
}
