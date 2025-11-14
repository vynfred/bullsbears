import { FileText, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";

export default function TermsPrivacyPage() {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-3xl text-slate-100">Legal Information</h2>
        <p className="text-slate-400">Terms of Service & Privacy Policy</p>
      </div>

      <Tabs defaultValue="terms" className="w-full">
        <TabsList className="grid w-full grid-cols-2 bg-slate-800 border border-slate-700">
          <TabsTrigger value="terms" className="data-[state=active]:bg-slate-700 text-slate-200">
            Terms of Service
          </TabsTrigger>
          <TabsTrigger value="privacy" className="data-[state=active]:bg-slate-700 text-slate-200">
            Privacy Policy
          </TabsTrigger>
        </TabsList>

        <TabsContent value="terms" className="space-y-4">
          <Card className="shadow-xl bg-slate-900/60 border-slate-700">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-100">
                <FileText className="w-5 h-5 text-blue-400" />
                Terms of Service
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-slate-300 text-sm leading-relaxed">
              <div>
                <h4 className="text-slate-100 mb-2">1. Acceptance of Terms</h4>
                <p>
                  By accessing and using BullsBears.xyz, you accept and agree to be bound by the terms and 
                  provisions of this agreement. If you do not agree to these terms, please do not use this service.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">2. Description of Service</h4>
                <p>
                  BullsBears.xyz provides AI-generated stock market analysis and trading insights. The service 
                  is designed to assist users in making informed trading decisions through machine learning 
                  algorithms and data analysis.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">3. No Financial Advice</h4>
                <p>
                  The information provided by BullsBears.xyz is for informational and educational purposes only. 
                  Nothing on this platform constitutes financial advice, investment advice, trading advice, or 
                  any other sort of advice. You should not treat any content as such.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">4. Risk Disclaimer</h4>
                <p>
                  Trading stocks and securities involves substantial risk of loss and is not suitable for all 
                  investors. Past performance does not guarantee future results. You should carefully consider 
                  your financial situation and risk tolerance before making any investment decisions.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">5. Accuracy of Information</h4>
                <p>
                  While we strive to provide accurate and up-to-date information, we make no warranties or 
                  representations about the accuracy, completeness, or timeliness of the content. Market 
                  conditions can change rapidly and historical accuracy is not a guarantee of future performance.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">6. User Responsibilities</h4>
                <p>
                  You are responsible for maintaining the confidentiality of your account credentials and for 
                  all activities that occur under your account. You agree to notify us immediately of any 
                  unauthorized use of your account.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">7. Limitation of Liability</h4>
                <p>
                  BullsBears.xyz and its operators shall not be liable for any direct, indirect, incidental, 
                  special, or consequential damages arising from your use of the service or any investment 
                  decisions made based on the information provided.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">8. Modifications to Service</h4>
                <p>
                  We reserve the right to modify, suspend, or discontinue any aspect of the service at any 
                  time without notice. We may also modify these terms at any time, and continued use of the 
                  service constitutes acceptance of modified terms.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">9. Intellectual Property</h4>
                <p>
                  All content, features, and functionality of BullsBears.xyz are owned by us and are protected 
                  by copyright, trademark, and other intellectual property laws. You may not reproduce, 
                  distribute, or create derivative works without our express written permission.
                </p>
              </div>

              <div className="pt-4 text-slate-400 text-xs">
                Last Updated: November 5, 2024
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="privacy" className="space-y-4">
          <Card className="shadow-xl bg-slate-900/60 border-slate-700">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-100">
                <Shield className="w-5 h-5 text-purple-400" />
                Privacy Policy
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-slate-300 text-sm leading-relaxed">
              <div>
                <h4 className="text-slate-100 mb-2">1. Information We Collect</h4>
                <p>
                  We collect information you provide directly to us, such as your name, email address, and 
                  account preferences. We also collect information about your use of the service, including 
                  the picks you view, stocks you add to your watchlist, and interaction with features.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">2. How We Use Your Information</h4>
                <p>
                  We use your information to provide and improve our services, send you notifications and 
                  updates, personalize your experience, analyze usage patterns, and communicate with you 
                  about the service. We do not sell your personal information to third parties.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">3. Data Security</h4>
                <p>
                  We implement appropriate technical and organizational measures to protect your personal 
                  information against unauthorized access, alteration, disclosure, or destruction. However, 
                  no method of transmission over the internet is 100% secure.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">4. Cookies and Tracking</h4>
                <p>
                  We use cookies and similar tracking technologies to track activity on our service and 
                  hold certain information. You can instruct your browser to refuse all cookies or to 
                  indicate when a cookie is being sent.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">5. Third-Party Services</h4>
                <p>
                  We may use third-party services for analytics, payment processing, and other functions. 
                  These third parties have access to your information only to perform specific tasks on our 
                  behalf and are obligated not to disclose or use it for any other purpose.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">6. Data Retention</h4>
                <p>
                  We retain your personal information for as long as necessary to provide our services and 
                  fulfill the purposes outlined in this privacy policy. You may request deletion of your 
                  account and associated data at any time.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">7. Your Rights</h4>
                <p>
                  You have the right to access, correct, or delete your personal information. You can update 
                  your information in your account settings or contact us to exercise these rights. You also 
                  have the right to opt-out of marketing communications.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">8. Children's Privacy</h4>
                <p>
                  Our service is not intended for users under the age of 18. We do not knowingly collect 
                  personal information from children. If you become aware that a child has provided us with 
                  personal information, please contact us.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">9. Changes to Privacy Policy</h4>
                <p>
                  We may update our privacy policy from time to time. We will notify you of any changes by 
                  posting the new privacy policy on this page and updating the "Last Updated" date.
                </p>
              </div>

              <div>
                <h4 className="text-slate-100 mb-2">10. Contact Us</h4>
                <p>
                  If you have any questions about this privacy policy or our data practices, please contact 
                  us at privacy@bullsbears.xyz
                </p>
              </div>

              <div className="pt-4 text-slate-400 text-xs">
                Last Updated: November 5, 2024
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
