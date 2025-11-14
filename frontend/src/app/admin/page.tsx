// src/app/admin/page.tsx
"use client";

import { useState, useEffect } from "react";
import { Power, Database, Cloud, Key, RefreshCw, PlayCircle, StopCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

export default function AdminPage() {
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

  const checkSystemStatus = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/status`);
      if (response.ok) {
        const data = await response.json();
        setSystemStatus(data.status || systemStatus);
        setIsSystemOn(data.system_on || false);
      }
    } catch (error) {
      toast.error("Failed to check system status");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSystem = async (turnOn: boolean) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/system/${turnOn ? 'on' : 'off'}`, {
        method: 'POST',
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
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/prime-data`, {
        method: 'POST',
      });
      if (response.ok) {
        toast.success("Data priming started! This will take several minutes...");
      } else {
        toast.error("Failed to start data priming");
      }
    } catch (error) {
      toast.error("Failed to prime data");
    } finally {
      setIsPriming(false);
    }
  };

  useEffect(() => {
    checkSystemStatus();
    const interval = setInterval(checkSystemStatus, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const StatusBadge = ({ status }: { status: boolean }) => (
    <Badge className={status ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/50" : "bg-red-500/20 text-red-400 border-red-500/50"}>
      {status ? "Connected" : "Disconnected"}
    </Badge>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <Toaster />
      
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-slate-100">BullsBears Admin</h1>
          <p className="text-slate-400">System Control & Status Monitor</p>
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
              <p className="text-sm text-slate-400 mb-4">Load 90 days of historical data for all NASDAQ stocks (~6,960 tickers)</p>
              <Button
                onClick={primeData}
                disabled={isPriming}
                className="bg-amber-600 hover:bg-amber-500"
              >
                <Database className="w-4 h-4 mr-2" />
                {isPriming ? "Priming..." : "Prime Data"}
              </Button>
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

