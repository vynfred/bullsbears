// src/app/dashboard/page.tsx
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Menu, TrendingUp, Eye, LineChart, User, HelpCircle, Settings, FileText, LogOut } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import PicksTab from "@/components/private/PicksTab";
import WatchlistTab from "@/components/private/WatchlistTab";
import AnalyticsTab from "@/components/private/AnalyticsTab";
import ProfilePage from "@/components/private/ProfilePage";
import SettingsPage from "@/components/private/SettingsPage";
import HowItWorksPage from "@/components/public/HowItWorksPage";
import FAQPage from "@/components/public/FAQPage";
import TermsPrivacyPage from "@/components/public/TermsPrivacyPage";
import { AnimatedLogo } from "@/components/shared/AnimatedLogo";
import { CandleBackground } from "@/components/shared/CandleBackground";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Toaster } from "@/components/ui/sonner";

type TabType = "picks" | "watchlist" | "analytics";
type PageType = TabType | "profile" | "settings" | "howItWorks" | "faq" | "terms";

export default function Dashboard() {
  const router = useRouter();
  const { user, loading: authLoading, signOut } = useAuth();
  const [activePage, setActivePage] = useState<PageType>("picks");
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // Auth protection
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  const handleNavigation = (page: PageType) => {
    setActivePage(page);
    setIsMenuOpen(false);
  };

  const handleLogout = async () => {
    await signOut();
    router.push('/');
  };

  if (authLoading) {
    return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">Loading...</div>;
  }

  if (!user) return null;

  return (
    <div className="dark min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 pb-20">
      <CandleBackground />
      <Toaster />
      {/* Header */}
      <header className="border-b border-slate-800 sticky top-0 bg-slate-950/95 backdrop-blur-sm z-20 shadow-lg shadow-black/20">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* Left Side - Menu */}
            <Sheet open={isMenuOpen} onOpenChange={setIsMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="hover:bg-slate-800 text-slate-100 border border-slate-700">
                  <Menu className="w-6 h-6" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="bg-slate-950 border-slate-800">
                <SheetHeader>
                  <SheetTitle>
                    <AnimatedLogo className="text-2xl font-black" />
                  </SheetTitle>
                </SheetHeader>
                <div className="mt-8 space-y-2">
                  <Button
                    variant="ghost"
                    className="w-full justify-start hover:bg-slate-800 text-slate-200"
                    onClick={() => handleNavigation("profile")}
                  >
                    <User className="w-5 h-5 mr-3" />
                    Profile
                  </Button>
                  <Button
                    variant="ghost"
                    className="w-full justify-start hover:bg-slate-800 text-slate-200"
                    onClick={() => handleNavigation("howItWorks")}
                  >
                    <HelpCircle className="w-5 h-5 mr-3" />
                    How it Works
                  </Button>
                  <Button
                    variant="ghost"
                    className="w-full justify-start hover:bg-slate-800 text-slate-200"
                    onClick={() => handleNavigation("settings")}
                  >
                    <Settings className="w-5 h-5 mr-3" />
                    Settings
                  </Button>
                  <Button
                    variant="ghost"
                    className="w-full justify-start hover:bg-slate-800 text-slate-200"
                    onClick={() => handleNavigation("faq")}
                  >
                    <HelpCircle className="w-5 h-5 mr-3" />
                    FAQ
                  </Button>
                  <Button
                    variant="ghost"
                    className="w-full justify-start hover:bg-slate-800 text-slate-200"
                    onClick={() => handleNavigation("terms")}
                  >
                    <FileText className="w-5 h-5 mr-3" />
                    Terms / Privacy
                  </Button>
                  
                  <Separator className="my-4 bg-slate-800" />
                  
                  <Button
                    variant="ghost"
                    className="w-full justify-start hover:bg-slate-800 text-rose-400 hover:text-rose-300"
                    onClick={handleLogout}
                  >
                    <LogOut className="w-5 h-5 mr-3" />
                    Logout
                  </Button>
                </div>
              </SheetContent>
            </Sheet>

            {/* Logo */}
            <div className="absolute left-1/2 -translate-x-1/2">
              <AnimatedLogo className="text-2xl font-black" />
            </div>

            {/* Placeholder for balance */}
            <div className="w-10"></div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 max-w-6xl relative z-10">
        {activePage === "picks" && <PicksTab />}
        {activePage === "watchlist" && <WatchlistTab />}
        {activePage === "analytics" && <AnalyticsTab onNavigateToPicks={() => setActivePage("picks")} />}
        {activePage === "profile" && <ProfilePage />}
        {activePage === "settings" && <SettingsPage />}
        {activePage === "howItWorks" && <HowItWorksPage />}
        {activePage === "faq" && <FAQPage />}
        {activePage === "terms" && <TermsPrivacyPage />}
      </main>

      {/* Bottom Navigation - Always show */}
      <nav className="fixed bottom-0 left-0 right-0 border-t border-slate-800 bg-slate-950/95 backdrop-blur-sm shadow-2xl z-20">
        <div className="grid grid-cols-3 h-20">
          <button
            onClick={() => setActivePage("picks")}
            className={`flex flex-col items-center justify-center gap-1 transition-all duration-300 ${
              activePage === "picks"
                ? "text-emerald-400 bg-gradient-to-t from-emerald-950/40 to-transparent shadow-inner"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
            }`}
          >
            <TrendingUp className="w-6 h-6" />
            <span className="text-sm">AI Picks</span>
          </button>

          <button
            onClick={() => setActivePage("watchlist")}
            className={`flex flex-col items-center justify-center gap-1 transition-all duration-300 ${
              activePage === "watchlist"
                ? "text-purple-400 bg-gradient-to-t from-purple-950/40 to-transparent shadow-inner"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
            }`}
          >
            <Eye className="w-6 h-6" />
            <span className="text-sm">Watchlist</span>
          </button>

          <button
            onClick={() => setActivePage("analytics")}
            className={`flex flex-col items-center justify-center gap-1 transition-all duration-300 ${
              activePage === "analytics"
                ? "text-blue-400 bg-gradient-to-t from-blue-950/40 to-transparent shadow-inner"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/20"
            }`}
          >
            <LineChart className="w-6 h-6" />
            <span className="text-sm">Analytics</span>
          </button>
        </div>
      </nav>
    </div>
  );
}
