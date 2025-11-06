import { Mail, Calendar, Award, Flame, Share2, Copy } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { toast } from "sonner";

export function ProfilePage() {
  const referralCode = "BULLS2024XYZ";
  const referralLink = `https://bullsbears.xyz/ref/${referralCode}`;

  const copyReferralLink = () => {
    navigator.clipboard.writeText(referralLink);
    toast.success("Referral link copied to clipboard!");
  };

  return (
    <div className="space-y-6">
      {/* Profile Header */}
      <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-blue-950/30 border-2 border-purple-700/40">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center text-center space-y-4">
            <Avatar className="w-24 h-24 border-4 border-purple-500/50">
              <AvatarFallback className="bg-gradient-to-br from-purple-600 to-blue-600 text-white text-3xl">
                JD
              </AvatarFallback>
            </Avatar>
            <div>
              <h2 className="text-2xl text-slate-100">John Doe</h2>
              <p className="text-slate-400">Premium Member</p>
            </div>
            <Badge className="bg-gradient-to-r from-emerald-500 to-purple-500 text-white border-0">
              <Award className="w-3 h-3 mr-1" />
              Pro Trader
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Account Info */}
      <Card className="shadow-xl bg-slate-900/60 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Account Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3 text-slate-300">
            <Mail className="w-5 h-5 text-slate-400" />
            <div>
              <p className="text-sm text-slate-500">Email</p>
              <p>john.doe@example.com</p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-slate-300">
            <Calendar className="w-5 h-5 text-slate-400" />
            <div>
              <p className="text-sm text-slate-500">Sign Up Date</p>
              <p>January 15, 2024</p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-slate-300">
            <Calendar className="w-5 h-5 text-slate-400" />
            <div>
              <p className="text-sm text-slate-500">Days as Member</p>
              <p>295 days</p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-slate-300">
            <Flame className="w-5 h-5 text-orange-400" />
            <div>
              <p className="text-sm text-slate-500">Active Streak</p>
              <p className="flex items-center gap-1">
                <span>42 days</span>
                <Flame className="w-4 h-4 text-orange-400" />
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Referral Section */}
      <Card className="shadow-xl bg-gradient-to-br from-purple-950/60 via-slate-900/40 to-pink-950/30 border-2 border-purple-700/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-100">
            <Share2 className="w-5 h-5 text-purple-400" />
            Share & Earn
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-300 text-center">
            Invite friends and earn premium features! Share your unique referral link.
          </p>
          
          <div className="bg-slate-800/50 p-4 rounded-lg">
            <p className="text-xs text-slate-400 mb-2 text-center">Your Referral Code</p>
            <p className="text-lg text-purple-400 text-center font-mono">{referralCode}</p>
          </div>

          <div className="bg-slate-800/50 p-4 rounded-lg">
            <p className="text-xs text-slate-400 mb-2 text-center">Your Referral Link</p>
            <p className="text-sm text-slate-300 text-center break-all">{referralLink}</p>
          </div>

          <Button 
            className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500"
            onClick={copyReferralLink}
          >
            <Copy className="w-4 h-4 mr-2" />
            Copy Referral Link
          </Button>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="text-center p-3 bg-slate-800/30 rounded-lg">
              <p className="text-xl text-emerald-400">7</p>
              <p className="text-xs text-slate-400">Friends Joined</p>
            </div>
            <div className="text-center p-3 bg-slate-800/30 rounded-lg">
              <p className="text-xl text-purple-400">14</p>
              <p className="text-xs text-slate-400">Days Earned</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <Card className="shadow-xl bg-slate-900/60 border-slate-700">
        <CardContent className="pt-6 space-y-3">
          <Button className="w-full bg-purple-600 hover:bg-purple-500">
            Edit Profile
          </Button>
          <Button variant="outline" className="w-full border-slate-600 text-slate-200 hover:bg-slate-800">
            Change Password
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
