import { Bell, Moon, DollarSign, Mail, MessageSquare, Shield, Smartphone } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Separator } from "./ui/separator";

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl text-slate-100 text-center">Settings</h2>

      {/* Notifications */}
      <Card className="shadow-xl bg-gradient-to-br from-amber-950/60 via-slate-900/40 to-orange-950/30 border-2 border-amber-700/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-100">
            <Bell className="w-5 h-5 text-amber-400" />
            Notifications
          </CardTitle>
          <CardDescription className="text-slate-400">
            Manage your notification preferences
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="push-notifications" className="text-slate-200">Push Notifications</Label>
              <p className="text-sm text-slate-400">Receive push notifications on your device</p>
            </div>
            <Switch id="push-notifications" defaultChecked />
          </div>
          
          <Separator className="bg-slate-700" />
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="email-alerts" className="text-slate-200">Email Alerts</Label>
              <p className="text-sm text-slate-400">Get daily summary emails</p>
            </div>
            <Switch id="email-alerts" defaultChecked />
          </div>
          
          <Separator className="bg-slate-700" />
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="ai-picks" className="text-slate-200">AI Pick Alerts</Label>
              <p className="text-sm text-slate-400">Notify when new AI picks are available</p>
            </div>
            <Switch id="ai-picks" defaultChecked />
          </div>
          
          <Separator className="bg-slate-700" />
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="watchlist-alerts" className="text-slate-200">Watchlist Alerts</Label>
              <p className="text-sm text-slate-400">Notify on watchlist stock movements</p>
            </div>
            <Switch id="watchlist-alerts" defaultChecked />
          </div>
          
          <Separator className="bg-slate-700" />
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="price-targets" className="text-slate-200">Price Target Alerts</Label>
              <p className="text-sm text-slate-400">Notify when stocks hit price targets</p>
            </div>
            <Switch id="price-targets" defaultChecked />
          </div>
        </CardContent>
      </Card>

      {/* Preferences */}
      <Card className="shadow-xl bg-slate-900/60 border-slate-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-100">
            <Moon className="w-5 h-5 text-slate-400" />
            Preferences
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label className="text-slate-200">Default Currency</Label>
            <Select defaultValue="usd">
              <SelectTrigger className="bg-slate-800 border-slate-600 text-slate-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-700">
                <SelectItem value="usd" className="text-slate-200 focus:bg-slate-800">USD ($)</SelectItem>
                <SelectItem value="eur" className="text-slate-200 focus:bg-slate-800">EUR (€)</SelectItem>
                <SelectItem value="gbp" className="text-slate-200 focus:bg-slate-800">GBP (£)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <Separator className="bg-slate-700" />
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="dark-mode" className="text-slate-200">Dark Mode</Label>
              <p className="text-sm text-slate-400">Always use dark theme</p>
            </div>
            <Switch id="dark-mode" defaultChecked />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
