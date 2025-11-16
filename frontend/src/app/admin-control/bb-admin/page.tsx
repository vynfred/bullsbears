"use client";

/**
 * Hidden Admin Control Panel
 * Access: /admin-control-xyz (secret URL, not linked anywhere)
 * Authentication: Separate admin login (not regular user auth)
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Power, Database, Cloud, Key, RefreshCw, PlayCircle, StopCircle, Lock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";

interface SystemStatus {
  googleSQL: boolean;
  firebase: boolean;
  fmpAPI: boolean;
  groqAPI: boolean;
  grokAPI: boolean;
  deepseekAPI: boolean;
  runpodEndpoint: boolean;
}

export default function AdminControlPanel() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [adminToken, setAdminToken] = useState<string | null>(null);
  
  // Login form state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // System state
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    googleSQL: false,
    firebase: false,
    fmpAPI: false,
    groqAPI: false,
    grokAPI: false,
    deepseekAPI: false,
    runpodEndpoint: false,
  });
  const [isSystemOn, setIsSystemOn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isPriming, setIsPriming] = useState(false);
  const [primeProgress, setPrimeProgress] = useState<any>(null);

  // Check if admin token exists in localStorage
  useEffect(() => {
    const token = localStorage.getItem("admin_token");
    if (token) {
      setAdminToken(token);
      setIsAuthenticated(true);
      checkSystemStatus();
    }
  }, []);

  // Admin login
  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingIn(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: loginEmail, password: loginPassword }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.token) {
          localStorage.setItem("admin_token", data.token);
          setAdminToken(data.token);
          setIsAuthenticated(true);
          toast.success("Admin access granted");
          checkSystemStatus();
        } else {
          toast.error("Invalid admin credentials");
        }
      } else {
        toast.error("Authentication failed");
      }
    } catch (error) {
      toast.error("Login error");
    } finally {
      setIsLoggingIn(false);
    }
  };

  // Admin logout
  const handleAdminLogout = () => {
    localStorage.removeItem("admin_token");
    setAdminToken(null);
    setIsAuthenticated(false);
    setLoginEmail("");
    setLoginPassword("");
    toast.success("Logged out");
  };

  const checkSystemStatus = async () => {
    if (!adminToken) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/status`, {
        headers: { "Authorization": `Bearer ${adminToken}` },
      });
      if (response.ok) {
        const data = await response.json();
        setSystemStatus({
          googleSQL: data.databases?.google_sql?.connected || false,
          firebase: data.databases?.firebase?.connected || false,
          fmpAPI: data.apis?.fmp?.status === 'healthy',
          groqAPI: data.apis?.groq?.status === 'healthy',
          grokAPI: data.apis?.grok?.status === 'healthy',
          deepseekAPI: data.apis?.deepseek?.status === 'healthy',
          runpodEndpoint: data.runpod?.status === 'healthy',
        });
        setIsSystemOn(data.system?.status === 'ON');
      } else if (response.status === 401) {
        // Token expired or invalid
        handleAdminLogout();
        toast.error("Session expired. Please login again.");
      }
    } catch (error) {
      toast.error("Failed to check system status");
    } finally {
      setIsLoading(false);
    }
  };

  // If not authenticated, show login form
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-6">
        <Toaster />
        <Card className="w-full max-w-md shadow-2xl bg-slate-900/80 border-slate-700">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <Lock className="w-16 h-16 text-cyan-400" />
            </div>
            <CardTitle className="text-2xl text-slate-100">Admin Control Panel</CardTitle>
            <p className="text-sm text-slate-400 mt-2">Restricted Access Only</p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAdminLogin} className="space-y-4">
              <div>
                <label className="text-sm text-slate-300 mb-2 block">Admin Email</label>
                <Input
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="admin@bullsbears.xyz"
                  required
                  className="bg-slate-800 border-slate-600 text-slate-100"
                />
              </div>
              <div>
                <label className="text-sm text-slate-300 mb-2 block">Admin Password</label>
                <Input
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="bg-slate-800 border-slate-600 text-slate-100"
                />
              </div>
              <Button
                type="submit"
                disabled={isLoggingIn}
                className="w-full bg-cyan-600 hover:bg-cyan-500"
              >
                {isLoggingIn ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Authenticating...
                  </>
                ) : (
                  <>
                    <Lock className="w-4 h-4 mr-2" />
                    Admin Login
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  const toggleSystem = async (turnOn: boolean) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/system/${turnOn ? 'on' : 'off'}`, {
        method: 'POST',
        headers: { "Authorization": `Bearer ${adminToken}` },
      });
      if (response.ok) {
        setIsSystemOn(turnOn);
        toast.success(`System turned ${turnOn ? 'ON' : 'OFF'}`);
      } else {
        toast.error(`Failed to turn system ${turnOn ? 'on' : 'off'}`);
      }
    } catch (error) {
      toast.error("Failed to toggle system");
    } finally {
      setIsLoading(false);
    }
  };

  const primeData = async () => {
    setIsPriming(true);
    setPrimeProgress({ status: 'starting', current_batch: 0, total_batches: 7 });
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/prime-data`, {
        method: 'POST',
        headers: { "Authorization": `Bearer ${adminToken}` },
      });
      if (response.ok) {
        toast.success("Data priming started!");
      } else {
        toast.error("Failed to start data priming");
        setIsPriming(false);
      }
    } catch (error) {
      toast.error("Failed to prime data");
      setIsPriming(false);
    }
  };

  const StatusBadge = ({ status }: { status: boolean }) => (
    <Badge className={status ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/50" : "bg-red-500/20 text-red-400 border-red-500/50"}>
      {status ? "Connected" : "Disconnected"}
    </Badge>
  );

  // Auto-refresh system status
  useEffect(() => {
    if (isAuthenticated) {
      const interval = setInterval(checkSystemStatus, 30000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, adminToken]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <Toaster />

      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header with Logout */}
        <div className="flex items-center justify-between">
          <div className="text-center flex-1">
            <h1 className="text-4xl font-bold text-slate-100">🎛️ Admin Control Panel</h1>
            <p className="text-slate-400">System Control & Status Monitor</p>
          </div>
          <Button onClick={handleAdminLogout} variant="outline" size="sm">
            Logout
          </Button>
        </div>

        {/* System Controls */}
        <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-blue-950/30 border-2 border-purple-700/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-100">
              <Power className="w-6 h-6 text-purple-400" />
              System Controls
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-200 font-semibold">System Status</p>
                <p className="text-sm text-slate-400">Turn the AI pipeline on or off</p>
              </div>
              <Badge className={isSystemOn ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/50 text-lg px-4 py-2" : "bg-slate-500/20 text-slate-400 border-slate-500/50 text-lg px-4 py-2"}>
                {isSystemOn ? "ONLINE" : "OFFLINE"}
              </Badge>
            </div>

            <div className="flex gap-4">
              <Button
                onClick={() => toggleSystem(true)}
                disabled={isSystemOn || isLoading}
                className="flex-1 bg-emerald-600 hover:bg-emerald-500"
              >
                <PlayCircle className="w-4 h-4 mr-2" />
                Turn ON
              </Button>
              <Button
                onClick={() => toggleSystem(false)}
                disabled={!isSystemOn || isLoading}
                variant="destructive"
                className="flex-1"
              >
                <StopCircle className="w-4 h-4 mr-2" />
                Turn OFF
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Data Priming */}
        <Card className="shadow-xl bg-gradient-to-br from-amber-950/60 via-slate-900/40 to-orange-950/30 border-2 border-amber-700/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-100">
              <Database className="w-6 h-6 text-amber-400" />
              Data Management
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-slate-200 font-semibold">Prime Database</p>
              <p className="text-sm text-slate-400 mb-4">Load 90 days of historical data for all NASDAQ stocks</p>

              <Button
                onClick={primeData}
                disabled={isPriming}
                className="bg-amber-600 hover:bg-amber-500"
              >
                <Database className="w-4 h-4 mr-2" />
                {isPriming ? "Priming..." : "Prime All Data"}
              </Button>

              {primeProgress && primeProgress.status === 'in_progress' && (
                <div className="mt-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                  <div className="flex justify-between text-sm text-slate-300 mb-2">
                    <span>Batch {primeProgress.current_batch} of {primeProgress.total_batches}</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div
                      className="bg-amber-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${(primeProgress.current_batch / primeProgress.total_batches) * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Database Status */}
        <Card className="shadow-xl bg-slate-900/60 border-slate-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-slate-100">
                <Database className="w-6 h-6 text-cyan-400" />
                Database Connections
              </CardTitle>
              <Button onClick={checkSystemStatus} variant="outline" size="sm" disabled={isLoading}>
                <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-slate-300">Google Cloud SQL</span>
              <StatusBadge status={systemStatus.googleSQL} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-300">Firebase Realtime DB</span>
              <StatusBadge status={systemStatus.firebase} />
            </div>
          </CardContent>
        </Card>

        {/* API Status */}
        <Card className="shadow-xl bg-slate-900/60 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-100">
              <Key className="w-6 h-6 text-purple-400" />
              API Keys & Services
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-slate-300">FMP API (Financial Data)</span>
              <StatusBadge status={systemStatus.fmpAPI} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-300">Groq API (Vision Agent)</span>
              <StatusBadge status={systemStatus.groqAPI} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-300">Grok API (Social Context)</span>
              <StatusBadge status={systemStatus.grokAPI} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-300">DeepSeek API (Arbitrator)</span>
              <StatusBadge status={systemStatus.deepseekAPI} />
            </div>
          </CardContent>
        </Card>

        {/* RunPod Status */}
        <Card className="shadow-xl bg-slate-900/60 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-100">
              <Cloud className="w-6 h-6 text-blue-400" />
              RunPod Infrastructure
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-slate-300">RunPod Serverless Endpoint</span>
              <StatusBadge status={systemStatus.runpodEndpoint} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}


