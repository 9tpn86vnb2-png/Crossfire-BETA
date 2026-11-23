#!/usr/bin/env python3
"""Emulator-only UI dump helper, no dependency on the plugin or production app. MIT."""
from pathlib import Path
import os,subprocess
r=Path('window-driver');r.mkdir(exist_ok=True);sdk=Path(os.environ['ANDROID_HOME'])
tools=sorted((sdk/'build-tools').iterdir(),key=lambda p:[int(x) for x in p.name.split('.') if x.isdigit()])[-1]
android=sdk/'platforms/android-35/android.jar';assert android.exists()
(r/'AndroidManifest.xml').write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="org.bitchord.testdriver"><uses-sdk android:minSdkVersion="27" android:targetSdkVersion="28"/><application android:label="Test driver only" android:debuggable="true"/><instrumentation android:name="org.bitchord.testdriver.WindowDump" android:targetPackage="org.bitchord.testdriver"/></manifest>''')
(r/'WindowDump.java').write_text(r'''package org.bitchord.testdriver;
import android.app.*;import android.os.*;import android.graphics.Rect;import android.accessibilityservice.AccessibilityServiceInfo;import android.view.accessibility.*;import java.util.*;
public class WindowDump extends Instrumentation {
 @Override public void onCreate(Bundle b){super.onCreate(b);start();}
 String esc(CharSequence s){return s==null?"":s.toString().replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\"","&quot;").replace("\n","&#10;").replace("\r","");}
 void node(StringBuilder s,AccessibilityNodeInfo n,int depth){
  if(n==null||depth>80)return;Rect r=new Rect();n.getBoundsInScreen(r);
  s.append("<node text=\"").append(esc(n.getText())).append("\" content-desc=\"").append(esc(n.getContentDescription())).append("\" class=\"").append(esc(n.getClassName())).append("\" package=\"").append(esc(n.getPackageName())).append("\" enabled=\"").append(n.isEnabled()).append("\" bounds=\"[").append(r.left).append(',').append(r.top).append("][ ".trim()).append(r.right).append(',').append(r.bottom).append("]\">");
  for(int i=0;i<n.getChildCount();i++){AccessibilityNodeInfo c=n.getChild(i);node(s,c,depth+1);if(c!=null)c.recycle();}s.append("</node>");
 }
 @Override public void onStart(){Bundle result=new Bundle();try{
  UiAutomation a=getUiAutomation();AccessibilityServiceInfo f=a.getServiceInfo();f.flags|=AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS|AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;a.setServiceInfo(f);SystemClock.sleep(400);
  StringBuilder s=new StringBuilder("<hierarchy>");for(AccessibilityWindowInfo w:a.getWindows()){AccessibilityNodeInfo n=w.getRoot();node(s,n,0);if(n!=null)n.recycle();w.recycle();}s.append("</hierarchy>");result.putString("xml",s.toString());finish(Activity.RESULT_OK,result);
 }catch(Throwable t){result.putString("error",t.toString());finish(Activity.RESULT_CANCELED,result);}}
}
''')
(r/'classes').mkdir(exist_ok=True);(r/'dex').mkdir(exist_ok=True)
def run(*a):subprocess.run([str(x) for x in a],check=True)
run('javac','-source','8','-target','8','-bootclasspath',android,'-d',r/'classes',r/'WindowDump.java')
run(tools/'d8','--lib',android,'--min-api','27','--output',r/'dex',r/'classes/org/bitchord/testdriver/WindowDump.class')
run(tools/'aapt','package','-f','-M',r/'AndroidManifest.xml','-I',android,'-F',r/'unsigned.apk')
run('jar','uf',r/'unsigned.apk','-C',r/'dex','classes.dex')
run(tools/'zipalign','-f','4',r/'unsigned.apk',r/'aligned.apk')
run('keytool','-genkeypair','-keystore',r/'test-only.jks','-alias','test','-storepass','android','-keypass','android','-keyalg','RSA','-validity','365','-dname','CN=Emulator Test Only')
run(tools/'apksigner','sign','--ks',r/'test-only.jks','--ks-pass','pass:android','--key-pass','pass:android','--out',r/'driver.apk',r/'aligned.apk')
